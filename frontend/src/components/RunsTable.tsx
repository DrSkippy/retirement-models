import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from "@tanstack/react-table";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import type { RunSummary } from "../types/runs";
import { formatDollar } from "../utils/formatters";

const col = createColumnHelper<RunSummary>();

const columns = [
  col.accessor("id", { header: "ID", size: 60 }),
  col.accessor("label", { header: "Label", cell: (i) => i.getValue() ?? "—" }),
  col.accessor("tags", {
    header: "Tags",
    cell: (i) =>
      i.getValue().length > 0 ? (
        <span className="flex flex-wrap gap-1">
          {i.getValue().map((t) => (
            <span key={t} className="bg-blue-100 text-blue-800 text-xs px-1.5 py-0.5 rounded">
              {t}
            </span>
          ))}
        </span>
      ) : (
        "—"
      ),
    enableSorting: false,
  }),
  col.accessor("run_started_at", {
    header: "Started",
    cell: (i) => i.getValue().slice(0, 16).replace("T", " "),
  }),
  col.accessor("terminal_net_worth", {
    header: "Terminal NW",
    cell: (i) => (i.getValue() != null ? formatDollar(i.getValue()!) : "—"),
  }),
  col.accessor("ruin_period", {
    header: "Ruin",
    cell: (i) => (i.getValue() != null ? `Period ${i.getValue()}` : "Solvent"),
  }),
  col.accessor("n_periods", { header: "Periods" }),
];

interface Props {
  runs: RunSummary[];
}

export default function RunsTable({ runs }: Props) {
  const navigate = useNavigate();
  const [sorting, setSorting] = useState<SortingState>([{ id: "run_started_at", desc: true }]);

  const table = useReactTable({
    data: runs,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm border-collapse">
        <thead className="bg-gray-50">
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id}>
              {hg.headers.map((h) => (
                <th
                  key={h.id}
                  className="px-3 py-2 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide cursor-pointer select-none"
                  onClick={h.column.getToggleSortingHandler()}
                >
                  {flexRender(h.column.columnDef.header, h.getContext())}
                  {h.column.getIsSorted() === "asc" ? " ▲" : h.column.getIsSorted() === "desc" ? " ▼" : ""}
                </th>
              ))}
              <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">
                Actions
              </th>
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr
              key={row.id}
              className="border-t hover:bg-gray-50 cursor-pointer"
              onClick={() => navigate(`/runs/${row.original.id}`)}
            >
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="px-3 py-2">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
              <td className="px-3 py-2">
                <button
                  className="text-blue-600 hover:underline text-xs mr-2"
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(`/runs/${row.original.id}`);
                  }}
                >
                  View
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {runs.length === 0 && (
        <p className="text-center text-gray-400 py-8">No simulation runs found.</p>
      )}
    </div>
  );
}
