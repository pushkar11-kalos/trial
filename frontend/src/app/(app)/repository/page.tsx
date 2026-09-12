"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Search } from "lucide-react";
import { PageShell } from "@/components/layout/page-shell";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { PageSpinner } from "@/components/ui/spinner";
import { OverallResultBadge, RuleTag } from "@/components/common/status-badge";
import { PRODUCT_CATEGORIES } from "@/lib/types";
import * as api from "@/lib/api";
import { formatConfidence, formatDate } from "@/lib/utils";
import type { InspectionListItem } from "@/lib/types";

export default function RepositoryPage() {
  const [items, setItems] = useState<InspectionListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [result, setResult] = useState("");
  const [category, setCategory] = useState("");
  const [supplyType, setSupplyType] = useState("");

  async function search() {
    setLoading(true);
    try {
      const res = await api.searchRepository({
        q: q || undefined,
        status: status || undefined,
        result: result || undefined,
        category: category || undefined,
        supply_type: supplyType || undefined,
        limit: 100,
      });
      setItems(res.items);
      setTotal(res.total);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    search();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, result, category, supplyType]);

  return (
    <PageShell title="Repository">
      <Card className="mb-4">
        <CardContent className="flex flex-wrap gap-3 pt-5">
          <div className="relative min-w-[220px] flex-1">
            <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-500" />
            <Input
              placeholder="Search product, brand, batch, reference..."
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && search()}
              className="pl-8"
            />
          </div>
          <Select value={result} onChange={(e) => setResult(e.target.value)} className="w-44">
            <option value="">All results</option>
            <option value="COMPLIANT">Compliant</option>
            <option value="NON_COMPLIANT">Non-Compliant</option>
            <option value="REVIEW_REQUIRED">Review Required</option>
          </Select>
          <Select value={category} onChange={(e) => setCategory(e.target.value)} className="w-48">
            <option value="">All categories</option>
            {PRODUCT_CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </Select>
          <Select value={supplyType} onChange={(e) => setSupplyType(e.target.value)} className="w-44">
            <option value="">Domestic &amp; Imported</option>
            <option value="DOMESTIC">Domestic</option>
            <option value="IMPORTED">Imported</option>
          </Select>
          <Select value={status} onChange={(e) => setStatus(e.target.value)} className="w-44">
            <option value="">All statuses</option>
            <option value="DRAFT">Draft</option>
            <option value="EVIDENCE_UPLOADED">Evidence Uploaded</option>
            <option value="DECLARATIONS_EXTRACTED">Declarations Extracted</option>
            <option value="ANALYZED">Analyzed</option>
            <option value="REVIEWED">Reviewed</option>
            <option value="FINALIZED">Finalized</option>
          </Select>
          <Button onClick={search}>Search</Button>
        </CardContent>
      </Card>

      <Card>
        {loading ? (
          <PageSpinner label="Searching..." />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Reference</TableHead>
                <TableHead>Product</TableHead>
                <TableHead>Brand</TableHead>
                <TableHead>Batch</TableHead>
                <TableHead>Category</TableHead>
                <TableHead>Supply</TableHead>
                <TableHead>Location</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Score</TableHead>
                <TableHead>Result</TableHead>
                <TableHead>Inspector</TableHead>
                <TableHead>Date</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((item) => (
                <TableRow key={item.id}>
                  <TableCell>
                    <Link href={`/inspections/${item.id}`} className="hover:text-accent">
                      <RuleTag>{item.reference_code}</RuleTag>
                    </Link>
                  </TableCell>
                  <TableCell>
                    <Link href={`/inspections/${item.id}`} className="font-medium text-ink-900 hover:text-accent">
                      {item.product_name}
                    </Link>
                  </TableCell>
                  <TableCell>{item.brand || "—"}</TableCell>
                  <TableCell>{item.batch_lot || "—"}</TableCell>
                  <TableCell>{item.category || "—"}</TableCell>
                  <TableCell>{item.supply_type === "IMPORTED" ? "Imported" : "Domestic"}</TableCell>
                  <TableCell>{item.inspection_location || "—"}</TableCell>
                  <TableCell className="whitespace-nowrap text-xs">{item.status.replace(/_/g, " ")}</TableCell>
                  <TableCell>{formatConfidence(item.overall_score)}</TableCell>
                  <TableCell>
                    <OverallResultBadge result={item.overall_result} />
                  </TableCell>
                  <TableCell>{item.inspector_name}</TableCell>
                  <TableCell className="whitespace-nowrap">{formatDate(item.inspection_date)}</TableCell>
                </TableRow>
              ))}
              {items.length === 0 && (
                <TableRow>
                  <TableCell colSpan={12} className="py-8 text-center text-ink-500">
                    No inspections match these filters.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        )}
      </Card>
      <p className="mt-3 text-xs text-ink-500">
        {total} inspection{total === 1 ? "" : "s"} found.
      </p>
    </PageShell>
  );
}
