import { useParams } from "react-router-dom";
import { useRun, useRunTax } from "../api/runs";
import FreeCashFlowChart from "../components/charts/FreeCashFlowChart";
import NetWorthChart from "../components/charts/NetWorthChart";
import TaxAnalysisChart from "../components/charts/TaxAnalysisChart";
import { findRetirementDate, findRmdDate } from "../utils/chartHelpers";
import { formatDollar } from "../utils/formatters";

export default function RunDetailPage() {
  const { id } = useParams<{ id: string }>();
  const runId = Number(id);
  const { data, isLoading, error } = useRun(runId);
  const { data: taxRows } = useRunTax(runId);

  if (isLoading) return <p className="text-gray-400">Loading…</p>;
  if (error || !data) return <p className="text-red-500">Failed to load run.</p>;

  const { run, metrics } = data;
  const retirementDate = findRetirementDate(metrics);
  const rmdDate = findRmdDate(metrics);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-800">
            Run #{run.id}{run.label ? ` — ${run.label}` : ""}
          </h2>
          <p className="text-sm text-gray-500">{run.run_started_at?.slice(0, 16).replace("T", " ")}</p>
          {run.tags.length > 0 && (
            <div className="flex gap-1 mt-1">
              {run.tags.map((t) => (
                <span key={t} className="bg-blue-100 text-blue-800 text-xs px-1.5 py-0.5 rounded">{t}</span>
              ))}
            </div>
          )}
        </div>
        <div className="text-right">
          <p className="text-sm text-gray-500">Terminal Net Worth</p>
          <p className="text-2xl font-bold text-blue-700">
            {run.terminal_net_worth != null ? formatDollar(run.terminal_net_worth) : "—"}
          </p>
          <p className={`text-sm ${run.ruin_period != null ? "text-red-600" : "text-green-600"}`}>
            {run.ruin_period != null ? `Ruin at period ${run.ruin_period}` : "Solvent"}
          </p>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg border p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Net Worth & Debt</h3>
          <NetWorthChart metrics={metrics} />
        </div>
        <div className="bg-white rounded-lg border p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Free Cash Flow</h3>
          <FreeCashFlowChart metrics={metrics} />
        </div>
      </div>

      {taxRows && taxRows.length > 0 && (
        <div className="bg-white rounded-lg border p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Tax Analysis</h3>
          <TaxAnalysisChart rows={taxRows} retirementDate={retirementDate} rmdDate={rmdDate} />
        </div>
      )}

      {run.notes && (
        <div className="bg-yellow-50 border border-yellow-200 rounded p-3 text-sm text-gray-700">
          <strong>Notes:</strong> {run.notes}
        </div>
      )}
    </div>
  );
}
