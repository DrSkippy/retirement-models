import {
  Area,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ScenarioMetricRow } from "../../types/runs";
import { findRetirementDate } from "../../utils/chartHelpers";
import { formatDate, formatDollar } from "../../utils/formatters";

interface Props {
  metrics: ScenarioMetricRow[];
}

export default function NetWorthChart({ metrics }: Props) {
  const retirementDate = findRetirementDate(metrics);
  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={metrics}>
        <XAxis dataKey="period_date" tickFormatter={formatDate} tick={{ fontSize: 10 }} />
        <YAxis tickFormatter={formatDollar} tick={{ fontSize: 10 }} width={70} />
        <Tooltip formatter={(v: number) => formatDollar(v)} labelFormatter={formatDate} />
        {retirementDate && (
          <ReferenceLine x={retirementDate} stroke="#455A64" strokeDasharray="4 2" label={{ value: "Retirement", fontSize: 9, fill: "#455A64" }} />
        )}
        <Area type="monotone" dataKey="net_worth" fill="#1A6FAF" stroke="#1A6FAF" fillOpacity={0.25} name="Net Worth" />
        <Line type="monotone" dataKey="debt" stroke="#E57373" dot={false} name="Debt" />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
