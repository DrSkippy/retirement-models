export type TaxClass = "income" | "capital_gain" | "social_security" | "roth";
export type AssetType = "Equity" | "RealEstate" | "Salary";

export interface TaxClasses {
  income: number;
  capital_gain: number;
  social_security: number;
  roth: number;
}

export interface WorldConfig {
  birth_date: string;
  spouse_birth_date: string;
  retirement_age: number;
  savings_rate: number;
  inflation_rate: number;
  roth_savings_rate: number;
  rmd_age: number;
  tax_classes: TaxClasses;
  withdrawal_rate: number;
  stock_allocation: number;
  bond_allocation: number;
  start_date: string;
  end_date: string;
}

interface BaseAsset {
  name: string;
  description: string;
  type: AssetType;
  start_date: string;
  end_date: string;
  tax_class: TaxClass;
}

export interface EquityAsset extends BaseAsset {
  type: "Equity";
  initial_value: number;
  initial_expense_rate: number;
  appreciation_rate: number;
  appreciation_rate_volatility: number;
  dividend_rate: number;
  sampled_monthly_sp500_returns?: string;
}

export interface RealEstateAsset extends BaseAsset {
  type: "RealEstate";
  initial_value: number;
  initial_debt: number;
  appreciation_rate: number;
  property_tax_rate: number;
  insurance_cost: number;
  management_fee_rate: number;
  monthly_rental_income: number;
  rental_expense_rate: number;
  interest_rate: number;
  payment: number;
}

export interface SalaryAsset extends BaseAsset {
  type: "Salary";
  salary?: number;
  cola: number;
  initial_debt: number;
  retirement_age: string;
  retirement_age_based_benefit?: Record<string, number>;
}

export type Asset = EquityAsset | RealEstateAsset | SalaryAsset;

export interface AssetFile {
  filename: string;
  data: Asset;
}
