import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(value?: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

export function formatDateTime(value?: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatConfidence(value?: number | null): string {
  if (value === null || value === undefined) return "—";
  return `${Math.round(value)}%`;
}

export const STATUS_META: Record<string, { label: string; color: string; bg: string }> = {
  PASS: { label: "Pass", color: "text-status-pass", bg: "bg-status-passBg" },
  REVIEW: { label: "Review", color: "text-status-review", bg: "bg-status-reviewBg" },
  NON_COMPLIANT: { label: "Non-Compliant", color: "text-status-fail", bg: "bg-status-failBg" },
  NOT_APPLICABLE: { label: "N/A", color: "text-status-na", bg: "bg-status-naBg" },
};

export const RESULT_META: Record<string, { label: string; color: string; bg: string }> = {
  COMPLIANT: { label: "Compliant", color: "text-status-pass", bg: "bg-status-passBg" },
  NON_COMPLIANT: { label: "Non-Compliant", color: "text-status-fail", bg: "bg-status-failBg" },
  REVIEW_REQUIRED: { label: "Review Required", color: "text-status-review", bg: "bg-status-reviewBg" },
};

export const SEVERITY_LABEL: Record<string, string> = {
  CRITICAL: "Critical",
  MAJOR: "Major",
  MINOR: "Minor",
  INFO: "Info",
};

export const STATUS_ICON: Record<string, string> = {
  PASS: "✓",
  REVIEW: "⚠",
  NON_COMPLIANT: "✕",
  NOT_APPLICABLE: "–",
};
