import { useState } from "react";
import { useParams } from "react-router-dom";
import { useMcSet } from "../api/mc";
import McFanChart from "../components/charts/McFanChart";
import TerminalWealthDist from "../components/charts/TerminalWealthDist";
import RuinProbabilityGauge from "../components/RuinProbabilityGauge";
import { formatDollar, formatPercent } from "../utils/formatters";

export default function McDetailPage() {
  const { id } = useParams<{ id: string }>();
  const mcSetId = Number(id);
  const [includeRuns, setIncludeRuns] = useState(false);
  const { data, isLoading, error } = useMcSet(mcSetId, includeRuns);

  if (isLoading) return <p className="text-gray-400">Loading…</p>;
  if (error || !data) return <p className="text-red-500">Failed to load MC run set.</p>;

  const pcts = data.terminal_percentiles;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-800">
            MC Set #{data.id}{data.label ? ` — ${data.label}` : ""}
          </h2>
          <p className="text-sm text-gray-500">{data.n_runs} runs · {data.run_started_at?.slice(0, 16).replace("T", " ")}</p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-bold" style={{ color: data.ruin_probability < 0.05 ? "#2E7D32" : data.ruin_probability < 0.2 ? "#F9A825" : "#C62828" }}>
            {formatPercent(data.ruin_probability)} ruin
          </p>
          <p className="text-sm text-gray-500">P50: {pcts["50"] != null ? formatDollar(pcts["50"]) : "—"}</p>
        </div>
      </div>

      {/* Ruin gauge */}
      <div className="bg-white border rounded-lg p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Ruin vs Survival</h3>
        <RuinProbabilityGauge probability={data.ruin_probability} />
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "P10 Terminal Wealth", value: pcts["10"] },
          { label: "P50 Terminal Wealth", value: pcts["50"] },
          { label: "P90 Terminal Wealth", value: pcts["90"] },
        ].map(({ label, value }) => (
          <div key={label} className="bg-white border rounded-lg p-4 text-center">
            <p className="text-xs text-gray-500">{label}</p>
            <p className="text-lg font-bold text-blue-700">{value != null ? formatDollar(value) : "—"}</p>
          </div>
        ))}
      </div>

      {/* Fan chart */}
      <div className="bg-white border rounded-lg p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Net Worth Trajectory Fan Chart</h3>
        <McFanChart detail={data} />
      </div>

      {/* Terminal wealth distribution */}
      <div className="bg-white border rounded-lg p-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-gray-700">Terminal Wealth Distribution</h3>
          {!data.individual_runs && (
            <button
              className="text-xs text-blue-600 hover:underline"
              onClick={() => setIncludeRuns(true)}
            >
              Load distribution data
            </button>
          )}
        </div>
        {data.individual_runs ? (
          <TerminalWealthDist runs={data.individual_runs} />
        ) : (
          <p className="text-sm text-gray-400 py-6 text-center">
            Click "Load distribution data" to fetch individual run results.
          </p>
        )}
      </div>
    </div>
  );
}
