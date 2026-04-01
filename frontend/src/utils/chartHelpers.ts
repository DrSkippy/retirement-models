import type { ScenarioMetricRow } from "../types/runs";

/** Return the period_date of the first row where retirement_withdrawal > 0. */
export function findRetirementDate(metrics: ScenarioMetricRow[]): string | null {
  const row = metrics.find((r) => r.retirement_withdrawal > 0);
  return row ? row.period_date : null;
}

/** Return the period_date of the first row where age >= 73. */
export function findRmdDate(metrics: ScenarioMetricRow[]): string | null {
  const row = metrics.find((r) => r.age >= 73);
  return row ? row.period_date : null;
}
