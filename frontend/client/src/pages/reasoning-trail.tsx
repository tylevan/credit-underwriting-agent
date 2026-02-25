/**
 * Reasoning Trail Page
 * Hiển thị chi tiết từng bước thẩm định dạng timeline.
 *
 * Hai chế độ:
 *   /trail/:threadId  → fetch từ API (dashboard), back → /dashboard
 *   /trail            → đọc localStorage (home), back → /
 */
import { useState, useEffect } from "react";
import { useLocation, useRoute } from "wouter";
import { type ReasoningStep, API_BASE } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
    ArrowLeft,
    UserCheck,
    ShieldCheck,
    Calculator,
    BarChart3,
    Landmark,
    CheckCircle2,
    XCircle,
    AlertTriangle,
    Info,
    Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";

/* ── Step icon & color mapping ── */
function getStepMeta(step: ReasoningStep) {
    const iconMap: Record<number, React.ReactNode> = {
        1: <UserCheck className="w-5 h-5" />,
        2: <ShieldCheck className="w-5 h-5" />,
        3: <Calculator className="w-5 h-5" />,
        4: <BarChart3 className="w-5 h-5" />,
        5: <Landmark className="w-5 h-5" />,
    };

    const decisionMeta: Record<string, { icon: React.ReactNode; color: string; bg: string; border: string; label: string }> = {
        PASS: {
            icon: <CheckCircle2 className="w-4 h-4" />,
            color: "text-emerald-700",
            bg: "bg-emerald-50",
            border: "border-emerald-200",
            label: "Đạt",
        },
        FAIL: {
            icon: <XCircle className="w-4 h-4" />,
            color: "text-red-700",
            bg: "bg-red-50",
            border: "border-red-200",
            label: "Không đạt",
        },
        REVIEW: {
            icon: <AlertTriangle className="w-4 h-4" />,
            color: "text-amber-700",
            bg: "bg-amber-50",
            border: "border-amber-200",
            label: "Cần xem xét",
        },
        CALCULATED: {
            icon: <Info className="w-4 h-4" />,
            color: "text-blue-700",
            bg: "bg-blue-50",
            border: "border-blue-200",
            label: "Đã tính",
        },
        ERROR: {
            icon: <XCircle className="w-4 h-4" />,
            color: "text-gray-700",
            bg: "bg-gray-50",
            border: "border-gray-200",
            label: "Lỗi",
        },
    };

    const stepIcon = iconMap[step.step] || <Info className="w-5 h-5" />;
    const meta = decisionMeta[step.decision] || decisionMeta.CALCULATED;

    return { stepIcon, ...meta };
}

function sanitizeTrail(trail: ReasoningStep[] = []): ReasoningStep[] {
    return trail
        .filter(step => typeof step.step === "number" && step.step >= 1 && step.step <= 5)
        .sort((a, b) => a.step - b.step);
}

/* ── Trail data interface ── */
export interface TrailData {
    customerName: string;
    decision: string;
    threadId: string;
    timestamp: string;
    trail: ReasoningStep[];
}

function getTrailFromLocalStorage(): TrailData | null {
    try {
        const raw = localStorage.getItem("reasoning_trail");
        return raw ? JSON.parse(raw) : null;
    } catch {
        return null;
    }
}

