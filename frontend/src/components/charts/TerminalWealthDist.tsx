import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { McRunResult } from "../../types/mc";
import { formatDollar } from "../../utils/formatters";

interface Props {
  runs: McRunResult[];
  bins?: number;
}

function buildHistogram(values: number[], bins: number): { x: number; count: number }[] {
  if (values.length === 0) return [];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const width = (max - min) / bins || 1;
  const counts = new Array(bins).fill(0);
  for (const v of values) {
    const idx = Math.min(Math.floor((v - min) / width), bins - 1);
    counts[idx]++;
  }
  return counts.map((count, i) => ({ x: min + i * width + width / 2, count }));
}

export default function TerminalWealthDist({ runs, bins = 40 }: Props) {
  const values = runs.map((r) => r.terminal_net_worth);
  const data = buildHistogram(values, bins);
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data}>
        <XAxis dataKey="x" tickFormatter={formatDollar} tick={{ fontSize: 10 }} />
        <YAxis tick={{ fontSize: 10 }} />
        <Tooltip formatter={(v: number) => v} labelFormatter={formatDollar} />
        <Bar dataKey="count" name="Count">
          {data.map((d, i) => (
            <Cell key={i} fill={d.x >= 0 ? "#4DA6E8" : "#C62828"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
