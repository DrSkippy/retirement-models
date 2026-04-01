import { Bar, BarChart, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ScenarioMetricRow } from "../../types/runs";
import { findRetirementDate } from "../../utils/chartHelpers";
import { formatDate, formatDollar } from "../../utils/formatters";

interface Props {
  metrics: ScenarioMetricRow[];
}

export default function FreeCashFlowChart({ metrics }: Props) {
  const retirementDate = findRetirementDate(metrics);
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={metrics}>
        <XAxis dataKey="period_date" tickFormatter={formatDate} tick={{ fontSize: 10 }} />
        <YAxis tickFormatter={formatDollar} tick={{ fontSize: 10 }} width={70} />
        <Tooltip formatter={(v: number) => formatDollar(v)} labelFormatter={formatDate} />
        <ReferenceLine y={0} stroke="#999" />
        {retirementDate && (
          <ReferenceLine x={retirementDate} stroke="#455A64" strokeDasharray="4 2" />
        )}
        <Bar dataKey="free_cash_flows" name="Free Cash Flow">
          {metrics.map((row, i) => (
            <Cell key={i} fill={row.free_cash_flows >= 0 ? "#F9A825" : "#C62828"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
