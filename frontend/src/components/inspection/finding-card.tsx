"use client";
import { useState } from "react";
import { Check, Eye, X as XIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { FindingStatusBadge, SeverityBadge, RuleTag } from "@/components/common/status-badge";
import { formatConfidence, formatDateTime } from "@/lib/utils";
import type { Finding } from "@/lib/types";

const STATUS_BORDER: Record<string, string> = {
  PASS: "border-l-status-pass",
  REVIEW: "border-l-status-review",
  NON_COMPLIANT: "border-l-status-fail",
  NOT_APPLICABLE: "border-l-status-na",
};

export function FindingCard({
  finding,
  onReview,
}: {
  finding: Finding;
  onReview: (findingId: number, decision: string, note?: string) => Promise<void>;
}) {
  const [pendingDecision, setPendingDecision] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const latestDecision = finding.officer_decisions[finding.officer_decisions.length - 1];

  async function submit(decision: string) {
    setSubmitting(true);
    try {
      await onReview(finding.id, decision, note || undefined);
      setPendingDecision(null);
      setNote("");
    } finally {
      setSubmitting(false);
    }
  }

  function toggle(decision: string) {
    setPendingDecision((current) => (current === decision ? null : decision));
  }

  return (
    <div className={`rounded-lg border border-l-4 border-line ${STATUS_BORDER[finding.status]} bg-white p-4`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <RuleTag>{finding.rule_code}</RuleTag>
          <span className="font-heading text-sm font-semibold text-ink-900">{finding.rule_name}</span>
        </div>
        <div className="flex items-center gap-2">
          <SeverityBadge severity={finding.severity} />
          <FindingStatusBadge status={finding.status} />
        </div>
      </div>

      <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
        {finding.detected_value && (
          <div>
            <dt className="text-xs font-medium uppercase text-ink-500">Detected</dt>
            <dd className="text-ink-900">{finding.detected_value}</dd>
          </div>
        )}
        {finding.expected_condition && (
          <div>
            <dt className="text-xs font-medium uppercase text-ink-500">Expected</dt>
            <dd className="text-ink-900">{finding.expected_condition}</dd>
          </div>
        )}
        {finding.confidence !== null && finding.confidence !== undefined && (
          <div>
            <dt className="text-xs font-medium uppercase text-ink-500">Confidence</dt>
            <dd className="text-ink-900">{formatConfidence(finding.confidence)}</dd>
          </div>
        )}
      </dl>

      {finding.explanation && (
        <p className="mt-3 rounded-md bg-canvas p-3 text-xs leading-relaxed text-ink-600">
          {finding.explanation}
        </p>
      )}

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-3">
        <div className="text-xs text-ink-500">
          {latestDecision ? (
            <>
              Officer decision:{" "}
              <span className="font-medium text-ink-900">
                {latestDecision.decision.replace(/_/g, " ").toLowerCase()}
              </span>{" "}
              by {latestDecision.officer_name ?? "officer"} on {formatDateTime(latestDecision.decided_at)}
              {latestDecision.note && <span className="italic"> — &quot;{latestDecision.note}&quot;</span>}
            </>
          ) : (
            "Officer decision: pending"
          )}
        </div>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => toggle("MARKED_FOR_REVIEW")}>
            <Eye className="h-3.5 w-3.5" /> Mark for Review
          </Button>
          <Button size="sm" variant="outline" onClick={() => toggle("DISMISSED")}>
            <XIcon className="h-3.5 w-3.5" /> Dismiss
          </Button>
          <Button size="sm" onClick={() => toggle("CONFIRMED")}>
            <Check className="h-3.5 w-3.5" /> Confirm
          </Button>
        </div>
      </div>

      {pendingDecision && (
        <div className="mt-3 space-y-2 rounded-md border border-line bg-canvas p-3">
          <Textarea
            placeholder="Optional note..."
            value={note}
            onChange={(e) => setNote(e.target.value)}
            className="bg-white text-xs"
            rows={2}
          />
          <div className="flex justify-end gap-2">
            <Button size="sm" variant="ghost" onClick={() => setPendingDecision(null)}>
              Cancel
            </Button>
            <Button size="sm" onClick={() => submit(pendingDecision)} disabled={submitting}>
              {submitting ? "Saving..." : "Confirm Action"}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
