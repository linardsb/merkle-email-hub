"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useSession } from "next-auth/react";
import { X, ArrowRight, GripVertical, MousePointer, Monitor, ShieldCheck } from "../icons";

const ONBOARDING_KEY = "builder-onboarding-completed";

interface OnboardingStep {
  title: string;
  description: string;
  icon: React.ElementType;
  highlightSelector: string;
}

const STEPS: OnboardingStep[] = [
  {
    title: "Drag a section",
    description: "Pick a component from the palette and drop it onto the canvas.",
    icon: GripVertical,
    highlightSelector: "[data-builder-palette]",
  },
  {
    title: "Click to configure",
    description: "Select any section to open its property panel on the right.",
    icon: MousePointer,
    highlightSelector: "[data-builder-canvas]",
  },
  {
    title: "Preview your email",
    description: "Use the device buttons to see how it looks on mobile and tablet.",
    icon: Monitor,
    highlightSelector: "[data-builder-toolbar]",
  },
  {
    title: "Run quality checks",
    description: "Click Run QA to validate accessibility, compatibility, and more.",
    icon: ShieldCheck,
    highlightSelector: "[data-builder-qa]",
  },
];

export function BuilderOnboarding() {
  const session = useSession();
  const userRole = session.data?.user?.role;
  const [step, setStep] = useState(0);
  const [dismissed, setDismissed] = useState(true);
  const highlightRef = useRef<Element | null>(null);

  // Check if onboarding should show
  useEffect(() => {
    // Don't show for developers
    if (userRole === "developer") return;
    // Check localStorage
    if (typeof window === "undefined") return;
    const stored = localStorage.getItem(ONBOARDING_KEY);
    if (typeof stored === "string" && stored === "true") return;
    setDismissed(false);
  }, [userRole]);

  // Highlight target element
  useEffect(() => {
    if (dismissed) return;

    const currentStep = STEPS[step];
    if (!currentStep) return;

    // Remove previous highlight
    if (highlightRef.current) {
      highlightRef.current.classList.remove("ring-2", "ring-interactive", "animate-pulse");
      highlightRef.current = null;
    }

    // Add new highlight
    requestAnimationFrame(() => {
      const el = document.querySelector(currentStep.highlightSelector);
      if (el) {
        el.classList.add("ring-2", "ring-interactive", "animate-pulse");
        highlightRef.current = el;
      }
    });

    return () => {
      if (highlightRef.current) {
        highlightRef.current.classList.remove("ring-2", "ring-interactive", "animate-pulse");
        highlightRef.current = null;
      }
    };
  }, [step, dismissed]);

  const complete = useCallback(() => {
    setDismissed(true);
    localStorage.setItem(ONBOARDING_KEY, "true");
    if (highlightRef.current) {
      highlightRef.current.classList.remove("ring-2", "ring-interactive", "animate-pulse");
      highlightRef.current = null;
    }
  }, []);

  const handleNext = useCallback(() => {
    if (step < STEPS.length - 1) {
      setStep((s) => s + 1);
    } else {
      complete();
    }
  }, [step, complete]);

  if (dismissed) return null;

  const currentStep = STEPS[step];
  if (!currentStep) return null;
  const StepIcon = currentStep.icon;

  return (
    <div className="border-border bg-card fixed bottom-6 left-6 z-50 w-80 rounded-lg border p-4 shadow-lg">
      {/* Close button */}
      <button
        type="button"
        onClick={complete}
        className="text-muted-foreground hover:bg-accent hover:text-foreground absolute top-2 right-2 rounded p-1 transition-colors"
        aria-label="Close onboarding"
      >
        <X className="h-3.5 w-3.5" />
      </button>

      {/* Step content */}
      <div className="flex items-start gap-3">
        <div className="bg-interactive/10 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md">
          <StepIcon className="text-interactive h-4 w-4" />
        </div>
        <div className="flex-1 pr-4">
          <h3 className="text-foreground text-sm font-semibold">{currentStep.title}</h3>
          <p className="text-muted-foreground mt-0.5 text-xs">{currentStep.description}</p>
        </div>
      </div>

      {/* Footer: dots + buttons */}
      <div className="mt-4 flex items-center justify-between">
        {/* Step dots */}
        <div className="flex gap-1.5">
          {STEPS.map((_, i) => (
            <div
              key={i}
              className={`h-1.5 w-1.5 rounded-full transition-colors ${
                i === step ? "bg-interactive" : "bg-muted-foreground/30"
              }`}
            />
          ))}
        </div>

        {/* Buttons */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={complete}
            className="text-muted-foreground hover:text-foreground text-xs transition-colors"
          >
            {"Skip"}
          </button>
          <button
            type="button"
            onClick={handleNext}
            className="bg-interactive text-interactive-foreground hover:bg-interactive/90 flex items-center gap-1 rounded-md px-3 py-1 text-xs font-medium transition-colors"
          >
            {step < STEPS.length - 1 ? (
              <>
                {"Next"}
                <ArrowRight className="h-3 w-3" />
              </>
            ) : (
              "Done"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
