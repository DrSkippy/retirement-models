import { useEffect, useState } from "react";
import { Plus, Pencil, Trash2, X, Save, AlertCircle, Check } from "lucide-react";
import {
  useWorldConfig,
  useSaveWorldConfig,
  useAssets,
  useSaveAsset,
  useDeleteAsset,
} from "../api/configuration";
import type {
  WorldConfig,
  Asset,
  AssetFile,
  AssetType,
  TaxClass,
  EquityAsset,
  RealEstateAsset,
  SalaryAsset,
} from "../types/configuration";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const DATE_PLACEHOLDERS = ["first_date", "end_date", "retirement"] as const;

const TAX_CLASSES: TaxClass[] = [
  "income",
  "capital_gain",
  "social_security",
  "roth",
];

const TYPE_COLORS: Record<AssetType, string> = {
  Equity: "bg-blue-100 text-blue-700",
  RealEstate: "bg-green-100 text-green-700",
  Salary: "bg-purple-100 text-purple-700",
};

function fmt$(n: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);
}

function pct(n: number) {
  return `${(n * 100).toFixed(2)}%`;
}

function slugify(name: string) {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_|_$/g, "");
}

// ---------------------------------------------------------------------------
// Generic form primitives
// ---------------------------------------------------------------------------

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">
        {label}
        {hint && <span className="ml-1 text-gray-400 font-normal">{hint}</span>}
      </label>
      {children}
    </div>
  );
}

const inputCls =
  "w-full border border-gray-200 rounded-md px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300 bg-white";

