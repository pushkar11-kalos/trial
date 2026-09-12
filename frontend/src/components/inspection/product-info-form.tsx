import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { PRODUCT_CATEGORIES } from "@/lib/types";
import type { InspectionCreatePayload } from "@/lib/api";

export function ProductInfoForm({
  value,
  onChange,
}: {
  value: InspectionCreatePayload;
  onChange: (patch: Partial<InspectionCreatePayload>) => void;
}) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Field label="Product Name" required>
        <Input
          value={value.product_name}
          onChange={(e) => onChange({ product_name: e.target.value })}
          placeholder="e.g. Multigrain Muesli"
        />
      </Field>
      <Field label="Brand">
        <Input
          value={value.brand ?? ""}
          onChange={(e) => onChange({ brand: e.target.value })}
          placeholder="e.g. Solara Foods"
        />
      </Field>
      <Field label="Category">
        <Select value={value.category ?? ""} onChange={(e) => onChange({ category: e.target.value })}>
          <option value="">Select category</option>
          {PRODUCT_CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </Select>
      </Field>
      <Field label="Domestic / Imported">
        <Select
          value={value.supply_type}
          onChange={(e) => onChange({ supply_type: e.target.value as InspectionCreatePayload["supply_type"] })}
        >
          <option value="DOMESTIC">Domestic</option>
          <option value="IMPORTED">Imported</option>
        </Select>
      </Field>
      <Field label="Batch / Lot">
        <Input value={value.batch_lot ?? ""} onChange={(e) => onChange({ batch_lot: e.target.value })} />
      </Field>
      <Field label="Manufacturer / Importer">
        <Input
          value={value.manufacturer_name ?? ""}
          onChange={(e) => onChange({ manufacturer_name: e.target.value })}
        />
      </Field>
      <Field label="Inspection Location">
        <Input
          value={value.inspection_location ?? ""}
          onChange={(e) => onChange({ inspection_location: e.target.value })}
          placeholder="e.g. Sector 17 Market, Chandigarh"
        />
      </Field>
      <Field label="Product / Listing URL (if applicable)">
        <Input
          value={value.listing_url ?? ""}
          onChange={(e) => onChange({ listing_url: e.target.value })}
          placeholder="https://..."
        />
      </Field>
    </div>
  );
}

function Field({
  label,
  required,
  children,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label>
        {label}
        {required && <span className="text-status-fail"> *</span>}
      </Label>
      {children}
    </div>
  );
}
