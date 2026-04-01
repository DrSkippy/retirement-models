export interface RunSummary {
  id: number;
  config_id: number;
  label: string | null;
  tags: string[];
  run_started_at: string;
  run_completed_at: string | null;
  n_periods: number;
  terminal_net_worth: number | null;
  ruin_period: number | null;
  notes: string | null;
}

export interface ScenarioMetricRow {
  period: number;
  period_date: string;
  age: number;
  retirement_withdrawal: number;
  net_worth: number;
  debt: number;
  monthly_taxable_income: number;
  monthly_operational_expenses: number;
  taxes_paid: number;
  free_cash_flows: number;
  investment: number;
  tax_ordinary_income: number | null;
  tax_capital_gains: number | null;
  tax_social_security: number | null;
}

export interface RunDetail {
  run: RunSummary;
  metrics: ScenarioMetricRow[];
}

export interface AssetMetricRow {
  asset_name: string;
  description: string | null;
  period: number;
  period_date: string;
  value: number;
  debt: number;
  income: number;
  expenses: number;
  extra: Record<string, unknown> | null;
}

export interface TaxRow {
  period: number;
  period_date: string;
  taxes_paid: number;
  monthly_taxable_income: number;
  tax_ordinary_income: number | null;
  tax_capital_gains: number | null;
  tax_social_security: number | null;
  effective_rate: number;
}
