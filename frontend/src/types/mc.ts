export interface McSetSummary {
  id: number;
  config_id: number;
  label: string | null;
  tags: string[];
  n_runs: number;
  random_seed: number | null;
  ruin_probability: number;
  run_started_at: string;
  run_completed_at: string | null;
  terminal_percentiles: Record<string, number>;
  notes: string | null;
}

export interface McRunResult {
  run_index: number;
  terminal_net_worth: number;
  ruin_period: number | null;
}

export interface McSetDetail {
  id: number;
  config_id: number;
  label: string | null;
  tags: string[];
  n_runs: number;
  random_seed: number | null;
  ruin_probability: number;
  run_started_at: string;
  run_completed_at: string | null;
  percentile_bands: Record<string, number[]>; // "p10" | "p25" | "p50" | "p75" | "p90"
  terminal_percentiles: Record<string, number>;
  individual_runs: McRunResult[] | null;
  notes: string | null;
}
