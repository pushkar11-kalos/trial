"use client";
import { useEffect, useState } from "react";
import { Pencil } from "lucide-react";
import { PageShell } from "@/components/layout/page-shell";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { PageSpinner, Spinner } from "@/components/ui/spinner";
import { SeverityBadge, RuleTag } from "@/components/common/status-badge";
import { useAuth } from "@/lib/auth";
import * as api from "@/lib/api";
import { formatDate } from "@/lib/utils";
import type { Rule, RulePack, Severity } from "@/lib/types";

interface EditForm {
  name: string;
  description: string;
  severity: Severity;
  is_active: boolean;
}

export default function RulePackPage() {
  const { user } = useAuth();
  const [pack, setPack] = useState<RulePack | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<Rule | null>(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<EditForm>({
    name: "",
    description: "",
    severity: "MINOR",
    is_active: true,
  });

  async function load() {
    setLoading(true);
    try {
      const active = await api.getActiveRulePack();
      setPack(active);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function openEdit(rule: Rule) {
    setEditing(rule);
    setForm({
      name: rule.name,
      description: rule.description ?? "",
      severity: rule.severity,
      is_active: rule.is_active,
    });
  }

  async function saveEdit() {
    if (!editing) return;
    setSaving(true);
    try {
      await api.updateRule(editing.id, form);
      setEditing(null);
      await load();
    } finally {
      setSaving(false);
    }
  }

  const canEdit = user?.role === "ADMINISTRATOR";

  if (loading) {
    return (
      <PageShell title="Rule Pack">
        <PageSpinner label="Loading rule pack..." />
      </PageShell>
    );
  }
  if (!pack) {
    return (
      <PageShell title="Rule Pack">
        <p className="text-sm text-ink-500">No active rule pack configured.</p>
      </PageShell>
    );
  }

  return (
    <PageShell title="Rule Pack">
      <Card className="mb-4">
        <CardHeader>
          <CardTitle>{pack.name}</CardTitle>
          <CardDescription>
            Version {pack.version} · Effective from {formatDate(pack.effective_from)} · {pack.rules.length}{" "}
            rules
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-ink-600">{pack.description}</p>
          {!canEdit && (
            <p className="mt-2 text-xs text-ink-500">
              Only Administrators can edit rule metadata
              {user?.role === "SUPERVISOR" ? " — you have read-only access." : "."}
            </p>
          )}
        </CardContent>
      </Card>

      <div className="space-y-3">
        {pack.rules.map((rule) => (
          <Card key={rule.id}>
            <CardContent className="pt-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <RuleTag>{rule.rule_code}</RuleTag>
                    <span className="font-heading text-sm font-semibold text-ink-900">{rule.name}</span>
                    {!rule.is_active && <Badge variant="na">Inactive</Badge>}
                    {!rule.counts_toward_score && <Badge variant="outline">Advisory · excluded from score</Badge>}
                  </div>
                  <p className="mt-1 text-xs text-ink-500">{rule.category}</p>
                </div>
                <div className="flex items-center gap-2">
                  <SeverityBadge severity={rule.severity} />
                  {canEdit && (
                    <Button size="icon" variant="ghost" onClick={() => openEdit(rule)}>
                      <Pencil className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </div>
              </div>
              <p className="mt-3 text-sm text-ink-600">{rule.description}</p>
              <dl className="mt-3 grid gap-3 text-xs sm:grid-cols-2">
                <div>
                  <dt className="font-medium uppercase text-ink-500">Applicability</dt>
                  <dd className="mt-0.5 text-ink-700">{rule.applicability}</dd>
                </div>
                <div>
                  <dt className="font-medium uppercase text-ink-500">Expected Condition</dt>
                  <dd className="mt-0.5 text-ink-700">{rule.expected_condition}</dd>
                </div>
              </dl>
              <p className="mt-3 text-[11px] italic text-ink-500">{rule.source_reference}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Dialog
        open={!!editing}
        onOpenChange={(open) => !open && setEditing(null)}
        title={editing ? `Edit ${editing.rule_code}` : ""}
        description="Only descriptive metadata and activation status are editable here — rule logic and legal references are fixed for this prototype."
        footer={
          <>
            <Button variant="ghost" onClick={() => setEditing(null)}>
              Cancel
            </Button>
            <Button onClick={saveEdit} disabled={saving}>
              {saving ? <Spinner className="text-white" /> : "Save"}
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label>Name</Label>
            <Input value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} />
          </div>
          <div className="space-y-1.5">
            <Label>Description</Label>
            <Textarea
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              rows={3}
            />
          </div>
          <div className="space-y-1.5">
            <Label>Severity</Label>
            <Select
              value={form.severity}
              onChange={(e) => setForm((f) => ({ ...f, severity: e.target.value as Severity }))}
            >
              <option value="CRITICAL">Critical</option>
              <option value="MAJOR">Major</option>
              <option value="MINOR">Minor</option>
              <option value="INFO">Info</option>
            </Select>
          </div>
          <label className="flex items-center gap-2 text-sm text-ink-700">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
            />
            Active
          </label>
        </div>
      </Dialog>
    </PageShell>
  );
}
