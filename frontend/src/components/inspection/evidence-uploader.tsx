"use client";
import { useRef, useState } from "react";
import { Upload, X } from "lucide-react";
import { cn } from "@/lib/utils";
import type { EvidenceType } from "@/lib/types";

const SLOTS: { type: EvidenceType; label: string; required?: boolean }[] = [
  { type: "FRONT", label: "Front", required: true },
  { type: "BACK", label: "Back", required: true },
  { type: "SIDE", label: "Side" },
  { type: "ADDITIONAL", label: "Additional" },
];

export function EvidenceUploader({
  files,
  onChange,
}: {
  files: Partial<Record<EvidenceType, File>>;
  onChange: (type: EvidenceType, file: File | null) => void;
}) {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      {SLOTS.map((slot) => (
        <Dropzone
          key={slot.type}
          label={slot.label}
          required={slot.required}
          file={files[slot.type] ?? null}
          onSelect={(f) => onChange(slot.type, f)}
        />
      ))}
    </div>
  );
}

function Dropzone({
  label,
  required,
  file,
  onSelect,
}: {
  label: string;
  required?: boolean;
  file: File | null;
  onSelect: (file: File | null) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  function select(f: File | null) {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(f ? URL.createObjectURL(f) : null);
    onSelect(f);
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        const f = e.dataTransfer.files?.[0];
        if (f) select(f);
      }}
      className={cn(
        "relative flex aspect-square flex-col items-center justify-center rounded-lg border-2 border-dashed p-3 text-center transition-colors",
        dragOver ? "border-accent bg-accent-50" : "border-line bg-white hover:border-accent/50"
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/png,image/jpeg,image/webp"
        className="hidden"
        onChange={(e) => select(e.target.files?.[0] ?? null)}
      />
      {file && previewUrl ? (
        <>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={previewUrl} alt={label} className="h-full w-full rounded object-cover" />
          <button
            type="button"
            onClick={() => select(null)}
            className="absolute right-1.5 top-1.5 rounded-full bg-ink-900/70 p-1 text-white hover:bg-ink-900"
          >
            <X className="h-3 w-3" />
          </button>
          <span className="absolute bottom-1.5 left-1.5 rounded bg-ink-900/70 px-1.5 py-0.5 text-[10px] text-white">
            {label}
          </span>
        </>
      ) : (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="flex flex-col items-center gap-1.5"
        >
          <Upload className="h-5 w-5 text-ink-500" />
          <span className="text-xs font-medium text-ink-900">
            {label}
            {required && <span className="text-status-fail"> *</span>}
          </span>
          <span className="text-[10px] text-ink-500">Drop or click</span>
        </button>
      )}
    </div>
  );
}
