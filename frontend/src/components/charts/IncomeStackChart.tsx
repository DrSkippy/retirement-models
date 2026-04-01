import { AreaChart, Area, XAxis, YAxis, Tooltip, ReferenceLine, ResponsiveContainer, Legend } from "recharts";
import type { AssetMetricRow } from "../../types/runs";
import { formatDate, formatDollar } from "../../utils/formatters";

interface Props {
  rows: AssetMetricRow[];
  retirementDate: string | null;
}

const COLORS = [
  "#2E7D32", "#1A6FAF", "#EF6C00", "#6A1B9A", "#00838F",
  "#AD1457", "#558B2F", "#4527A0", "#D84315",
];

/** Pivot flat asset rows into one object per period, summing income by asset name. */
function pivot(rows: AssetMetricRow[]): { period_date: string; [asset: string]: number | string }[] {
  const byPeriod = new Map<string, Record<string, number | string>>();
  for (const row of rows) {
    if (row.income <= 0) continue; // skip non-income assets for this period
    if (!byPeriod.has(row.period_date)) {
      byPeriod.set(row.period_date, { period_date: row.period_date });
    }
    const entry = byPeriod.get(row.period_date)!;
    entry[row.asset_name] = (Number(entry[row.asset_name] ?? 0) + row.income);
  }
  return Array.from(byPeriod.values()).sort((a, b) =>
    String(a.period_date).localeCompare(String(b.period_date))
  );
}

export default function IncomeStackChart({ rows, retirementDate }: Props) {
  // Only include asset names that have any income
  const incomeAssets = Array.from(
    new Set(rows.filter((r) => r.income > 0).map((r) => r.asset_name))
  );
  const data = pivot(rows);

  if (incomeAssets.length === 0) {
    return <p className="text-xs text-gray-400 italic">No income data available.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={data}>
        <XAxis dataKey="period_date" tickFormatter={formatDate} tick={{ fontSize: 10 }} />
        <YAxis tickFormatter={formatDollar} tick={{ fontSize: 10 }} width={70} />
        <Tooltip formatter={(v: number) => formatDollar(v)} labelFormatter={formatDate} />
        <Legend iconSize={10} wrapperStyle={{ fontSize: 10 }} />
        {retirementDate && (
          <ReferenceLine x={retirementDate} stroke="#455A64" strokeDasharray="4 2" label={{ value: "Retirement", fontSize: 9, fill: "#455A64" }} />
        )}
        {incomeAssets.map((name, i) => (
          <Area
            key={name}
            type="monotone"
            dataKey={name}
            stackId="1"
            stroke={COLORS[i % COLORS.length]}
            fill={COLORS[i % COLORS.length]}
            fillOpacity={0.65}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}
