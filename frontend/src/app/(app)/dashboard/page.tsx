"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Plus, MapPin } from "lucide-react";
import { PageShell } from "@/components/layout/page-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { PageSpinner } from "@/components/ui/spinner";
import { Alert } from "@/components/ui/alert";
import { StatCard } from "@/components/dashboard/stat-card";
import { ViolationsByCategoryChart, InspectionTrendsChart } from "@/components/dashboard/charts";
import { OverallResultBadge, FindingStatusBadge, RuleTag } from "@/components/common/status-badge";
import * as api from "@/lib/api";
import type { DashboardStats } from "@/lib/types";
import { formatDate, formatConfidence } from "@/lib/utils";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getDashboardStats()
      .then(setStats)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load dashboard"));
  }, []);

  return (
    <PageShell title="Dashboard">
      <div className="mb-6 flex items-start justify-between gap-4">
        <p className="text-sm text-ink-500">
          {stats?.active_rule_pack ? (
            <>
              Active rule pack: <RuleTag>{stats.active_rule_pack}</RuleTag>
            </>
          ) : (
            "AI-assisted compliance screening and evidence management for Legal Metrology inspections."
          )}
        </p>
        <Link href="/inspections/new" className="shrink-0">
          <Button size="lg">
            <Plus className="h-4 w-4" /> Start New Inspection
          </Button>
        </Link>
      </div>

      {error && <Alert variant="destructive">{error}</Alert>}
      {!stats && !error && <PageSpinner label="Loading dashboard..." />}

      {stats && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-5">
            <StatCard label="Total Inspections" value={stats.total_inspections} />
            <StatCard label="Compliant" value={stats.compliant_count} tone="pass" />
            <StatCard label="Non-Compliant" value={stats.non_compliant_count} tone="fail" />
            <StatCard label="Reviews Pending" value={stats.review_pending_count} tone="review" />
            <StatCard
              label="Avg. Compliance Score"
              value={formatConfidence(stats.average_compliance_score)}
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Violations by Category</CardTitle>
              </CardHeader>
              <CardContent>
                <ViolationsByCategoryChart data={stats.violations_by_category} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Inspection Trends</CardTitle>
              </CardHeader>
              <CardContent>
                <InspectionTrendsChart data={stats.inspection_trends} />
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Recent Inspections</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {stats.recent_inspections.length === 0 && (
                  <p className="text-sm text-ink-500">No inspections yet — start one to see it here.</p>
                )}
                {stats.recent_inspections.map((insp) => (
                  <Link
                    key={insp.id}
                    href={`/inspections/${insp.id}`}
                    className="flex items-center justify-between rounded-md border border-line px-3 py-2.5 transition-colors hover:bg-canvas"
                  >
                    <div>
                      <p className="text-sm font-medium text-ink-900">{insp.product_name}</p>
                      <RuleTag>{insp.reference_code}</RuleTag>
                    </div>
                    <div className="text-right">
                      <OverallResultBadge result={insp.overall_result} />
                      <p className="mt-1 text-xs text-ink-500">{formatDate(insp.inspection_date)}</p>
                    </div>
                  </Link>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Locations</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2.5">
                {stats.locations_summary.length === 0 && (
                  <p className="text-sm text-ink-500">No location data yet.</p>
                )}
                {stats.locations_summary.map((loc) => (
                  <div key={loc.location} className="flex items-center justify-between text-sm">
                    <span className="flex items-center gap-1.5 text-ink-600">
                      <MapPin className="h-3.5 w-3.5 text-ink-500" /> {loc.location}
                    </span>
                    <span className="font-medium text-ink-900">{loc.count}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Recent Violations</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {stats.recent_violations.length === 0 && (
                <p className="text-sm text-ink-500">No violations recorded.</p>
              )}
              {stats.recent_violations.map((f) => (
                <div
                  key={f.id}
                  className="flex items-center justify-between rounded-md border border-line px-3 py-2.5"
                >
                  <div className="flex items-center gap-2">
                    <RuleTag>{f.rule_code}</RuleTag>
                    <span className="text-sm text-ink-900">{f.rule_name}</span>
                  </div>
                  <FindingStatusBadge status={f.status} />
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      )}
    </PageShell>
  );
}
