"use client";
import { useEffect, useState } from "react";
import { PageShell } from "@/components/layout/page-shell";
import { Card } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { PageSpinner } from "@/components/ui/spinner";
import { RuleTag } from "@/components/common/status-badge";
import * as api from "@/lib/api";
import { formatDateTime } from "@/lib/utils";
import type { AuditEvent } from "@/lib/types";

const ACTIONS = [
  "LOGIN",
  "INSPECTION_CREATED",
  "INSPECTION_UPDATED",
  "IMAGE_UPLOADED",
  "EVIDENCE_DELETED",
  "OCR_EXECUTED",
  "OCR_EDITED",
  "ANALYSIS_EXECUTED",
  "FINDING_CREATED",
  "FINDING_CONFIRMED",
  "FINDING_DISMISSED",
  "FINDING_MARKED_FOR_REVIEW",
  "REPORT_GENERATED",
  "INSPECTION_FINALIZED",
  "RULE_UPDATED",
];

export default function AuditTrailPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [action, setAction] = useState("");

  useEffect(() => {
    setLoading(true);
    api
      .listAuditEvents({ action: action || undefined, limit: 200 })
      .then(setEvents)
      .finally(() => setLoading(false));
  }, [action]);

  return (
    <PageShell title="Audit Trail">
      <div className="mb-4 flex items-center justify-between gap-4">
        <p className="text-sm text-ink-500">
          Immutable-style log of every login, inspection, OCR run, analysis, officer decision,
          and report generated across MetraCheck.
        </p>
        <Select value={action} onChange={(e) => setAction(e.target.value)} className="w-56 shrink-0">
          <option value="">All actions</option>
          {ACTIONS.map((a) => (
            <option key={a} value={a}>
              {a.replace(/_/g, " ")}
            </option>
          ))}
        </Select>
      </div>

      <Card>
        {loading ? (
          <PageSpinner label="Loading audit trail..." />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Timestamp</TableHead>
                <TableHead>User</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>Entity</TableHead>
                <TableHead>Description</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {events.map((e) => (
                <TableRow key={e.id}>
                  <TableCell className="whitespace-nowrap text-xs">{formatDateTime(e.timestamp)}</TableCell>
                  <TableCell>{e.user_name || "System"}</TableCell>
                  <TableCell className="whitespace-nowrap text-xs">{e.role_name || "—"}</TableCell>
                  <TableCell>
                    <RuleTag>{e.action}</RuleTag>
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-xs">
                    {e.entity_type}
                    {e.entity_id ? ` #${e.entity_id}` : ""}
                  </TableCell>
                  <TableCell className="text-xs text-ink-600">{e.description}</TableCell>
                </TableRow>
              ))}
              {events.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="py-8 text-center text-ink-500">
                    No audit events yet.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        )}
      </Card>
    </PageShell>
  );
}
