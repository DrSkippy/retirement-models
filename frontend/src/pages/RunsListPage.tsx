import { useState } from "react";
import { useRuns } from "../api/runs";
import RunsTable from "../components/RunsTable";

export default function RunsListPage() {
  const [tagFilter, setTagFilter] = useState("");
  const { data: runs, isLoading, error } = useRuns(tagFilter || undefined);

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-800">Simulation Runs</h2>
        <input
          type="text"
          placeholder="Filter by tag…"
          value={tagFilter}
          onChange={(e) => setTagFilter(e.target.value)}
          className="border rounded px-3 py-1.5 text-sm w-48 focus:outline-none focus:ring-2 focus:ring-blue-300"
        />
      </div>
      {isLoading && <p className="text-gray-400">Loading…</p>}
      {error && <p className="text-red-500">Failed to load runs.</p>}
      {runs && <RunsTable runs={runs} />}
    </div>
  );
}
