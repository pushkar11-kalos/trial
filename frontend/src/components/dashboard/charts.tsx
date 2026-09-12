"use client";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { CategoryCount, TrendPoint } from "@/lib/types";

export function ViolationsByCategoryChart({ data }: { data: CategoryCount[] }) {
  if (!data.length) {
    return <p className="py-10 text-center text-sm text-ink-500">No violations recorded yet.</p>;
  }
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ left: -20, right: 10 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#E4E7EC" vertical={false} />
        <XAxis
          dataKey="category"
          tick={{ fontSize: 10, fill: "#667085" }}
          interval={0}
          angle={-15}
          textAnchor="end"
          height={55}
        />
        <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "#667085" }} />
        <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, borderColor: "#E4E7EC" }} />
        <Bar dataKey="count" fill="#C0392B" radius={[3, 3, 0, 0]} maxBarSize={40} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function InspectionTrendsChart({ data }: { data: TrendPoint[] }) {
  if (!data.length) {
    return <p className="py-10 text-center text-sm text-ink-500">No inspections recorded yet.</p>;
  }
  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data} margin={{ left: -20, right: 10 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#E4E7EC" vertical={false} />
        <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#667085" }} />
        <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "#667085" }} />
        <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, borderColor: "#E4E7EC" }} />
        <Line type="monotone" dataKey="count" stroke="#1D5FC7" strokeWidth={2} dot={{ r: 3 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}
