import {
  Area,
  Line,
  ComposedChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { McSetDetail } from "../../types/mc";
import { formatDollar } from "../../utils/formatters";

interface Props {
  detail: McSetDetail;
  retirementDate?: string | null;
}

export default function McFanChart({ detail, retirementDate }: Props) {
  const bands = detail.percentile_bands;
  const hasBands = bands && Object.keys(bands).length > 0;

  if (!hasBands) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400 text-sm">
        No trajectory data available. Re-run with <code className="mx-1 bg-gray-100 px-1 rounded">store_trajectories=True</code>.
      </div>
    );
  }

  const n = (bands.p50 ?? []).length;
  const chartData = Array.from({ length: n }, (_, i) => ({
    period: i,
    p10: bands.p10?.[i] ?? null,
    p25: bands.p25?.[i] ?? null,
    p50: bands.p50?.[i] ?? null,
    p75: bands.p75?.[i] ?? null,
    p90: bands.p90?.[i] ?? null,
  }));

  return (
    <ResponsiveContainer width="100%" height={340}>
      <ComposedChart data={chartData}>
        <XAxis dataKey="period" tick={{ fontSize: 10 }} />
        <YAxis tickFormatter={formatDollar} tick={{ fontSize: 10 }} width={75} />
        <Tooltip formatter={(v: number) => formatDollar(v)} />
        <ReferenceLine y={0} stroke="#C62828" strokeDasharray="3 2" label={{ value: "Ruin", fontSize: 8, fill: "#C62828" }} />
        {retirementDate && (
          <ReferenceLine x={retirementDate} stroke="#455A64" strokeDasharray="4 2" />
        )}
        {/* P10–P90 outer band */}
        <Area type="monotone" dataKey="p90" stroke="none" fill="#90CAF9" fillOpacity={0.15} legendType="none" />
        <Area type="monotone" dataKey="p10" stroke="none" fill="#ffffff" fillOpacity={1} legendType="none" />
        {/* P25–P75 inner band */}
        <Area type="monotone" dataKey="p75" stroke="none" fill="#4DA6E8" fillOpacity={0.25} legendType="none" />
        <Area type="monotone" dataKey="p25" stroke="none" fill="#ffffff" fillOpacity={1} legendType="none" />
        {/* P50 median line */}
        <Line type="monotone" dataKey="p50" stroke="#0D47A1" strokeWidth={2} dot={false} name="Median (P50)" />
        {/* P10 / P90 dashed bounds */}
        <Line type="monotone" dataKey="p10" stroke="#90CAF9" strokeWidth={1} strokeDasharray="3 2" dot={false} name="P10" />
        <Line type="monotone" dataKey="p90" stroke="#90CAF9" strokeWidth={1} strokeDasharray="3 2" dot={false} name="P90" />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
