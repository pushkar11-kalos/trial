"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, ScanText } from "lucide-react";
import { PageShell } from "@/components/layout/page-shell";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/spinner";
import { EvidenceChain } from "@/components/common/evidence-chain";
import { RuleTag } from "@/components/common/status-badge";
import { DemoLoader } from "@/components/inspection/demo-loader";
import { EvidenceUploader } from "@/components/inspection/evidence-uploader";
import { ProductInfoForm } from "@/components/inspection/product-info-form";
import { DeclarationsTable, EvidenceThumbnails, OcrResultsList } from "@/components/inspection/ocr-panel";
import * as api from "@/lib/api";
import type { Declaration, DemoScenarioKey, EvidenceType, Inspection, OCRResult } from "@/lib/types";

const WIZARD_LABELS = ["Evidence & Product Info", "Run OCR", "Declarations Extracted"];

export default function NewInspectionPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // Manual-path collection state (before an inspection exists)
  const [files, setFiles] = useState<Partial<Record<EvidenceType, File>>>({});
  const [product, setProduct] = useState<api.InspectionCreatePayload>({
    product_name: "",
    supply_type: "DOMESTIC",
  });
  const [creating, setCreating] = useState(false);
  const [demoLoading, setDemoLoading] = useState<DemoScenarioKey | null>(null);

  // Once an inspection exists (manual or demo)
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [ocrResults, setOcrResults] = useState<OCRResult[] | null>(null);
  const [declarations, setDeclarations] = useState<Declaration[] | null>(null);
  const [runningOcr, setRunningOcr] = useState(false);

  async function handleLoadDemo(scenario: DemoScenarioKey) {
    setError(null);
    setDemoLoading(scenario);
    try {
      const insp = await api.loadDemo(scenario);
      setInspection(insp);
      setStep(1);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load demo scenario.");
    } finally {
      setDemoLoading(null);
    }
  }

  function handleFileChange(type: EvidenceType, file: File | null) {
    setFiles((prev) => {
      const next = { ...prev };
      if (file) next[type] = file;
      else delete next[type];
      return next;
    });
  }

  async function handleCreateAndUpload() {
    if (!product.product_name.trim()) {
      setError("Product name is required before continuing.");
      return;
    }
    if (!files.FRONT && !files.BACK) {
      setError("Upload at least a front or back image before continuing.");
      return;
    }
    setError(null);
    setCreating(true);
    try {
      const created = await api.createInspection(product);
      const entries = Object.entries(files) as [EvidenceType, File][];
      for (const [type, file] of entries) {
        await api.uploadEvidence(created.id, type, file);
      }
      const full = await api.getInspection(created.id);
      setInspection(full);
      setStep(1);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create the inspection.");
    } finally {
      setCreating(false);
    }
  }

  async function handleRunOcr() {
    if (!inspection) return;
    setError(null);
    setRunningOcr(true);
    try {
      const result = await api.runOcr(inspection.id);
      setOcrResults(result.ocr_results);
      setDeclarations(result.declarations);
      setStep(2);
    } catch (e) {
      setError(e instanceof Error ? e.message : "OCR failed.");
    } finally {
      setRunningOcr(false);
    }
  }

  async function handleDeclarationEdit(id: number, value: string) {
    const updated = await api.updateDeclaration(id, value);
    setDeclarations((prev) => (prev ? prev.map((d) => (d.id === id ? updated : d)) : prev));
  }

  return (
    <PageShell title="New Inspection">
      <div className="mb-6">
        <EvidenceChain activeIndex={step} labels={WIZARD_LABELS} />
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          {error}
        </Alert>
      )}

      {step === 0 && (
        <div className="space-y-6">
          <DemoLoader onLoad={handleLoadDemo} loading={demoLoading} />

          <Card>
            <CardHeader>
              <CardTitle>Step 1 — Evidence</CardTitle>
              <CardDescription>
                Upload front/back/side photographs. Drag and drop supported.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <EvidenceUploader files={files} onChange={handleFileChange} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Step 2 — Product Information</CardTitle>
            </CardHeader>
            <CardContent>
              <ProductInfoForm value={product} onChange={(patch) => setProduct((p) => ({ ...p, ...patch }))} />
              <div className="mt-6 flex justify-end">
                <Button size="lg" onClick={handleCreateAndUpload} disabled={creating}>
                  {creating ? <Spinner className="text-white" /> : <ArrowRight className="h-4 w-4" />}
                  Continue to OCR
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {step >= 1 && inspection && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>
                {inspection.product.name}{" "}
                <RuleTag>{inspection.reference_code}</RuleTag>
              </CardTitle>
              <CardDescription>
                {inspection.product.brand ? `${inspection.product.brand} · ` : ""}
                {inspection.supply_type === "IMPORTED" ? "Imported" : "Domestic"}
                {inspection.product.category ? ` · ${inspection.product.category}` : ""}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <EvidenceThumbnails evidence={inspection.evidence_items} />
            </CardContent>
          </Card>

          {step === 1 && (
            <Card>
              <CardContent className="flex flex-col items-center justify-center gap-3 py-10 text-center">
                <ScanText className="h-8 w-8 text-accent" />
                <p className="max-w-sm text-sm text-ink-600">
                  Run OCR to extract label text, then automatically parse it into structured
                  declarations for compliance analysis.
                </p>
                <Button size="lg" onClick={handleRunOcr} disabled={runningOcr}>
                  {runningOcr ? <Spinner className="text-white" /> : <ScanText className="h-4 w-4" />}
                  {runningOcr ? "Running OCR..." : "Run OCR"}
                </Button>
              </CardContent>
            </Card>
          )}

          {step === 2 && ocrResults && declarations && (
            <>
              <Card>
                <CardHeader>
                  <CardTitle>Step 3 — OCR Results</CardTitle>
                </CardHeader>
                <CardContent>
                  <OcrResultsList results={ocrResults} />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Step 4 — Extracted Declarations</CardTitle>
                  <CardDescription>
                    Click the pencil to correct any field manually — manual edits are clearly
                    labelled and are never overwritten by a later automatic re-run.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <DeclarationsTable declarations={declarations} onEdit={handleDeclarationEdit} />
                  <div className="mt-6 flex justify-end">
                    <Button size="lg" onClick={() => router.push(`/inspections/${inspection.id}`)}>
                      Proceed to Compliance Analysis <ArrowRight className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </div>
      )}
    </PageShell>
  );
}