function TextInput({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <input
      type="text"
      className={inputCls}
      value={value}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

function NumberInput({
  value,
  onChange,
  step = 0.01,
  min,
}: {
  value: number;
  onChange: (v: number) => void;
  step?: number;
  min?: number;
}) {
  return (
    <input
      type="number"
      className={inputCls}
      value={value}
      step={step}
      min={min}
      onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
    />
  );
}

function DateInput({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <input
      type="date"
      className={inputCls}
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

function SelectInput({
  value,
  options,
  onChange,
}: {
  value: string;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
}) {
  return (
    <select
      className={inputCls}
      value={value}
      onChange={(e) => onChange(e.target.value)}
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mt-4 mb-2 border-b pb-1">
      {children}
    </h3>
  );
}

// ---------------------------------------------------------------------------
// World Config Form
// ---------------------------------------------------------------------------

function WorldConfigForm() {
  const { data, isLoading, error } = useWorldConfig();
  const save = useSaveWorldConfig();
  const [form, setForm] = useState<WorldConfig | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (data) setForm(structuredClone(data));
  }, [data]);

  if (isLoading) return <p className="text-gray-400 text-sm">Loading…</p>;
  if (error || !form)
    return <p className="text-red-500 text-sm">Failed to load config.</p>;

  function set<K extends keyof WorldConfig>(key: K, val: WorldConfig[K]) {
    setForm((f) => f && { ...f, [key]: val });
  }

  function setTax(key: keyof WorldConfig["tax_classes"], val: number) {
    setForm((f) =>
      f ? { ...f, tax_classes: { ...f.tax_classes, [key]: val } } : f
    );
  }

  const allocationSum = form.stock_allocation + form.bond_allocation;
  const allocationOk = Math.abs(allocationSum - 1.0) < 0.001;

  async function handleSave() {
    if (!form) return;
    await save.mutateAsync(form);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <div className="bg-white rounded-lg border p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold text-gray-800">
          World Configuration
        </h2>
        <button
          onClick={handleSave}
          disabled={save.isPending || !allocationOk}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {saved ? (
            <>
              <Check size={14} /> Saved
            </>
          ) : (
            <>
              <Save size={14} /> Save
            </>
          )}
        </button>
      </div>

      <div className="grid grid-cols-2 gap-x-6 gap-y-3">
        <SectionHeading>Personal</SectionHeading>
        <div className="col-span-2 grid grid-cols-2 gap-x-6 gap-y-3">
          <Field label="Birth Date">
            <DateInput
              value={form.birth_date}
              onChange={(v) => set("birth_date", v)}
            />
          </Field>
          <Field label="Spouse Birth Date">
            <DateInput
              value={form.spouse_birth_date}
              onChange={(v) => set("spouse_birth_date", v)}
            />
          </Field>
          <Field label="Retirement Age">
            <NumberInput
              value={form.retirement_age}
              onChange={(v) => set("retirement_age", Math.round(v))}
              step={1}
              min={50}
            />
          </Field>
          <Field label="RMD Age">
            <NumberInput
              value={form.rmd_age}
              onChange={(v) => set("rmd_age", Math.round(v))}
              step={1}
              min={70}
            />
          </Field>
          <Field label="Simulation Start Date">
            <DateInput
              value={form.start_date}
              onChange={(v) => set("start_date", v)}
            />
          </Field>
          <Field label="Simulation End Date">
            <DateInput
              value={form.end_date}
              onChange={(v) => set("end_date", v)}
            />
          </Field>
        </div>

        <SectionHeading>Savings & Withdrawals</SectionHeading>
        <div className="col-span-2 grid grid-cols-2 gap-x-6 gap-y-3">
          <Field label="Savings Rate" hint="(0.20 = 20%)">
            <NumberInput
              value={form.savings_rate}
              onChange={(v) => set("savings_rate", v)}
              step={0.01}
              min={0}
            />
          </Field>
          <Field label="Roth Savings Rate" hint="(0.05 = 5%)">
            <NumberInput
              value={form.roth_savings_rate}
              onChange={(v) => set("roth_savings_rate", v)}
              step={0.01}
              min={0}
            />
          </Field>
          <Field label="Withdrawal Rate" hint="(0.04 = 4%)">
            <NumberInput
              value={form.withdrawal_rate}
              onChange={(v) => set("withdrawal_rate", v)}
              step={0.005}
              min={0}
            />
          </Field>
          <Field label="Inflation Rate" hint="(0.025 = 2.5%)">
            <NumberInput
              value={form.inflation_rate}
              onChange={(v) => set("inflation_rate", v)}
              step={0.005}
              min={0}
            />
          </Field>
        </div>

        <SectionHeading>Portfolio Allocation</SectionHeading>
        <div className="col-span-2 grid grid-cols-2 gap-x-6 gap-y-3">
          <Field label="Stock Allocation" hint="(0.60 = 60%)">
            <NumberInput
              value={form.stock_allocation}
              onChange={(v) => set("stock_allocation", v)}
              step={0.05}
              min={0}
            />
          </Field>
          <Field label="Bond Allocation" hint="(0.40 = 40%)">
            <NumberInput
              value={form.bond_allocation}
              onChange={(v) => set("bond_allocation", v)}
              step={0.05}
              min={0}
            />
          </Field>
          {!allocationOk && (
            <div className="col-span-2 flex items-center gap-1.5 text-amber-600 text-xs">
              <AlertCircle size={13} />
              Allocations must sum to 1.0 (currently {allocationSum.toFixed(3)})
            </div>
          )}
        </div>

        <SectionHeading>Tax Rates</SectionHeading>
        <div className="col-span-2 grid grid-cols-2 gap-x-6 gap-y-3">
          <Field label="Ordinary Income" hint="(0.37 = 37%)">
            <NumberInput
              value={form.tax_classes.income}
              onChange={(v) => setTax("income", v)}
              step={0.01}
              min={0}
            />
          </Field>
          <Field label="Capital Gains" hint="(0.20 = 20%)">
            <NumberInput
              value={form.tax_classes.capital_gain}
              onChange={(v) => setTax("capital_gain", v)}
              step={0.01}
              min={0}
            />
          </Field>
          <Field label="Social Security" hint="(0.153 = 15.3%)">
            <NumberInput
              value={form.tax_classes.social_security}
              onChange={(v) => setTax("social_security", v)}
              step={0.001}
              min={0}
            />
          </Field>
          <Field label="Roth" hint="always 0.0">
            <input
              type="number"
              className={`${inputCls} bg-gray-50 text-gray-400 cursor-not-allowed`}
              value={form.tax_classes.roth}
              readOnly
            />
          </Field>
        </div>
      </div>

      {save.isError && (
        <p className="mt-3 text-red-500 text-xs">
          Failed to save. Check the API.
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Asset type-specific form sections
// ---------------------------------------------------------------------------

function EquityFields({
  asset,
  onChange,
}: {
  asset: EquityAsset;
  onChange: (a: EquityAsset) => void;
}) {
  function set<K extends keyof EquityAsset>(key: K, val: EquityAsset[K]) {
    onChange({ ...asset, [key]: val });
  }

  return (
    <>
      <SectionHeading>Values</SectionHeading>
      <div className="grid grid-cols-2 gap-x-6 gap-y-3">
        <Field label="Initial Value ($)">
          <NumberInput
            value={asset.initial_value}
            onChange={(v) => set("initial_value", v)}
            step={1000}
            min={0}
          />
        </Field>
        <Field label="Expense Ratio" hint="(0.0005 = 0.05%)">
          <NumberInput
            value={asset.initial_expense_rate}
            onChange={(v) => set("initial_expense_rate", v)}
            step={0.0001}
            min={0}
          />
        </Field>
        <Field label="Appreciation Rate" hint="(0.06 = 6%/yr)">
          <NumberInput
            value={asset.appreciation_rate}
            onChange={(v) => set("appreciation_rate", v)}
            step={0.005}
            min={0}
          />
        </Field>
        <Field label="Appreciation Volatility" hint="(0.02 = ±2%)">
          <NumberInput
            value={asset.appreciation_rate_volatility}
            onChange={(v) => set("appreciation_rate_volatility", v)}
            step={0.005}
            min={0}
          />
        </Field>
        <Field label="Dividend Rate" hint="(0.002 = 0.2%/yr)">
          <NumberInput
            value={asset.dividend_rate}
            onChange={(v) => set("dividend_rate", v)}
            step={0.001}
            min={0}
          />
        </Field>
      </div>
      <SectionHeading>Historical Returns (optional)</SectionHeading>
      <Field
        label="SP500 Monthly Returns CSV"
        hint="leave blank to use synthetic returns"
      >
        <TextInput
          value={asset.sampled_monthly_sp500_returns ?? ""}
          onChange={(v) =>
            set("sampled_monthly_sp500_returns", v || undefined)
          }
          placeholder="../sp500-historical-portfolio-returns/out_data/monthly_returns.csv"
        />
      </Field>
    </>
  );
}

function RealEstateFields({
  asset,
  onChange,
}: {
  asset: RealEstateAsset;
  onChange: (a: RealEstateAsset) => void;
}) {
  function set<K extends keyof RealEstateAsset>(
    key: K,
    val: RealEstateAsset[K]
  ) {
    onChange({ ...asset, [key]: val });
  }

  return (
    <>
      <SectionHeading>Property Value & Debt</SectionHeading>
      <div className="grid grid-cols-2 gap-x-6 gap-y-3">
        <Field label="Current Value ($)">
          <NumberInput
            value={asset.initial_value}
            onChange={(v) => set("initial_value", v)}
            step={5000}
            min={0}
          />
        </Field>
        <Field label="Outstanding Debt ($)">
          <NumberInput
            value={asset.initial_debt}
            onChange={(v) => set("initial_debt", v)}
            step={1000}
            min={0}
          />
        </Field>
      </div>
      <SectionHeading>Appreciation & Carrying Costs</SectionHeading>
      <div className="grid grid-cols-2 gap-x-6 gap-y-3">
        <Field label="Appreciation Rate" hint="(0.02 = 2%/yr)">
          <NumberInput
            value={asset.appreciation_rate}
            onChange={(v) => set("appreciation_rate", v)}
            step={0.005}
            min={0}
          />
        </Field>
        <Field label="Property Tax Rate" hint="(0.0058 = 0.58%/yr)">
          <NumberInput
            value={asset.property_tax_rate}
            onChange={(v) => set("property_tax_rate", v)}
            step={0.0001}
            min={0}
          />
        </Field>
        <Field label="Annual Insurance Cost ($)">
          <NumberInput
            value={asset.insurance_cost}
            onChange={(v) => set("insurance_cost", v)}
            step={100}
            min={0}
          />
        </Field>
        <Field label="Management Fee Rate" hint="(0.10 = 10%)">
          <NumberInput
            value={asset.management_fee_rate}
            onChange={(v) => set("management_fee_rate", v)}
            step={0.01}
            min={0}
          />
        </Field>
      </div>
      <SectionHeading>Rental Income & Expenses</SectionHeading>
      <div className="grid grid-cols-2 gap-x-6 gap-y-3">
        <Field label="Monthly Rental Income ($)">
          <NumberInput
            value={asset.monthly_rental_income}
            onChange={(v) => set("monthly_rental_income", v)}
            step={50}
            min={0}
          />
        </Field>
        <Field label="Rental Expense Rate" hint="(0.10 = 10% of income)">
          <NumberInput
            value={asset.rental_expense_rate}
            onChange={(v) => set("rental_expense_rate", v)}
            step={0.01}
            min={0}
          />
        </Field>
      </div>
      <SectionHeading>Mortgage</SectionHeading>
      <div className="grid grid-cols-2 gap-x-6 gap-y-3">
        <Field label="Interest Rate" hint="(0.028 = 2.8%)">
          <NumberInput
            value={asset.interest_rate}
            onChange={(v) => set("interest_rate", v)}
            step={0.0001}
            min={0}
          />
        </Field>
        <Field label="Monthly Payment ($)">
          <NumberInput
            value={asset.payment}
            onChange={(v) => set("payment", v)}
            step={10}
            min={0}
          />
        </Field>
      </div>
    </>
  );
}

function BenefitTableEditor({
  value,
  onChange,
}: {
  value: Record<string, number>;
  onChange: (v: Record<string, number>) => void;
}) {
  const rows = Object.entries(value).sort(
    ([a], [b]) => parseInt(a) - parseInt(b)
  );

  function updateAge(oldAge: string, newAge: string) {
    const next = { ...value };
    const benefit = next[oldAge];
    delete next[oldAge];
    next[newAge] = benefit;
    onChange(next);
  }

  function updateBenefit(age: string, amount: number) {
    onChange({ ...value, [age]: amount });
  }

  function removeRow(age: string) {
    const next = { ...value };
    delete next[age];
    onChange(next);
  }

  function addRow() {
    const maxAge = rows.length
      ? Math.max(...rows.map(([a]) => parseInt(a))) + 1
      : 62;
    onChange({ ...value, [String(maxAge)]: 0 });
  }

  return (
    <div>
      <div className="space-y-1.5 mb-2">
        {rows.map(([age, benefit]) => (
          <div key={age} className="flex items-center gap-2">
            <span className="text-xs text-gray-500 w-12">Age</span>
            <input
              type="number"
              className="border border-gray-200 rounded px-2 py-1 text-sm w-16 focus:outline-none focus:ring-2 focus:ring-blue-300"
              value={age}
              step={1}
              min={62}
              onChange={(e) => updateAge(age, e.target.value)}
            />
            <span className="text-xs text-gray-500 w-16">$/month</span>
            <input
              type="number"
              className="border border-gray-200 rounded px-2 py-1 text-sm w-28 focus:outline-none focus:ring-2 focus:ring-blue-300"
              value={benefit}
              step={10}
              min={0}
              onChange={(e) =>
                updateBenefit(age, parseFloat(e.target.value) || 0)
              }
            />
            <button
              type="button"
              onClick={() => removeRow(age)}
              className="text-gray-400 hover:text-red-500"
            >
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
      <button
        type="button"
        onClick={addRow}
        className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800"
      >
        <Plus size={12} /> Add age bracket
      </button>
    </div>
  );
}

function SalaryFields({
  asset,
  onChange,
}: {
  asset: SalaryAsset;
  onChange: (a: SalaryAsset) => void;
}) {
  function set<K extends keyof SalaryAsset>(key: K, val: SalaryAsset[K]) {
    onChange({ ...asset, [key]: val });
  }

  return (
    <>
      <SectionHeading>Income</SectionHeading>
      <div className="grid grid-cols-2 gap-x-6 gap-y-3">
        <Field label="Annual Salary ($)" hint="optional if using age-based benefits">
          <NumberInput
            value={asset.salary ?? 0}
            onChange={(v) => set("salary", v || undefined)}
            step={1000}
            min={0}
          />
        </Field>
        <Field label="COLA" hint="(0.015 = 1.5%/yr)">
          <NumberInput
            value={asset.cola}
            onChange={(v) => set("cola", v)}
            step={0.005}
            min={0}
          />
        </Field>
        <Field label="Initial Debt ($)">
          <NumberInput
            value={asset.initial_debt}
            onChange={(v) => set("initial_debt", v)}
            step={100}
            min={0}
          />
        </Field>
      </div>
      <SectionHeading>Age-Based Monthly Benefits</SectionHeading>
      <p className="text-xs text-gray-500 mb-2">
        Benefit amount by claiming age (Social Security). Leave empty for
        flat salary.
      </p>
      <BenefitTableEditor
        value={asset.retirement_age_based_benefit ?? {}}
        onChange={(v) =>
          set(
            "retirement_age_based_benefit",
            Object.keys(v).length ? v : undefined
          )
        }
      />
    </>
  );
}

// ---------------------------------------------------------------------------
// Asset Modal
// ---------------------------------------------------------------------------

const DEFAULT_EQUITY: EquityAsset = {
  name: "",
  description: "",
  type: "Equity",
  start_date: "first_date",
  end_date: "end_date",
  tax_class: "income",
  initial_value: 0,
  initial_expense_rate: 0.0005,
  appreciation_rate: 0.06,
  appreciation_rate_volatility: 0.02,
  dividend_rate: 0.002,
};

const DEFAULT_REALESTATE: RealEstateAsset = {
  name: "",
  description: "",
  type: "RealEstate",
  start_date: "first_date",
  end_date: "end_date",
  tax_class: "income",
  initial_value: 0,
  initial_debt: 0,
  appreciation_rate: 0.02,
  property_tax_rate: 0.005,
  insurance_cost: 1200,
  management_fee_rate: 0,
  monthly_rental_income: 0,
  rental_expense_rate: 0,
  interest_rate: 0.07,
  payment: 0,
};

const DEFAULT_SALARY: SalaryAsset = {
  name: "",
  description: "",
  type: "Salary",
  start_date: "first_date",
  end_date: "retirement",
  tax_class: "income",
  salary: undefined,
  cola: 0.015,
  initial_debt: 0,
  retirement_age: "retirement_age",
  retirement_age_based_benefit: undefined,
};

function defaultForType(type: AssetType): Asset {
  if (type === "RealEstate") return structuredClone(DEFAULT_REALESTATE);
  if (type === "Salary") return structuredClone(DEFAULT_SALARY);
  return structuredClone(DEFAULT_EQUITY);
}

interface ModalProps {
  initial: { filename: string; data: Asset } | null;
  onClose: () => void;
  onSave: (filename: string, data: Asset) => Promise<void>;
  saving: boolean;
}

function AssetModal({ initial, onClose, onSave, saving }: ModalProps) {
  const isNew = initial === null;
  const [filename, setFilename] = useState(initial?.filename ?? "");
  const [asset, setAsset] = useState<Asset>(
    initial?.data ?? structuredClone(DEFAULT_EQUITY)
  );
  const [autoFilename, setAutoFilename] = useState(isNew);

  function setType(type: AssetType) {
    setAsset(defaultForType(type));
  }

  function setName(name: string) {
    setAsset((a) => ({ ...a, name }));
    if (autoFilename) setFilename(`${slugify(name)}.json`);
  }

  const placeholderOpts = DATE_PLACEHOLDERS.map((p) => ({
    value: p,
    label: p,
  }));

  const taxOpts = TAX_CLASSES.map((t) => ({ value: t, label: t }));

  function setCommon(key: "description" | "tax_class" | "start_date" | "end_date", val: string) {
    // @ts-ignore — safe because key matches string fields on all Asset subtypes
    setAsset((a) => ({ ...a, [key]: val }));
  }

  async function handleSave() {
    if (!filename || !asset.name) return;
    await onSave(filename, asset);
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 overflow-y-auto py-8">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl mx-4">
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h2 className="text-base font-semibold text-gray-800">
            {isNew ? "New Asset" : `Edit — ${initial.data.name}`}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={18} />
          </button>
        </div>

        <div className="px-6 py-5 space-y-3">
          {/* Type selector (only when creating) */}
          {isNew && (
            <>
              <SectionHeading>Asset Type</SectionHeading>
              <div className="flex gap-3">
                {(["Equity", "RealEstate", "Salary"] as AssetType[]).map(
                  (t) => (
                    <button
                      key={t}
                      type="button"
                      onClick={() => setType(t)}
                      className={`flex-1 py-2 text-sm rounded-lg border font-medium transition-colors ${
                        asset.type === t
                          ? "border-blue-500 bg-blue-50 text-blue-700"
                          : "border-gray-200 text-gray-600 hover:border-gray-300"
                      }`}
                    >
                      {t}
                    </button>
                  )
                )}
              </div>
            </>
          )}

          {/* Common fields */}
          <SectionHeading>Common</SectionHeading>
          <div className="grid grid-cols-2 gap-x-6 gap-y-3">
            <Field label="Name">
              <TextInput
                value={asset.name}
                onChange={setName}
                placeholder="e.g. Roth IRA Stock"
              />
            </Field>
            <Field label="Description">
              <TextInput
                value={asset.description}
                onChange={(v) => setCommon("description", v)}
              />
            </Field>
            <Field label="Tax Class">
              <SelectInput
                value={asset.tax_class}
                options={taxOpts}
                onChange={(v) => setCommon("tax_class", v as TaxClass)}
              />
            </Field>
            <div /> {/* spacer */}
            <Field label="Start Date">
              <SelectInput
                value={asset.start_date}
                options={placeholderOpts}
                onChange={(v) => setCommon("start_date", v)}
              />
            </Field>
            <Field label="End Date">
              <SelectInput
                value={asset.end_date}
                options={placeholderOpts}
                onChange={(v) => setCommon("end_date", v)}
              />
            </Field>
          </div>

          {/* Type-specific fields */}
          {asset.type === "Equity" && (
            <EquityFields
              asset={asset as EquityAsset}
              onChange={(a) => setAsset(a)}
            />
          )}
          {asset.type === "RealEstate" && (
            <RealEstateFields
              asset={asset as RealEstateAsset}
              onChange={(a) => setAsset(a)}
            />
          )}
          {asset.type === "Salary" && (
            <SalaryFields
              asset={asset as SalaryAsset}
              onChange={(a) => setAsset(a)}
            />
          )}

          {/* Filename */}
          <SectionHeading>File</SectionHeading>
          <Field label="Filename" hint=".json">
            <div className="flex items-center gap-2">
              <input
                type="text"
                className={inputCls}
                value={filename}
                onChange={(e) => {
                  setFilename(e.target.value);
                  setAutoFilename(false);
                }}
                placeholder="my_asset.json"
                readOnly={!isNew}
              />
              {isNew && (
                <button
                  type="button"
                  onClick={() => {
                    setFilename(`${slugify(asset.name)}.json`);
                    setAutoFilename(true);
                  }}
                  className="text-xs text-blue-600 hover:text-blue-800 whitespace-nowrap"
                >
                  Auto
                </button>
              )}
            </div>
          </Field>
        </div>

        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !filename || !asset.name}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-md text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            <Save size={14} />
            {saving ? "Saving…" : "Save Asset"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Asset card
// ---------------------------------------------------------------------------

function assetSummary(a: Asset): string {
  if (a.type === "Equity") {
    const e = a as EquityAsset;
    return `${fmt$(e.initial_value)} · ${pct(e.appreciation_rate)}/yr · ${pct(e.dividend_rate)} div`;
  }
  if (a.type === "RealEstate") {
    const r = a as RealEstateAsset;
    return `${fmt$(r.initial_value)} value · ${fmt$(r.initial_debt)} debt · ${fmt$(r.monthly_rental_income)}/mo rent`;
  }
  const s = a as SalaryAsset;
  if (s.salary) return `${fmt$(s.salary)}/yr · ${pct(s.cola)} COLA`;
  const benefits = s.retirement_age_based_benefit ?? {};
  const ages = Object.keys(benefits).sort((a, b) => parseInt(a) - parseInt(b));
  if (ages.length === 0) return "No benefit table";
  const lo = benefits[ages[0]];
  const hi = benefits[ages[ages.length - 1]];
  return `${fmt$(lo)}–${fmt$(hi)}/mo by claiming age`;
}

function AssetCard({
  file,
  onEdit,
  onDelete,
}: {
  file: AssetFile;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const { filename, data } = file;

  return (
    <div className="bg-white rounded-lg border p-4 flex flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <span
            className={`inline-block px-2 py-0.5 rounded text-xs font-medium mb-1 ${TYPE_COLORS[data.type]}`}
          >
            {data.type}
          </span>
          <h3 className="font-medium text-gray-800 text-sm leading-snug">
            {data.name}
          </h3>
          <p className="text-xs text-gray-500 truncate">{data.description}</p>
        </div>
      </div>
      <p className="text-xs text-gray-600 font-mono leading-relaxed">
        {assetSummary(data)}
      </p>
      <div className="flex items-center justify-between pt-1 border-t">
        <span className="text-xs text-gray-400 font-mono">{filename}</span>
        <div className="flex items-center gap-2">
          <button
            onClick={onEdit}
            className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 transition-colors"
          >
            <Pencil size={12} /> Edit
          </button>
          <button
            onClick={onDelete}
            className="flex items-center gap-1 text-xs text-red-500 hover:text-red-700 transition-colors"
          >
            <Trash2 size={12} /> Delete
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Assets Section
// ---------------------------------------------------------------------------

function AssetsSection() {
  const { data: files, isLoading, error } = useAssets();
  const saveAsset = useSaveAsset();
  const deleteAsset = useDeleteAsset();

  const [editing, setEditing] = useState<AssetFile | null | "new">(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  if (isLoading) return <p className="text-gray-400 text-sm">Loading…</p>;
  if (error) return <p className="text-red-500 text-sm">Failed to load assets.</p>;

  async function handleSave(filename: string, data: Asset) {
    await saveAsset.mutateAsync({ filename, data });
  }

  async function handleDelete(filename: string) {
    await deleteAsset.mutateAsync(filename);
    setConfirmDelete(null);
  }

  const modalFile =
    editing === "new"
      ? null
      : editing;

  const showModal = editing !== null;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold text-gray-800">Assets</h2>
        <button
          onClick={() => setEditing("new")}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors"
        >
          <Plus size={14} /> New Asset
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {(files ?? []).map((f) => (
          <AssetCard
            key={f.filename}
            file={f}
            onEdit={() => setEditing({ ...f, data: structuredClone(f.data) })}
            onDelete={() => setConfirmDelete(f.filename)}
          />
        ))}
      </div>

      {showModal && (
        <AssetModal
          initial={modalFile}
          onClose={() => setEditing(null)}
          onSave={handleSave}
          saving={saveAsset.isPending}
        />
      )}

      {confirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl shadow-xl p-6 w-80">
            <h3 className="font-semibold text-gray-800 mb-2">Delete asset?</h3>
            <p className="text-sm text-gray-600 mb-4">
              This will permanently delete{" "}
              <span className="font-mono font-medium">{confirmDelete}</span>.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setConfirmDelete(null)}
                className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDelete(confirmDelete)}
                disabled={deleteAsset.isPending}
                className="px-3 py-1.5 rounded-md text-sm font-medium bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
              >
                {deleteAsset.isPending ? "Deleting…" : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ConfigPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-gray-800">Configuration</h1>
      <WorldConfigForm />
      <AssetsSection />
    </div>
  );
}
