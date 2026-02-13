import { useState, useEffect } from "react";
import { UserCheck, ShieldCheck, BarChart3, Landmark, Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

const STEPS = [
    { label: "Kiểm tra thông tin KH", icon: UserCheck },
    { label: "Tra cứu điểm CIC", icon: ShieldCheck },
    { label: "Phân tích DTI", icon: BarChart3 },
    { label: "Xác định hạn mức", icon: Landmark },
];

const STEP_DURATION_MS = 2200;

interface AssessmentProgressProps {
    /** When true, the stepper starts animating */
    active?: boolean;
}

export function AssessmentProgress({ active = true }: AssessmentProgressProps) {
    const [currentStep, setCurrentStep] = useState(0);

    useEffect(() => {
        if (!active) return;

        const interval = setInterval(() => {
            setCurrentStep((prev) => {
                if (prev >= STEPS.length - 1) return prev;
                return prev + 1;
            });
        }, STEP_DURATION_MS);

        return () => clearInterval(interval);
    }, [active]);

    // Overall progress (0 → 100)
    const progress = Math.min(((currentStep + 1) / STEPS.length) * 100, 100);

    return (
        <div className="w-full max-w-md">
            {/* Card container */}
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                {/* Header */}
                <div className="bg-gradient-to-r from-primary to-blue-600 px-5 py-3.5 flex items-center gap-3">
                    <Loader2 className="w-5 h-5 text-white animate-spin" />
                    <div>
                        <p className="text-white font-bold text-sm tracking-tight">Đang thẩm định hồ sơ</p>
                        <p className="text-white/70 text-[11px] font-medium">Vui lòng chờ trong giây lát...</p>
                    </div>
                </div>

                {/* Progress bar */}
                <div className="px-5 pt-4">
                    <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div
                            className="h-full bg-gradient-to-r from-primary to-blue-500 rounded-full transition-all duration-700 ease-out"
                            style={{ width: `${progress}%` }}
                        />
                    </div>
                    <p className="text-[10px] font-bold text-slate-400 mt-1.5 text-right uppercase tracking-wider">
                        {currentStep + 1}/{STEPS.length} bước
                    </p>
                </div>

                {/* Steps */}
                <div className="px-5 pb-5 pt-2 space-y-1">
                    {STEPS.map((step, idx) => {
                        const isDone = idx < currentStep;
                        const isActive = idx === currentStep;
                        const isWaiting = idx > currentStep;
                        const Icon = step.icon;

                        return (
                            <div
                                key={idx}
                                className={cn(
                                    "flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-500",
                                    isDone && "bg-emerald-50/80",
                                    isActive && "bg-primary/5 scale-[1.02]",
                                    isWaiting && "opacity-40"
                                )}
                            >
                                {/* Step indicator */}
                                <div
                                    className={cn(
                                        "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 transition-all duration-500",
                                        isDone && "bg-emerald-500 text-white shadow-sm shadow-emerald-200",
                                        isActive && "bg-primary/10 text-primary assessment-step-pulse",
                                        isWaiting && "bg-slate-100 text-slate-300"
                                    )}
                                >
                                    {isDone ? (
                                        <Check className="w-4 h-4" />
                                    ) : isActive ? (
                                        <Icon className="w-4 h-4" />
                                    ) : (
                                        <Icon className="w-4 h-4" />
                                    )}
                                </div>

                                {/* Label */}
                                <span
                                    className={cn(
                                        "text-sm font-semibold transition-colors duration-300",
                                        isDone && "text-emerald-700",
                                        isActive && "text-slate-800",
                                        isWaiting && "text-slate-400"
                                    )}
                                >
                                    {step.label}
                                </span>

                                {/* Active indicator */}
                                {isActive && (
                                    <div className="ml-auto flex items-center gap-1.5">
                                        <span className="flex gap-0.5">
                                            <span className="w-1.5 h-1.5 rounded-full bg-primary assessment-dot-bounce" style={{ animationDelay: "0ms" }} />
                                            <span className="w-1.5 h-1.5 rounded-full bg-primary assessment-dot-bounce" style={{ animationDelay: "150ms" }} />
                                            <span className="w-1.5 h-1.5 rounded-full bg-primary assessment-dot-bounce" style={{ animationDelay: "300ms" }} />
                                        </span>
                                    </div>
                                )}

                                {/* Done checkmark label */}
                                {isDone && (
                                    <span className="ml-auto text-[10px] font-bold text-emerald-600 uppercase tracking-wider">
                                        Hoàn tất
                                    </span>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}
