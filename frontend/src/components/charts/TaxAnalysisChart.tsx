import { Area, AreaChart, Line, ComposedChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { TaxRow } from "../../types/runs";
import { formatDate, formatDollar, formatPercent } from "../../utils/formatters";

interface Props {
  rows: TaxRow[];
  retirementDate: string | null;
  rmdDate: string | null;
}

export default function TaxAnalysisChart({ rows, retirementDate, rmdDate }: Props) {
  return (
    <div className="space-y-4">
      {/* Taxes vs Income */}
      <div>
        <p className="text-xs text-gray-500 mb-1">Taxes vs Taxable Income</p>
        <ResponsiveContainer width="100%" height={200}>
          <ComposedChart data={rows}>
            <XAxis dataKey="period_date" tickFormatter={formatDate} tick={{ fontSize: 10 }} />
            <YAxis tickFormatter={formatDollar} tick={{ fontSize: 10 }} width={70} />
            <Tooltip formatter={(v: number) => formatDollar(v)} labelFormatter={formatDate} />
            {retirementDate && <ReferenceLine x={retirementDate} stroke="#455A64" strokeDasharray="4 2" />}
            {rmdDate && <ReferenceLine x={rmdDate} stroke="#B71C1C" strokeDasharray="4 2" />}
            <Area type="monotone" dataKey="taxes_paid" fill="#EF6C00" stroke="#EF6C00" fillOpacity={0.3} name="Taxes" />
            <Line type="monotone" dataKey="monthly_taxable_income" stroke="#2E7D32" dot={false} name="Income" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      {/* Effective Tax Rate */}
      <div>
        <p className="text-xs text-gray-500 mb-1">Effective Tax Rate</p>
        <ResponsiveContainer width="100%" height={160}>
          <AreaChart data={rows}>
            <XAxis dataKey="period_date" tickFormatter={formatDate} tick={{ fontSize: 10 }} />
            <YAxis tickFormatter={(v) => formatPercent(v)} tick={{ fontSize: 10 }} width={55} />
            <Tooltip formatter={(v: number) => formatPercent(v)} labelFormatter={formatDate} />
            {retirementDate && <ReferenceLine x={retirementDate} stroke="#455A64" strokeDasharray="4 2" />}
            {rmdDate && <ReferenceLine x={rmdDate} stroke="#B71C1C" strokeDasharray="4 2" />}
            <Area type="monotone" dataKey="effective_rate" fill="#EF6C00" stroke="#EF6C00" fillOpacity={0.3} name="Eff. Rate" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
