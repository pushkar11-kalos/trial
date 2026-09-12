"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { CheckCircle2, FileText, FileType2, ShieldCheck } from "lucide-react";
import { PageShell } from "@/components/layout/page-shell";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";
import { PageSpinner, Spinner } from "@/components/ui/spinner";
import { OverallResultBadge, RuleTag } from "@/components/common/status-badge";
import { EvidenceThumbnails, DeclarationsTable } from "@/components/inspection/ocr-panel";
import { FindingCard } from "@/components/inspection/finding-card";
import * as api from "@/lib/api";
import { formatConfidence, formatDate, formatDateTime } from "@/lib/utils";
import type { Inspection } from "@/lib/types";

export default function InspectionDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);

  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [finalizing, setFinalizing] = useState(false);
  const [generating, setGenerating] = useState<"PDF" | "DOCX" | null>(null);
  const [reportLinks, setReportLinks] = useState<{ pdf?: string; docx?: string }>({});

  async function load() {
    try {
      const insp = await api.getInspection(id);
      setInspection(insp);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load inspection");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function handleAnalyze() {
    setAnalyzing(true);
    setError(null);
    try {
      await api.runCompliance(id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Compliance analysis failed");
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleReview(findingId: number, decision: string, note?: string) {
    await api.reviewFinding(findingId, decision, note);
    await load();
  }

  async function handleFinalize() {
    setFinalizing(true);
    setError(null);
    try {
      await api.finalizeInspection(id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not finalize inspection");
    } finally {
      setFinalizing(false);
    }
  }

  async function handleGenerateReport(type: "PDF" | "DOCX") {
    setGenerating(type);
    setError(null);
    try {
      const report = type === "PDF" ? await api.generatePdfReport(id) : await api.generateDocxReport(id);
      setReportLinks((prev) => ({ ...prev, [type.toLowerCase()]: report.url }));
    } catch (e) {
      setError(e instanceof Error ? e.message : `Could not generate ${type} report`);
    } finally {
      setGenerating(null);
    }
  }

  if (loading) {
    return (
      <PageShell title="Inspection">
        <PageSpinner label="Loading inspection..." />
      </PageShell>
    );
  }

  if (!inspection) {
    return (
      <PageShell title="Inspection">
        <Alert variant="destructive">{error ?? "Inspection not found."}</Alert>
      </PageShell>
    );
  }

  const run = inspection.latest_compliance_run;

  return (
    <PageShell title={inspection.product.name}>
      <div className="space-y-6">
        {error && <Alert variant="destructive">{error}</Alert>}

        <Card>
          <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-4">
            <div>
              <CardTitle className="flex flex-wrap items-center gap-2">
                {inspection.product.name} <RuleTag>{inspection.reference_code}</RuleTag>
              </CardTitle>
              <CardDescription>
                {inspection.product.brand ? `${inspection.product.brand} · ` : ""}
                {inspection.supply_type === "IMPORTED" ? "Imported" : "Domestic"}
                {inspection.product.category ? ` · ${inspection.product.category}` : ""} · Batch{" "}
                {inspection.batch_lot || "—"}
              </CardDescription>
            </div>
            <OverallResultBadge result={inspection.overall_result} />
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 text-sm sm:grid-cols-3">
              <InfoItem label="Inspector" value={inspection.inspector.full_name} />
              <InfoItem label="Location" value={inspection.inspection_location || "—"} />
              <InfoItem label="Date" value={formatDate(inspection.inspection_date)} />
              <InfoItem label="Manufacturer / Importer" value={inspection.manufacturer_name || "—"} />
              <InfoItem label="Status" value={inspection.status.replace(/_/g, " ")} />
              <InfoItem
                label="Compliance Score"
                value={
                  inspection.overall_score !== null && inspection.overall_score !== undefined
                    ? formatConfidence(inspection.overall_score)
                    : "—"
                }
              />
            </div>
            <div className="mt-4">
              <EvidenceThumbnails evidence={inspection.evidence_items} />
            </div>
          </CardContent>
        </Card>

        {inspection.declarations.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Extracted Declarations</CardTitle>
            </CardHeader>
            <CardContent>
              <DeclarationsTable
                declarations={inspection.declarations}
                onEdit={async (declId, value) => {
                  await api.updateDeclaration(declId, value);
                  await load();
                }}
              />
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Compliance Findings</CardTitle>
            {!run && (
              <Button onClick={handleAnalyze} disabled={analyzing || inspection.declarations.length === 0}>
                {analyzing ? <Spinner className="text-white" /> : <ShieldCheck className="h-4 w-4" />}
                {analyzing ? "Analyzing..." : "Analyze Compliance"}
              </Button>
            )}
          </CardHeader>
          <CardContent>
            {!run && (
              <p className="text-sm text-ink-500">
                {inspection.declarations.length === 0
                  ? "Run OCR and extract declarations before analyzing compliance."
                  : "No compliance analysis has been run yet."}
              </p>
            )}
            {run && (
              <div className="space-y-3">
                <p className="text-xs text-ink-500">
                  Evaluated against{" "}
                  <RuleTag>
                    {run.rule_pack_name} ({run.rule_pack_version})
                  </RuleTag>{" "}
                  on {formatDateTime(run.run_at)}
                </p>
                {run.findings.map((f) => (
                  <FindingCard key={f.id} finding={f} onReview={handleReview} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {run && (
          <Card>
            <CardHeader>
              <CardTitle>Finalize &amp; Reports</CardTitle>
              <CardDescription>
                Generate the professional PDF and editable DOCX compliance reports, then finalize
                the inspection.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap items-center gap-3">
              <Button
                variant="outline"
                onClick={() => handleGenerateReport("PDF")}
                disabled={generating === "PDF"}
              >
                {generating === "PDF" ? <Spinner /> : <FileText className="h-4 w-4" />} Generate PDF
              </Button>
              <Button
                variant="outline"
                onClick={() => handleGenerateReport("DOCX")}
                disabled={generating === "DOCX"}
              >
                {generating === "DOCX" ? <Spinner /> : <FileType2 className="h-4 w-4" />} Generate DOCX
              </Button>
              {reportLinks.pdf && (
                <a
                  href={api.mediaUrl(reportLinks.pdf)}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm text-accent underline"
                >
                  Open PDF
                </a>
              )}
              {reportLinks.docx && (
                <a
                  href={api.mediaUrl(reportLinks.docx)}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm text-accent underline"
                >
                  Open DOCX
                </a>
              )}
              <div className="flex-1" />
              {inspection.status !== "FINALIZED" ? (
                <Button onClick={handleFinalize} disabled={finalizing}>
                  {finalizing ? <Spinner className="text-white" /> : <CheckCircle2 className="h-4 w-4" />}
                  {finalizing ? "Finalizing..." : "Finalize Inspection"}
                </Button>
              ) : (
                <span className="text-sm font-medium text-status-pass">
                  Finalized {formatDateTime(inspection.finalized_at)}
                </span>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </PageShell>
  );
}

function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-ink-500">{label}</p>
      <p className="text-ink-900">{value}</p>
    </div>
  );
}
