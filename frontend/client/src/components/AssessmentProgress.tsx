import { useState, useEffect } from "react";
import { UserCheck, ShieldCheck, BarChart3, Landmark, Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

const STEPS = [
    { label: "Kiểm tra thông tin KH", icon: UserCheck },
    { label: "Tra cứu điểm CIC", icon: ShieldCheck },
    { label: "Phân tích DTI", icon: BarChart3 },
    { label: "Xác định hạn mức", icon: Landmark },
];

/** Duration for each step before transitioning */
const STEP_ACTIVE_MS = 1800;
/** Brief pause showing checkmark before fading out */
const STEP_DONE_MS = 600;

type StepPhase = "active" | "done" | "fadeout" | "hidden";

interface AssessmentProgressProps {
    active?: boolean;
}

export function AssessmentProgress({ active = true }: AssessmentProgressProps) {
    const [currentStep, setCurrentStep] = useState(0);
    const [phase, setPhase] = useState<StepPhase>("active");

    useEffect(() => {
        if (!active) return;

        let timer: ReturnType<typeof setTimeout>;

        if (phase === "active") {
            // Step is running → after delay, mark as done
            timer = setTimeout(() => setPhase("done"), STEP_ACTIVE_MS);
        } else if (phase === "done") {
            // Show checkmark briefly → then fade out
            timer = setTimeout(() => setPhase("fadeout"), STEP_DONE_MS);
        } else if (phase === "fadeout") {
            // After fade animation → move to next step or stay on last
            timer = setTimeout(() => {
                if (currentStep < STEPS.length - 1) {
                    setCurrentStep((prev) => prev + 1);
                    setPhase("active");
                }
                // Last step stays in "fadeout" (will be removed when result arrives)
            }, 300);
        }

        return () => clearTimeout(timer);
    }, [active, phase, currentStep]);

    const step = STEPS[currentStep];
    if (!step) return null;
    const Icon = step.icon;

    return (
        <div
            className={cn(
                "inline-flex items-center gap-2.5 transition-all duration-300",
                phase === "fadeout" && "opacity-0 -translate-y-1",
                phase === "hidden" && "hidden"
            )}
        >
            {/* Icon / spinner / check */}
            {phase === "done" ? (
                <div className="w-6 h-6 rounded-full bg-emerald-500 flex items-center justify-center shadow-sm shadow-emerald-200 animate-in zoom-in duration-200">
                    <Check className="w-3.5 h-3.5 text-white" />
                </div>
            ) : (
                <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center assessment-step-pulse">
                    <Loader2 className="w-3.5 h-3.5 text-primary animate-spin" />
                </div>
            )}

            {/* Label */}
            <span
                className={cn(
                    "text-[13px] font-semibold transition-colors duration-300",
                    phase === "active" && "text-slate-700",
                    phase === "done" && "text-emerald-700"
                )}
            >
                {phase === "done" ? `${step.label} ✓` : `${step.label}...`}
            </span>

            {/* Bouncing dots (active only) */}
            {phase === "active" && (
                <span className="flex gap-0.5 ml-1">
                    <span className="w-1 h-1 rounded-full bg-primary/60 assessment-dot-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-1 h-1 rounded-full bg-primary/60 assessment-dot-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-1 h-1 rounded-full bg-primary/60 assessment-dot-bounce" style={{ animationDelay: "300ms" }} />
                </span>
            )}
        </div>
    );
}
