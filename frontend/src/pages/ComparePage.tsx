import { useSearchParams } from "react-router-dom";
import { useRun } from "../api/runs";
import NetWorthChart from "../components/charts/NetWorthChart";
import { formatDollar } from "../utils/formatters";

function RunColumn({ runId }: { runId: number }) {
  const { data, isLoading } = useRun(runId);
  if (isLoading) return <div className="text-gray-400 text-sm">Loading run #{runId}…</div>;
  if (!data) return <div className="text-red-500 text-sm">Run #{runId} not found</div>;
  const { run, metrics } = data;
  return (
    <div className="space-y-3">
      <div className="bg-white border rounded-lg p-3">
        <p className="text-sm font-semibold text-gray-800">
          #{run.id}{run.label ? ` — ${run.label}` : ""}
        </p>
        <p className={`text-xs ${run.ruin_period != null ? "text-red-600" : "text-green-600"}`}>
          {run.ruin_period != null ? `Ruin at period ${run.ruin_period}` : "Solvent"}
        </p>
        <p className="text-lg font-bold text-blue-700">
          {run.terminal_net_worth != null ? formatDollar(run.terminal_net_worth) : "—"}
        </p>
      </div>
      <div className="bg-white border rounded-lg p-3">
        <h4 className="text-xs font-semibold text-gray-600 mb-2">Net Worth</h4>
        <NetWorthChart metrics={metrics} />
      </div>
    </div>
  );
}

export default function ComparePage() {
  const [searchParams] = useSearchParams();
  const idsParam = searchParams.get("ids") ?? "";
  const ids = idsParam
    .split(",")
    .map(Number)
    .filter((n) => !isNaN(n) && n > 0);

  if (ids.length === 0) {
    return (
      <div className="text-gray-500 text-sm py-8 text-center">
        Add <code className="bg-gray-100 px-1 rounded">?ids=1,2,3</code> to the URL to compare runs.
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-800 mb-4">Compare Runs</h2>
      <div
        className="grid gap-4"
        style={{ gridTemplateColumns: `repeat(${Math.min(ids.length, 3)}, 1fr)` }}
      >
        {ids.map((id) => (
          <RunColumn key={id} runId={id} />
        ))}
      </div>
    </div>
  );
}
