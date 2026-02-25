import { useState } from "react";
import { LoanForm } from "@/components/LoanForm";
import { ChatInterface, Message } from "@/components/ChatInterface";
import { AssessmentResult } from "@/components/ResultCard";
import { assessCredit, chatWithAgent, type AssessmentResponse } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";

/** Strip markdown bold markers and clean extra whitespace (preserving newlines) */
function cleanMarkdown(text: string): string {
  return text
    .replace(/\*\*/g, "")
    .split("\n")
    .map(line => line.replace(/\s+/g, " ").trim())
    .join("\n")
    .trim();
}

function parseAssessmentResponse(res: AssessmentResponse, requestData: { id: string; amount: number; term: number }): AssessmentResult {
  const trail = res.reasoning_trail || [];

  const customerStep = trail.find(s => s.step === 1);
  const cicStep = trail.find(s => s.step === 2);
  const paymentStep = trail.find(s => s.step === 3);
  const dtiStep = trail.find(s => s.step === 4);

  // Hạn mức được ghi ở step 5 (tool calculate_max_loan).
  const loanStep = trail.find(s => s.step === 5);

  // ── Customer info ──
  const nameMatch = customerStep?.result?.match(/^([^,]+),/);
  const customerName = nameMatch ? nameMatch[1] : `Khách hàng #${requestData.id}`;

  const ageMatch = customerStep?.result?.match(/(\d+)\s*tuổi/);
  const age = ageMatch ? parseInt(ageMatch[1]) : 0;

  const incomeMatch = customerStep?.result?.match(/([\d,]+)\s*VND/);
  const income = incomeMatch ? parseInt(incomeMatch[1].replace(/,/g, "")) : 0;

  // ── CIC ──
  const cicMatch = cicStep?.result?.match(/CIC\s*=?\s*(\d+)/);
  const cicScore = cicMatch ? parseInt(cicMatch[1]) : 0;

  const rateMatch = cicStep?.detail?.match(/([\d.]+)%\/năm/);
  const rate = rateMatch ? parseFloat(rateMatch[1]) : undefined;

  let cicRating = "N/A";
  if (cicScore >= 750) cicRating = "Rất tốt";
  else if (cicScore >= 700) cicRating = "Tốt";
  else if (cicScore >= 650) cicRating = "Khá";
  else if (cicScore >= 600) cicRating = "Trung bình";
  else if (cicScore > 0) cicRating = "Kém";

  const hasBadDebt = cicStep?.detail?.includes("AUTO REJECT") && cicStep?.detail?.includes("Nhóm nợ");

  // ── Financial ──
  const pmtMatch = paymentStep?.result?.match(/([\d,]+)\s*VND/);
  const monthlyPayment = pmtMatch ? parseInt(pmtMatch[1].replace(/,/g, "")) : undefined;

  const dtiMatch = dtiStep?.result?.match(/([\d.]+)%/);
  const dtiValue: number | string = dtiMatch ? parseFloat(dtiMatch[1]) : "N/A";


  const limitMatch = loanStep?.result?.match(/([\d,]+)\s*VND/);
  const limit = limitMatch ? parseInt(limitMatch[1].replace(/,/g, "")) : undefined;

  // ── Decision & reason ──
  const status = (res.decision === "APPROVED" ? "APPROVED"
    : res.decision === "REJECTED" ? "REJECTED"
      : "REVIEW") as AssessmentResult["status"];

  // Keep reason extraction consistent with chat flow: prefer LLM report section
  const reasonMatch = res.report?.match(/##\s*(?:LÝ DO|Diễn giải[^\n]*)\n([\s\S]*?)(?=##|$)/i);

  // Fallback from reasoning trail when report doesn't contain detail section
  const failParts = trail
    .filter(s => s.decision === "FAIL" || s.decision === "REVIEW")
    .map(s => s.detail)
    .filter(Boolean);

  const reason = reasonMatch
    ? cleanMarkdown(reasonMatch[1])
    : failParts.length > 0
      ? cleanMarkdown(failParts.join(". "))
      : status === "APPROVED"
        ? "Hồ sơ đạt tất cả tiêu chí thẩm định. Đủ điều kiện phê duyệt khoản vay."
        : "Đã hoàn tất thẩm định.";

  // ── Extract recommendation from LLM report ──
  // Only read dedicated ĐỀ XUẤT section to avoid duplicating Diễn giải chi tiết.
  let recommendation: string | undefined;
  if (res.report) {
    const recMatch = res.report.match(/##\s*(?:ĐỀ XUẤT|Đề xuất|Gợi ý)[^\n]*\n([\s\S]*?)(?=##|$)/i);
    if (recMatch) {
      recommendation = cleanMarkdown(recMatch[1].replace(/^-\s*/gm, '• '));
    }
  }
  if (res.needs_human_review && !recommendation) {
    recommendation = "Hồ sơ cần được xem xét bởi chuyên viên cấp cao.";
  }

  return {
    status,
    customerName,
    age,
    income,
    cicScore,
    cicRating,
    badDebt: hasBadDebt || false,
    rate,
    monthlyPayment,
    dti: dtiValue,
    limit,
    requestedAmount: requestData.amount,
    reason,
    recommendation,
    reasoningTrail: trail,
  };
}

/**
 * Parse a chat message (raw LLM report text) into AssessmentResult if it contains an assessment.
 * Detects by looking for "## QUYẾT ĐỊNH" header in the text.
 */
function parseChatReport(text: string): AssessmentResult | null {
  if (!text.includes("QUYẾT ĐỊNH")) return null;

  // ── Decision ──
  const decisionMatch = text.match(/QUYẾT ĐỊNH[:\s]*(\w+)/);
  if (!decisionMatch) return null;

  const rawDecision = decisionMatch[1].toUpperCase();
  const status: AssessmentResult["status"] =
    rawDecision === "APPROVED" ? "APPROVED"
      : rawDecision === "REJECTED" ? "REJECTED"
        : "REVIEW";

  // ── Customer info ──
  const nameMatch = text.match(/Họ tên[:\s]*([^\n-]+)/);
  const customerName = nameMatch ? nameMatch[1].trim() : "Khách hàng";

  const ageMatch = text.match(/Tuổi[:\s]*(\d+)/);
  const age = ageMatch ? parseInt(ageMatch[1]) : 0;

  const incomeMatch = text.match(/Thu nhập[:\s]*([\d,.]+)\s*VND/);
  const income = incomeMatch ? parseInt(incomeMatch[1].replace(/[,. ]/g, "")) : 0;

  // ── CIC ──
  const cicMatch = text.match(/CIC\s*Score[:\s]*(\d+)/);
  const cicScore = cicMatch ? parseInt(cicMatch[1]) : 0;

  let cicRating = "N/A";
  if (cicScore >= 750) cicRating = "Rất tốt";
  else if (cicScore >= 700) cicRating = "Tốt";
  else if (cicScore >= 650) cicRating = "Khá";
  else if (cicScore >= 600) cicRating = "Trung bình";
  else if (cicScore > 0) cicRating = "Kém";

  const badDebtMatch = text.match(/Nợ xấu[:\s]*(Có|Không)/i);
  const badDebt = badDebtMatch ? badDebtMatch[1].toLowerCase() === "có" : false;

  const rateMatch = text.match(/Lãi suất[^:\n]*[:\s]*([\d.]+)%/);
  const rate = rateMatch ? parseFloat(rateMatch[1]) : undefined;

  // ── Financial ──
  const pmtMatch = text.match(/Tiền trả hàng tháng[:\s]*([\d,.]+)\s*VND/);
  const monthlyPayment = pmtMatch ? parseInt(pmtMatch[1].replace(/[,. ]/g, "")) : undefined;

  const dtiMatch = text.match(/DTI[:\s]*([\d.]+)%/);
  const dtiValue: number | string = dtiMatch ? parseFloat(dtiMatch[1]) : "N/A";

  const limitMatch = text.match(/Hạn mức[^:\n]*[:\s]*([\d,.]+)\s*VND/);
  const limit = limitMatch ? parseInt(limitMatch[1].replace(/[,. ]/g, "")) : undefined;

  const requestedAmountMatch = text.match(/(?:Số tiền vay(?: đề nghị)?|Khoản vay yêu cầu)[:\s]*([\d,.]+)\s*VND/i);
  const requestedAmount = requestedAmountMatch
    ? parseInt(requestedAmountMatch[1].replace(/[,. ]/g, ""))
    : undefined;

  // ── Reason ──
  // Match both old format (## LÝ DO) and current format (## Diễn giải chi tiết)
  const lyDoMatch = text.match(/##\s*(?:LÝ DO|Diễn giải[^\n]*)\n([\s\S]*?)(?=##|$)/);
  const reason = lyDoMatch ? cleanMarkdown(lyDoMatch[1]) : "Xem chi tiết trong báo cáo.";

  // ── Recommendation ──
  let recommendation: string | undefined;
  const recMatch = text.match(/##\s*(?:ĐỀ XUẤT|Đề xuất|Gợi ý)[^\n]*\n([\s\S]*?)(?=##|$)/i);
  if (recMatch) {
    recommendation = cleanMarkdown(recMatch[1].replace(/^-\s*/gm, '• '));
  }

  return {
    status,
    customerName,
    age,
    income,
    cicScore,
    cicRating,
    badDebt,
    rate,
    monthlyPayment,
    dti: dtiValue,
    limit,
    requestedAmount,
    reason,
    recommendation,
  };
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "system",
      content: "Chào mừng bạn đến với hệ thống trợ lý ảo FinSafe. Tôi đã sẵn sàng hỗ trợ bạn thẩm định hồ sơ vay tiêu dùng. Vui lòng nhập thông tin ID khách hàng và các chi tiết khoản vay ở bảng bên trái.",
      timestamp: new Date()
    }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [threadId, setThreadId] = useState<string | undefined>();

  const handleAssessment = async (data: { id: string; amount: number; term: number }) => {
    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: `Yêu cầu thẩm định hồ sơ. CCCD: ${data.id}. Số tiền: ${formatCurrency(data.amount)}. Kỳ hạn: ${data.term} tháng.`,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMsg]);

    setIsLoading(true);
    const loadingMsg: Message = {
      id: "loading",
      role: "system",
      content: `Đang thẩm định hồ sơ CCCD ${data.id}...`,
      isProgress: true,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, loadingMsg]);

    try {
      const response = await assessCredit({
        customer_id: data.id,
        loan_amount: data.amount,
        term_months: data.term,
      });

      setMessages(prev => prev.filter(m => m.id !== "loading"));

      if (response.success) {
        setThreadId(response.thread_id);
        const resultData = parseAssessmentResponse(response, data);

        // Save reasoning trail to localStorage for /trail page
        localStorage.setItem("reasoning_trail", JSON.stringify({
          customerName: resultData.customerName,
          decision: response.decision || resultData.status,
          threadId: response.assessment_id || response.thread_id,
          timestamp: new Date().toISOString(),
          trail: response.reasoning_trail || [],
        }));

        // Short assessment info
        setMessages(prev => [...prev, {
          id: (Date.now() + 1).toString(),
          role: "system",
          content: `📋 Thẩm định CCCD ${data.id}, hạn mức mong muốn ${formatCurrency(data.amount)}, thời hạn ${data.term} tháng.`,
          timestamp: new Date()
        }]);

        // Build shortened text summary — detail in card only
        const statusLabel = resultData.status === "APPROVED" ? "Phê duyệt"
          : resultData.status === "REJECTED" ? "Từ chối" : "Cần xem xét";
        const shortSummary = `Khách hàng **${resultData.customerName}** được **${statusLabel}**. Xem chi tiết bên dưới.`;

        setMessages(prev => [...prev, {
          id: (Date.now() + 2).toString(),
          role: "system",
          content: shortSummary,
          cardData: resultData,
          timestamp: new Date()
        }]);


        if (response.needs_human_review) {
          setMessages(prev => [...prev, {
            id: (Date.now() + 4).toString(),
            role: "system",
            content: `⚠️ CẦN XEM XÉT: Hồ sơ này cần được duyệt bởi chuyên viên cấp cao. Mã hồ sơ: ${response.assessment_id || response.thread_id}`,
            timestamp: new Date()
          }]);
        }
      } else {
        setMessages(prev => [...prev, {
          id: (Date.now() + 1).toString(),
          role: "system",
          content: `❌ Lỗi thẩm định: ${response.error || "Không xác định"}. Vui lòng thử lại.`,
          timestamp: new Date()
        }]);
      }
    } catch (error) {
      setMessages(prev => prev.filter(m => m.id !== "loading"));
      const errMsg = error instanceof Error ? error.message : "Unknown";
      const isRateLimit = errMsg.includes("giới hạn") || errMsg.includes("yêu cầu/ngày");
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: "system",
        content: isRateLimit
          ? `⚠️ ${errMsg}`
          : `❌ Không thể kết nối tới backend. Vui lòng kiểm tra kết nối mạng và thử lại.\nLỗi: ${errMsg}`,
        timestamp: new Date()
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleChatMessage = async (message: string) => {
    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: message,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);

    // Show progress stepper while waiting
    const loadingMsg: Message = {
      id: "loading",
      role: "system",
      content: "Đang xử lý yêu cầu...",
      isProgress: true,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, loadingMsg]);

    try {
      const response = await chatWithAgent(message, threadId);

      // Remove progress stepper
      setMessages(prev => prev.filter(m => m.id !== "loading"));

      if (response.success) {
        if (response.thread_id) setThreadId(response.thread_id);

        // Try to detect assessment report in chat response
        const cardData = parseChatReport(response.message);

        if (cardData) {
          // Assessment result detected → show short summary + card
          // Attach reasoning trail from response (same as LoanForm)
          const trail = response.reasoning_trail || [];
          if (trail.length) {
            cardData.reasoningTrail = trail;
          }

          // Always overwrite localStorage for latest assessment context,
          // kể cả khi trail rỗng để tránh hiển thị nhầm hồ sơ trước đó.
          localStorage.setItem("reasoning_trail", JSON.stringify({
            customerName: cardData.customerName,
            decision: cardData.status,
            threadId: response.assessment_id || response.thread_id,
            timestamp: new Date().toISOString(),
            trail,
          }));

          const statusLabel = cardData.status === "APPROVED" ? "Phê duyệt"
            : cardData.status === "REJECTED" ? "Từ chối" : "Cần xem xét";

          setMessages(prev => [...prev, {
            id: (Date.now() + 1).toString(),
            role: "system",
            content: `Khách hàng **${cardData.customerName}** được **${statusLabel}**. Xem chi tiết bên dưới.`,
            cardData,
            timestamp: new Date()
          }]);
        } else {
          // Normal chat message
          setMessages(prev => [...prev, {
            id: (Date.now() + 1).toString(),
            role: "system",
            content: response.message,
            timestamp: new Date()
          }]);
        }
      } else {
        setMessages(prev => [...prev, {
          id: (Date.now() + 1).toString(),
          role: "system",
          content: `❌ Lỗi: ${response.error || "Không xác định"}`,
          timestamp: new Date()
        }]);
      }
    } catch (error) {
      setMessages(prev => prev.filter(m => m.id !== "loading"));
      const errMsg = error instanceof Error ? error.message : "Unknown";
      const isRateLimit = errMsg.includes("giới hạn") || errMsg.includes("yêu cầu/ngày");
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: "system",
        content: isRateLimit
          ? `⚠️ ${errMsg}`
          : `❌ Không thể kết nối. Lỗi: ${errMsg}`,
        timestamp: new Date()
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen w-full bg-slate-100 overflow-hidden font-sans">
      <div className="w-[420px] flex-shrink-0 p-6 h-full hidden lg:block overflow-y-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-black text-primary tracking-tight">FinSafe <span className="text-slate-400 font-light">Core</span></h1>
          <p className="text-[11px] font-bold text-slate-400 uppercase tracking-[0.2em] mt-1">Hệ thống thẩm định nội bộ</p>
        </div>
        <LoanForm onSubmit={handleAssessment} isLoading={isLoading} />
      </div>

      <div className="flex-1 h-full relative z-10 lg:py-6 lg:pr-6">
        <div className="h-full bg-white shadow-2xl lg:rounded-3xl overflow-hidden border border-slate-200/50 flex flex-col">
          <ChatInterface messages={messages} onSendMessage={handleChatMessage} isLoading={isLoading} />
        </div>
      </div>
    </div>
  );
}
