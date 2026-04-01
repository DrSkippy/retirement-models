interface Props {
  probability: number; // 0–1
}

export default function RuinProbabilityGauge({ probability }: Props) {
  const pct = probability * 100;
  const survive = (1 - probability) * 100;

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="w-full h-8 rounded-full overflow-hidden flex">
        <div
          className="h-full flex items-center justify-center text-white text-xs font-bold"
          style={{ width: `${pct}%`, backgroundColor: "#C62828", minWidth: pct > 0 ? "2px" : 0 }}
        >
          {pct >= 8 ? `${pct.toFixed(1)}%` : ""}
        </div>
        <div
          className="h-full flex items-center justify-center text-white text-xs font-bold"
          style={{ width: `${survive}%`, backgroundColor: "#2E7D32" }}
        >
          {survive >= 10 ? `${survive.toFixed(1)}%` : ""}
        </div>
      </div>
      <div className="flex gap-6 text-sm">
        <span style={{ color: "#C62828" }}>■ Ruin: {pct.toFixed(1)}%</span>
        <span style={{ color: "#2E7D32" }}>■ Survive: {survive.toFixed(1)}%</span>
      </div>
    </div>
  );
}