export default function ReasoningTrailPage() {
    const [, setLocation] = useLocation();
    const [, params] = useRoute("/trail/:assessmentId");
    const assessmentId = params?.assessmentId;

    const [data, setData] = useState<TrailData | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Back destination depends on how we got here
    const backPath = assessmentId ? "/dashboard" : "/";

    useEffect(() => {
        if (assessmentId) {
            // Mode 1: Fetch from API
            setLoading(true);
            fetch(`${API_BASE}/dashboard/assessments/${assessmentId}`)
                .then(res => res.json())
                .then(json => {
                    if (json.success && json.data) {
                        const d = json.data;
                        setData({
                            customerName: d.customer_name || `KH #${d.customer_id}`,
                            decision: d.decision,
                            threadId: d.assessment_id,
                            timestamp: d.created_at,
                            trail: sanitizeTrail(d.reasoning_trail || []),
                        });
                    } else {
                        setError("Không tìm thấy hồ sơ.");
                    }
                })
                .catch(() => setError("Không thể kết nối tới server."))
                .finally(() => setLoading(false));
        } else {
            // Mode 2: Fallback to localStorage (from home page)
            const local = getTrailFromLocalStorage();
            setData(local ? { ...local, trail: sanitizeTrail(local.trail || []) } : null);
        }
    }, [assessmentId]);

    if (loading) {
        return (
            <div className="min-h-screen bg-slate-100 flex items-center justify-center p-6">
                <Loader2 className="w-8 h-8 text-slate-400 animate-spin" />
            </div>
        );
    }

    if (error || !data || !data.trail.length) {
        return (
            <div className="min-h-screen bg-slate-100 flex items-center justify-center p-6">
                <Card className="p-8 text-center max-w-md">
                    <div className="text-6xl mb-4">📋</div>
                    <h2 className="text-xl font-bold text-slate-800 mb-2">{error || "Chưa có dữ liệu thẩm định"}</h2>
                    <p className="text-sm text-slate-500 mb-6">
                        Hãy thực hiện thẩm định một hồ sơ trước, sau đó quay lại đây để xem chi tiết quá trình.
                    </p>
                    <Button onClick={() => setLocation(backPath)} variant="outline">
                        <ArrowLeft className="w-4 h-4 mr-2" /> Quay lại
                    </Button>
                </Card>
            </div>
        );
    }

    const decisionTheme = data.decision === "APPROVED"
        ? { bg: "from-emerald-500 to-emerald-600", label: "PHÊ DUYỆT", badge: "bg-emerald-100 text-emerald-800" }
        : data.decision === "REJECTED"
            ? { bg: "from-red-500 to-red-600", label: "TỪ CHỐI", badge: "bg-red-100 text-red-800" }
            : { bg: "from-amber-500 to-amber-600", label: "CẦN XEM XÉT", badge: "bg-amber-100 text-amber-800" };

    return (
        <div className="min-h-screen bg-slate-100">
            {/* Header */}
            <div className={cn("bg-gradient-to-r text-white", decisionTheme.bg)}>
                <div className="max-w-3xl mx-auto px-6 py-6">
                    <div className="flex items-center gap-3 mb-4">
                        <button
                            onClick={() => setLocation(backPath)}
                            className="p-2 rounded-lg bg-white/20 hover:bg-white/30 transition-colors"
                        >
                            <ArrowLeft className="w-4 h-4" />
                        </button>
                        <h1 className="text-lg font-bold">Quá trình thẩm định</h1>
                    </div>

                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-white/80 text-sm">Khách hàng</p>
                            <p className="text-xl font-bold">{data.customerName}</p>
                        </div>
                        <div className="text-right">
                            <span className={cn("px-3 py-1 rounded-full text-xs font-bold", decisionTheme.badge)}>
                                {decisionTheme.label}
                            </span>
                            <p className="text-white/60 text-xs mt-2">
                                {new Date(data.timestamp).toLocaleString("vi-VN")}
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Timeline */}
            <div className="max-w-3xl mx-auto px-6 py-8">
                <div className="relative">
                    {/* Vertical line */}
                    <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-slate-200" />

                    {data.trail.map((step, idx) => {
                        const meta = getStepMeta(step);
                        const isLast = idx === data.trail.length - 1;

                        return (
                            <div key={step.step} className={cn("relative flex gap-4 pb-8", isLast && "pb-0")}>
                                {/* Node dot */}
                                <div
                                    className={cn(
                                        "relative z-10 w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0 border-2 shadow-sm",
                                        meta.bg, meta.border, meta.color
                                    )}
                                >
                                    {meta.stepIcon}
                                </div>

                                {/* Content card */}
                                <Card className={cn(
                                    "flex-1 p-4 border shadow-sm transition-all hover:shadow-md",
                                    meta.border
                                )}>
                                    {/* Header */}
                                    <div className="flex items-start justify-between mb-2">
                                        <div>
                                            <p className="text-xs text-slate-400 font-medium">BƯỚC {step.step}</p>
                                            <h3 className="font-semibold text-slate-800 text-sm">{step.action}</h3>
                                        </div>
                                        <span className={cn(
                                            "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold",
                                            meta.bg, meta.color
                                        )}>
                                            {meta.icon} {meta.label}
                                        </span>
                                    </div>

                                    {/* Result */}
                                    <p className="text-sm text-slate-700 font-medium mb-2">
                                        {step.result}
                                    </p>

                                    {/* Detail */}
                                    <p className="text-xs text-slate-500 leading-relaxed">
                                        {step.detail}
                                    </p>

                                    {/* Policy ref */}
                                    {step.policy_ref && (
                                        <p className="text-[11px] text-slate-400 mt-2 italic">
                                            📌 {step.policy_ref}
                                        </p>
                                    )}
                                </Card>
                            </div>
                        );
                    })}
                </div>

                {/* Summary footer */}
                <div className={cn(
                    "mt-8 p-4 rounded-xl border text-center",
                    data.decision === "APPROVED" ? "bg-emerald-50 border-emerald-200" :
                        data.decision === "REJECTED" ? "bg-red-50 border-red-200" :
                            "bg-amber-50 border-amber-200"
                )}>
                    <p className="text-sm font-semibold text-slate-700">
                        Kết luận: {data.trail.length} bước thẩm định →{" "}
                        <span className={cn(
                            "font-bold",
                            data.decision === "APPROVED" ? "text-emerald-700" :
                                data.decision === "REJECTED" ? "text-red-700" : "text-amber-700"
                        )}>
                            {decisionTheme.label}
                        </span>
                    </p>
                    <p className="text-xs text-slate-500 mt-1">Thread ID: {data.threadId}</p>
                </div>
            </div>
        </div>
    );
}
