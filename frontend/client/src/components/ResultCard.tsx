import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatCurrency } from "@/lib/utils";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  CheckCircle2,
  XCircle,
  AlertCircle,
  AlertTriangle,
  User,
  Activity,
  Banknote,
  TrendingUp,
  ShieldCheck,
  CreditCard,
  Lightbulb,
  UserCheck,
  Calculator,
  BarChart3,
  Landmark,
  Info,
  GitBranch,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { ReasoningStep } from "@/lib/api";

export interface AssessmentResult {
  status: "APPROVED" | "REJECTED" | "REVIEW";
  customerName: string;
  age: number;
  income: number;
  cicScore: number;
  cicRating: string;
  badDebt: boolean;
  rate?: number;
  monthlyPayment?: number;
  dti?: number | string;
  limit?: number;
  requestedAmount?: number;
  reason: string;
  recommendation?: string;
  reasoningTrail?: ReasoningStep[];
}

interface ResultCardProps {
  data: AssessmentResult;
}

/* ── Helpers ── */
function StatusIcon({ status }: { status: string }) {
  if (status === "APPROVED") return <CheckCircle2 className="w-6 h-6" />;
  if (status === "REJECTED") return <XCircle className="w-6 h-6" />;
  return <AlertCircle className="w-6 h-6" />;
}

/** 
 * Parse recommendation text: separate the summary (first sentence/line) 
 * from detail bullets that repeat metrics already shown above. 
 */
function parseRecommendation(text: string): { summary: string; details: string[] } {
  const lines = text
    .split(/\n/)
    .map(line => line.replace(/^[•\-\*]\s*/, "").trim())
    .filter(line => line.length > 0);

  if (lines.length === 0) return { summary: text.trim(), details: [] };

  // First line that looks like a conclusion/summary (contains "phê duyệt", "từ chối", "dựa trên", etc.)
  const summaryIdx = lines.findIndex(l =>
    /phê duyệt|từ chối|xem xét|dựa trên|kết luận|đề xuất|hồ sơ/.test(l.toLowerCase())
  );

  if (summaryIdx >= 0) {
    const summary = lines[summaryIdx];
    const details = lines.filter((_, i) => i !== summaryIdx);
    return { summary, details };
  }

  // Fallback: first line = summary, rest = details
  return { summary: lines[0], details: lines.slice(1) };
}

function InfoRow({
  icon,
  label,
  value,
  valueClass,
}: {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
  valueClass?: string;
}) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-slate-100 last:border-b-0">
      <div className="flex items-center gap-2.5 text-slate-500 text-sm">
        {icon}
        <span>{label}</span>
      </div>
      <span className={cn("font-bold text-sm text-slate-800", valueClass)}>
        {value}
      </span>
    </div>
  );
}

/* ═══════════════════════════════════════
   Trail Step Meta — icon & color mapping
   ═══════════════════════════════════════ */

function getStepMeta(step: ReasoningStep) {
  const iconMap: Record<number, React.ReactNode> = {
    1: <UserCheck className="w-4 h-4" />,
    2: <ShieldCheck className="w-4 h-4" />,
    3: <Calculator className="w-4 h-4" />,
    4: <BarChart3 className="w-4 h-4" />,
    5: <Landmark className="w-4 h-4" />,
  };

  const decisionMeta: Record<string, { icon: React.ReactNode; color: string; bg: string; border: string; label: string }> = {
    PASS: {
      icon: <CheckCircle2 className="w-3 h-3" />,
      color: "text-emerald-700",
      bg: "bg-emerald-50",
      border: "border-emerald-200",
      label: "Đạt",
    },
    FAIL: {
      icon: <XCircle className="w-3 h-3" />,
      color: "text-red-700",
      bg: "bg-red-50",
      border: "border-red-200",
      label: "Không đạt",
    },
    REVIEW: {
      icon: <AlertTriangle className="w-3 h-3" />,
      color: "text-amber-700",
      bg: "bg-amber-50",
      border: "border-amber-200",
      label: "Cần xem xét",
    },
    CALCULATED: {
      icon: <Info className="w-3 h-3" />,
      color: "text-blue-700",
      bg: "bg-blue-50",
      border: "border-blue-200",
      label: "Đã tính",
    },
    ERROR: {
      icon: <XCircle className="w-3 h-3" />,
      color: "text-gray-700",
      bg: "bg-gray-50",
      border: "border-gray-200",
      label: "Lỗi",
    },
  };

  const stepIcon = iconMap[step.step] || <Info className="w-4 h-4" />;
  const meta = decisionMeta[step.decision] || decisionMeta.CALCULATED;

  return { stepIcon, ...meta };
}

