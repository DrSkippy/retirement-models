import { useNavigate } from "react-router-dom";
import { useMcSets } from "../api/mc";
import { formatDollar, formatPercent } from "../utils/formatters";

export default function McListPage() {
  const navigate = useNavigate();
  const { data: sets, isLoading, error } = useMcSets();

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-800 mb-4">Monte Carlo Run Sets</h2>
      {isLoading && <p className="text-gray-400">Loading…</p>}
      {error && <p className="text-red-500">Failed to load MC sets.</p>}
      {sets && sets.length === 0 && (
        <p className="text-gray-400 py-8 text-center">No Monte Carlo runs found.</p>
      )}
      <div className="space-y-3">
        {sets?.map((s) => (
          <div
            key={s.id}
            className="bg-white border rounded-lg p-4 cursor-pointer hover:border-blue-300 transition-colors"
            onClick={() => navigate(`/mc/${s.id}`)}
          >
            <div className="flex items-center justify-between">
              <div>
                <span className="font-medium text-gray-800">
                  #{s.id}{s.label ? ` — ${s.label}` : ""}
                </span>
                <span className="ml-3 text-sm text-gray-500">{s.n_runs} runs</span>
                {(s.tags ?? []).length > 0 && (s.tags ?? []).map((t) => (
                  <span key={t} className="ml-1 bg-blue-100 text-blue-800 text-xs px-1.5 py-0.5 rounded">{t}</span>
                ))}
              </div>
              <div className="text-right">
                <span
                  className={`text-sm font-semibold ${
                    s.ruin_probability < 0.05
                      ? "text-green-600"
                      : s.ruin_probability < 0.2
                      ? "text-yellow-600"
                      : "text-red-600"
                  }`}
                >
                  Ruin: {formatPercent(s.ruin_probability)}
                </span>
                <p className="text-xs text-gray-500">
                  P50: {s.terminal_percentiles["50"] != null ? formatDollar(s.terminal_percentiles["50"]) : "—"}
                </p>
              </div>
            </div>
            <p className="text-xs text-gray-400 mt-1">{s.run_started_at?.slice(0, 16).replace("T", " ")}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
