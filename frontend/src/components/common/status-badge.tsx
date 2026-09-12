import { Badge } from "@/components/ui/badge";
import { STATUS_ICON, STATUS_META, RESULT_META, SEVERITY_LABEL } from "@/lib/utils";
import type { FindingStatus, OverallResult, Severity } from "@/lib/types";

const VARIANT_BY_STATUS: Record<string, "pass" | "review" | "fail" | "na"> = {
  PASS: "pass",
  REVIEW: "review",
  NON_COMPLIANT: "fail",
  NOT_APPLICABLE: "na",
};

export function FindingStatusBadge({ status }: { status: FindingStatus }) {
  const meta = STATUS_META[status];
  return (
    <Badge variant={VARIANT_BY_STATUS[status]}>
      <span aria-hidden>{STATUS_ICON[status]}</span> {meta?.label ?? status}
    </Badge>
  );
}

const RESULT_VARIANT: Record<string, "pass" | "review" | "fail"> = {
  COMPLIANT: "pass",
  NON_COMPLIANT: "fail",
  REVIEW_REQUIRED: "review",
};

export function OverallResultBadge({ result }: { result?: OverallResult | null }) {
  if (!result) return <Badge variant="outline">Not analyzed</Badge>;
  const meta = RESULT_META[result];
  return <Badge variant={RESULT_VARIANT[result]}>{meta?.label ?? result}</Badge>;
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  return <Badge variant="outline">{SEVERITY_LABEL[severity] ?? severity}</Badge>;
}

export function RuleTag({ children }: { children: React.ReactNode }) {
  return <span className="mc-tag">{children}</span>;
}
