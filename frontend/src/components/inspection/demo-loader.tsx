"use client";
import { CheckCircle2, AlertTriangle, XCircle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import type { DemoScenarioKey } from "@/lib/types";

const SCENARIOS: {
  key: DemoScenarioKey;
  label: string;
  description: string;
  icon: React.ReactNode;
  tone: string;
}[] = [
  {
    key: "compliant",
    label: "Compliant",
    description: "A fully-declared domestic packaged food product.",
    icon: <CheckCircle2 className="h-5 w-5" />,
    tone: "text-status-pass",
  },
  {
    key: "non_compliant",
    label: "Non-Compliant",
    description: "An imported multipack with missing mandatory declarations.",
    icon: <XCircle className="h-5 w-5" />,
    tone: "text-status-fail",
  },
  {
    key: "review",
    label: "Review Required",
    description: "OCR confidence & readability uncertainty — nothing outright missing.",
    icon: <AlertTriangle className="h-5 w-5" />,
    tone: "text-status-review",
  },
];

export function DemoLoader({
  onLoad,
  loading,
}: {
  onLoad: (scenario: DemoScenarioKey) => void;
  loading: DemoScenarioKey | null;
}) {
  return (
    <Card className="border-accent/30 bg-accent-50/40">
      <CardContent className="pt-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-accent-700">
          Load Hackathon Demo
        </p>
        <p className="mt-1 text-sm text-ink-600">
          Instantly populate a realistic inspection and walk it through the real OCR →
          extraction → compliance pipeline — nothing here is a pre-baked screenshot.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          {SCENARIOS.map((s) => (
            <button
              key={s.key}
              onClick={() => onLoad(s.key)}
              disabled={!!loading}
              className="flex flex-col items-start gap-2 rounded-lg border border-line bg-white p-4 text-left transition-colors hover:border-accent disabled:opacity-60"
            >
              <span className={s.tone}>{loading === s.key ? <Spinner /> : s.icon}</span>
              <span className="font-heading text-sm font-semibold text-ink-900">{s.label}</span>
              <span className="text-xs text-ink-500">{s.description}</span>
            </button>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
