"use client";
import { useState } from "react";
import { Check, Pencil, X as XIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { mediaUrl } from "@/lib/api";
import { DECLARATION_FIELD_LABELS } from "@/lib/types";
import { formatConfidence } from "@/lib/utils";
import type { Declaration, Evidence, OCRResult } from "@/lib/types";

export function EvidenceThumbnails({ evidence }: { evidence: Evidence[] }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {evidence.map((e) => (
        <div key={e.id} className="overflow-hidden rounded-lg border border-line">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={mediaUrl(e.url)} alt={e.image_type} className="aspect-square w-full object-cover" />
          <p className="px-2 py-1.5 text-center text-xs font-medium text-ink-600">{e.image_type}</p>
        </div>
      ))}
    </div>
  );
}

export function OcrResultsList({ results }: { results: OCRResult[] }) {
  return (
    <div className="space-y-3">
      {results.map((r) => {
        const conf = r.overall_confidence ?? 0;
        return (
          <div key={r.id} className="rounded-lg border border-line p-3">
            <div className="flex items-center justify-between">
              <span className="mc-tag">{r.engine_name}</span>
              <Badge variant={r.requires_manual_entry ? "na" : conf >= 75 ? "pass" : "review"}>
                {r.requires_manual_entry ? "Manual entry required" : `${formatConfidence(conf)} confidence`}
              </Badge>
            </div>
            {r.warnings && r.warnings.length > 0 && (
              <p className="mt-2 text-xs text-status-review">{r.warnings.join(" ")}</p>
            )}
            <pre className="mc-scrollbar mt-2 max-h-28 overflow-auto whitespace-pre-wrap rounded bg-canvas p-2 text-xs text-ink-600">
              {r.raw_text || "(no text detected — enter declarations manually below)"}
            </pre>
          </div>
        );
      })}
    </div>
  );
}

export function DeclarationsTable({
  declarations,
  onEdit,
}: {
  declarations: Declaration[];
  onEdit: (id: number, value: string) => Promise<void>;
}) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);

  function startEdit(d: Declaration) {
    setEditingId(d.id);
    setDraft(d.value);
  }

  async function save(id: number) {
    setSaving(true);
    try {
      await onEdit(id, draft);
      setEditingId(null);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="overflow-hidden rounded-lg border border-line">
      <table className="w-full text-sm">
        <thead className="bg-canvas text-xs uppercase text-ink-500">
          <tr>
            <th className="px-3 py-2 text-left">Field</th>
            <th className="px-3 py-2 text-left">Value</th>
            <th className="px-3 py-2 text-left">Confidence</th>
            <th className="px-3 py-2 text-left">Method</th>
            <th className="px-3 py-2" />
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {declarations.map((d) => (
            <tr key={d.id}>
              <td className="whitespace-nowrap px-3 py-2 font-medium text-ink-900">
                {DECLARATION_FIELD_LABELS[d.field_key] ?? d.field_key}
              </td>
              <td className="px-3 py-2">
                {editingId === d.id ? (
                  <Input
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    className="h-7 text-xs"
                    autoFocus
                  />
                ) : (
                  <span className={d.value ? "text-ink-900" : "italic text-ink-500"}>
                    {d.value || "Not detected"}
                  </span>
                )}
              </td>
              <td className="whitespace-nowrap px-3 py-2">
                <Badge variant={d.confidence >= 75 ? "pass" : d.confidence > 0 ? "review" : "na"}>
                  {formatConfidence(d.confidence)}
                </Badge>
              </td>
              <td className="whitespace-nowrap px-3 py-2">
                <Badge variant={d.is_manually_edited ? "accent" : "outline"}>
                  {d.is_manually_edited ? "Manual" : "Automatic"}
                </Badge>
              </td>
              <td className="whitespace-nowrap px-3 py-2 text-right">
                {editingId === d.id ? (
                  <div className="flex justify-end gap-1">
                    <Button size="icon" variant="ghost" onClick={() => save(d.id)} disabled={saving}>
                      {saving ? <Spinner /> : <Check className="h-3.5 w-3.5" />}
                    </Button>
                    <Button size="icon" variant="ghost" onClick={() => setEditingId(null)}>
                      <XIcon className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                ) : (
                  <Button size="icon" variant="ghost" onClick={() => startEdit(d)}>
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