/* ═══════════════════════════════════════
   Trail Dialog — Inline Popup
   ═══════════════════════════════════════ */

function TrailDialog({
  open,
  onOpenChange,
  trail,
  customerName,
  status,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  trail: ReasoningStep[];
  customerName: string;
  status: string;
}) {
  const decisionTheme = status === "APPROVED"
    ? { gradient: "from-emerald-500 to-green-600", label: "PHÊ DUYỆT", badge: "bg-emerald-100 text-emerald-800", summaryBg: "bg-emerald-50 border-emerald-200", summaryText: "text-emerald-700" }
    : status === "REJECTED"
      ? { gradient: "from-red-500 to-red-600", label: "TỪ CHỐI", badge: "bg-red-100 text-red-800", summaryBg: "bg-red-50 border-red-200", summaryText: "text-red-700" }
      : { gradient: "from-amber-500 to-amber-600", label: "CẦN XEM XÉT", badge: "bg-amber-100 text-amber-800", summaryBg: "bg-amber-50 border-amber-200", summaryText: "text-amber-700" };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-hidden p-0 rounded-2xl border-0 shadow-2xl gap-0">
        {/* ── Header ── */}
        <div className={cn("bg-gradient-to-r text-white px-6 py-5", decisionTheme.gradient)}>
          <DialogHeader>
            <div className="flex items-center justify-between">
              <div>
                <DialogTitle className="text-white text-lg font-bold tracking-tight flex items-center gap-2">
                  <GitBranch className="w-5 h-5" />
                  Luồng quyết định
                </DialogTitle>
                <DialogDescription className="text-white/80 text-sm mt-1">
                  {customerName}
                </DialogDescription>
              </div>
              <span className={cn("px-3 py-1 rounded-full text-xs font-bold", decisionTheme.badge)}>
                {decisionTheme.label}
              </span>
            </div>
          </DialogHeader>
        </div>

        {/* ── Timeline ── */}
        <div className="overflow-y-auto px-6 py-6 max-h-[60vh]">
          <div className="relative">
            {/* Vertical line */}
            <div className="absolute left-[18px] top-2 bottom-2 w-0.5 bg-slate-200" />

            <div className="space-y-4">
              {trail.map((step, idx) => {
                const meta = getStepMeta(step);
                return (
                  <div key={`${step.step}-${idx}`} className="relative flex gap-3">
                    {/* Node dot */}
                    <div
                      className={cn(
                        "relative z-10 w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 border-2 shadow-sm",
                        meta.bg, meta.border, meta.color
                      )}
                    >
                      {meta.stepIcon}
                    </div>

                    {/* Content */}
                    <div className={cn(
                      "flex-1 p-3.5 rounded-xl border transition-all",
                      meta.border, "bg-white hover:shadow-sm"
                    )}>
                      <div className="flex items-start justify-between gap-2 mb-1.5">
                        <div>
                          <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Bước {step.step}</p>
                          <h4 className="font-semibold text-slate-800 text-[13px] leading-tight">{step.action}</h4>
                        </div>
                        <span className={cn(
                          "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold flex-shrink-0",
                          meta.bg, meta.color
                        )}>
                          {meta.icon} {meta.label}
                        </span>
                      </div>

                      <p className="text-[13px] text-slate-700 font-medium mb-1">{step.result}</p>
                      <p className="text-[11px] text-slate-500 leading-relaxed">{step.detail}</p>

                      {step.policy_ref && (
                        <p className="text-[10px] text-slate-400 mt-2 italic flex items-center gap-1">
                          📌 {step.policy_ref}
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Summary footer */}
          <div className={cn("mt-5 p-3 rounded-xl border text-center", decisionTheme.summaryBg)}>
            <p className="text-sm font-semibold text-slate-700">
              {trail.length} bước thẩm định →{" "}
              <span className={cn("font-bold", decisionTheme.summaryText)}>
                {decisionTheme.label}
              </span>
            </p>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

/* ═══════════════════════════════════════
   Main ResultCard Component
   ═══════════════════════════════════════ */

export function ResultCard({ data }: ResultCardProps) {
  const [trailOpen, setTrailOpen] = useState(false);
  const isApproved = data.status === "APPROVED";
  const isRejected = data.status === "REJECTED";
  const normalizedTrail = (data.reasoningTrail || [])
    .filter(step => typeof step.step === "number" && step.step >= 1 && step.step <= 5)
    .sort((a, b) => a.step - b.step);
  const hasTrail = normalizedTrail.length > 0;

  // Theme colors
  const theme = isApproved
    ? {
      headerBg: "bg-gradient-to-r from-emerald-500 to-green-600",
      headerText: "text-white",
      badgeBg: "bg-white/20 text-white border-white/30",
      label: "Phê duyệt",
      accentColor: "text-emerald-600",
      accentBg: "bg-emerald-50",
      borderColor: "border-emerald-200",
    }
    : isRejected
      ? {
        headerBg: "bg-gradient-to-r from-red-500 to-rose-600",
        headerText: "text-white",
        badgeBg: "bg-white/20 text-white border-white/30",
        label: "Từ chối",
        accentColor: "text-red-600",
        accentBg: "bg-red-50",
        borderColor: "border-red-200",
      }
      : {
        headerBg: "bg-gradient-to-r from-amber-400 to-orange-500",
        headerText: "text-white",
        badgeBg: "bg-white/20 text-white border-white/30",
        label: "Cần xem xét",
        accentColor: "text-amber-600",
        accentBg: "bg-amber-50",
        borderColor: "border-amber-200",
      };

  const hasCicData = data.cicScore > 0;
  const hasFinancialData = data.monthlyPayment != null || (typeof data.dti === "number");
  const hasLimit = data.limit != null && data.limit > 0;

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      <Card className="overflow-hidden border-0 shadow-lg rounded-2xl">
        {/* ── Header ── */}
        <div className={cn("px-5 py-4 flex items-center justify-between", theme.headerBg)}>
          <div className={cn("flex items-center gap-3 font-bold text-lg", theme.headerText)}>
            <StatusIcon status={data.status} />
            <span className="tracking-tight">{data.status}</span>
          </div>
          <Badge
            variant="outline"
            className={cn("font-semibold text-xs px-3 py-1 rounded-full border", theme.badgeBg)}
          >
            {theme.label}
          </Badge>
        </div>

        <div className="p-5 space-y-5 bg-white">
          {/* ── Section 1: Thông tin khách hàng ── */}
          <div>
            <h4 className="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-3 flex items-center gap-1.5">
              <User className="w-3.5 h-3.5" /> Thông tin khách hàng
            </h4>
            <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
              <div className="flex items-baseline justify-between mb-1">
                <span className="font-bold text-slate-800 text-base">{data.customerName}</span>
                <span className="text-xs text-slate-500">{data.age} tuổi</span>
              </div>
              <div className="text-sm font-semibold text-primary">
                {formatCurrency(data.income)} / tháng
              </div>
            </div>
          </div>

          {/* ── Section 2: Chỉ số tín dụng CIC ── */}
          <div>
            <h4 className="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-3 flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5" /> Kết quả thẩm định
            </h4>
            <div className="bg-slate-50 rounded-xl p-4 border border-slate-100 space-y-0">
              <InfoRow
                icon={<ShieldCheck className="w-4 h-4" />}
                label="CIC Score"
                value={
                  hasCicData ? (
                    <span className="flex items-center gap-2">
                      <span
                        className={cn(
                          "text-lg font-black",
                          data.cicScore >= 700
                            ? "text-emerald-600"
                            : data.cicScore >= 600
                              ? "text-amber-500"
                              : "text-red-500"
                        )}
                      >
                        {data.cicScore}
                      </span>
                      <span className="text-xs text-slate-500 font-semibold">
                        ({data.cicRating})
                      </span>
                    </span>
                  ) : (
                    <span className="text-slate-400">N/A</span>
                  )
                }
              />
              <InfoRow
                icon={<AlertCircle className="w-4 h-4" />}
                label="Nợ xấu"
                value={
                  hasCicData ? (
                    data.badDebt ? (
                      <span className="text-red-600 font-black">CÓ</span>
                    ) : (
                      <span className="text-emerald-600 font-black">KHÔNG</span>
                    )
                  ) : (
                    <span className="text-slate-400">N/A</span>
                  )
                }
              />
              <InfoRow
                icon={<TrendingUp className="w-4 h-4" />}
                label="Lãi suất áp dụng"
                value={
                  data.rate != null ? (
                    `${data.rate}%/năm`
                  ) : (
                    <span className="text-slate-400">N/A</span>
                  )
                }
              />
              <InfoRow
                icon={<Banknote className="w-4 h-4" />}
                label="Tiền trả hàng tháng"
                value={
                  data.monthlyPayment != null ? (
                    formatCurrency(data.monthlyPayment)
                  ) : (
                    <span className="text-slate-400">N/A</span>
                  )
                }
              />
              <InfoRow
                icon={<CreditCard className="w-4 h-4" />}
                label="DTI"
                value={
                  typeof data.dti === "number" ? (
                    <span
                      className={cn(
                        "font-black",
                        data.dti <= 40
                          ? "text-emerald-600"
                          : data.dti <= 50
                            ? "text-amber-500"
                            : "text-red-500"
                      )}
                    >
                      {data.dti}%
                    </span>
                  ) : (
                    <span className="text-slate-400">{data.dti || "N/A"}</span>
                  )
                }
              />
              <InfoRow
                icon={<Banknote className="w-4 h-4" />}
                label="Hạn mức được duyệt"
                value={
                  hasLimit ? (
                    <span className={cn("text-base font-black", theme.accentColor)}>
                      {formatCurrency(data.limit!)}
                    </span>
                  ) : (
                    <span className="text-slate-400">N/A</span>
                  )
                }
              />
            </div>
          </div>

          {/* ── Section 3: Diễn giải chi tiết ── */}
          {(data.reason || data.recommendation) && (() => {
            // Combine reason + recommendation into one section
            const parts: string[] = [];
            if (data.reason) parts.push(data.reason);
            if (data.recommendation) {
              const { summary, details } = parseRecommendation(data.recommendation);
              parts.push(summary);
              parts.push(...details);
            }
            // Deduplicate and clean
            const allText = Array.from(new Set(parts))
              .map(t => t.replace(/\*\*/g, "").trim())
              .filter(t => t.length > 0);

            return (
              <div>
                <h4 className="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-3 flex items-center gap-1.5">
                  <Info className="w-3.5 h-3.5" /> Diễn giải chi tiết
                </h4>
                <div
                  className={cn(
                    "rounded-xl border p-4 space-y-2",
                    theme.accentBg,
                    theme.borderColor,
                  )}
                >
                  {allText.map((text, idx) => (
                    <p key={idx} className="text-[13px] leading-relaxed text-slate-700">
                      {idx > 0 && <span className="text-slate-400 mr-1.5">•</span>}
                      {text}
                    </p>
                  ))}
                </div>
              </div>
            );
          })()}

          {/* ── Section 4: Đề xuất (chỉ hiện khi REVIEW — DTI cận ngưỡng, cần điều chỉnh) ── */}
          {data.status === "REVIEW" && (
            <div>
              <h4 className="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-3 flex items-center gap-1.5">
                <Lightbulb className="w-3.5 h-3.5" /> Đề xuất
              </h4>
              <div className="rounded-xl border border-amber-200 bg-amber-50/50 p-4 space-y-2">
                {typeof data.dti === "number" && data.dti > 40 && data.dti <= 50 && (
                  <p className="text-[13px] leading-relaxed text-amber-800 flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    <span>DTI {data.dti}% vượt ngưỡng 40%. Đề xuất <strong>giảm hạn mức vay</strong> hoặc <strong>tăng thời hạn vay</strong> để giảm tỷ lệ DTI về mức cho phép.</span>
                  </p>
                )}
                {data.limit != null && data.requestedAmount != null && data.requestedAmount > data.limit && (
                  <p className="text-[13px] leading-relaxed text-amber-800 flex items-start gap-2">
                    <Lightbulb className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    <span>Có thể xem xét điều chỉnh khoản vay xuống mức hạn mức được duyệt {formatCurrency(data.limit)} để đảm bảo khả năng trả nợ.</span>
                  </p>
                )}
                {!(typeof data.dti === "number" && data.dti > 40) && (
                  <p className="text-[13px] leading-relaxed text-amber-800 flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    <span>Hồ sơ cần được xem xét bởi chuyên viên cấp cao trước khi đưa ra quyết định cuối cùng.</span>
                  </p>
                )}
              </div>
            </div>
          )}

          {/* ── Section 5: CTA — Xem luồng quyết định ── */}
          {hasTrail && (
            <button
              onClick={() => setTrailOpen(true)}
              className="w-full flex items-center justify-center gap-2 py-3 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 hover:border-slate-300 transition-all group cursor-pointer"
            >
              <GitBranch className="w-4 h-4 text-slate-400 group-hover:text-primary transition-colors" />
              <span className="text-sm font-semibold text-slate-500 group-hover:text-primary transition-colors">
                Xem luồng quyết định
              </span>
            </button>
          )}
        </div>
      </Card>

      {/* ── Trail Popup ── */}
      {hasTrail && (
        <TrailDialog
          open={trailOpen}
          onOpenChange={setTrailOpen}
          trail={normalizedTrail}
          customerName={data.customerName}
          status={data.status}
        />
      )}
    </div>
  );
}
