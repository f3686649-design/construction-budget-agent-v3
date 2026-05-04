export type AnyRecord = Record<string, unknown>;

export type PageKey =
  | "dashboard"
  | "new"
  | "budget"
  | "gpr"
  | "sales"
  | "credit"
  | "dscr"
  | "scenarios"
  | "optimization"
  | "improvement"
  | "history";

export interface ProjectInput {
  project_name?: string;
  city?: string;
  object_type?: string;
  object_class?: string;
  land_area?: number;
  land_cost?: number;
  total_area?: number;
  sellable_area?: number;
  floors?: number;
  sale_price_per_m2?: number;
  construction_cost_per_m2?: number;
  gp_contract_price_per_m2?: number;
  construction_months?: number;
  sales_months?: number;
  credit_share?: number;
  credit_rate?: number;
  external_networks_included?: boolean;
  gas_only_cooking?: boolean;
  foundation_type?: string;
  has_underground_part?: boolean;
  sellable_finish_level?: string;
  above_ground_structures_rate_override?: number;
  envelope_roof_walls_rate_override?: number;
  design_cost_override?: number;
  preparation_cost_override?: number;
  earthworks_rate_override?: number;
  sellable_finish_rate_override?: number;
  pile_foundation_rate_override?: number;
  pile_foundation_cost_override?: number;
  pile_count?: number;
  average_pile_depth?: number;
  pile_unit_cost?: number;
  grillage_rate_override?: number;
  foundation_optimization_mode?: string;
  plumbing_rate_override?: number;
  heating_rate_override?: number;
  electrical_rate_override?: number;
  low_voltage_rate_override?: number;
  ventilation_rate_override?: number;
}

export interface AuthUser {
  login: string;
  role: "admin" | "user" | string;
}

export interface AuthSession {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export interface ProjectSummary {
  project_name?: string;
  city?: string;
  total_budget?: number;
  revenue?: number;
  profit?: number;
  margin?: number;
  minimum_dscr?: number | null;
  total_equity_required?: number;
  max_credit_balance?: number;
}

export interface GeneratedProject {
  project_id: string;
  summary: ProjectSummary;
  tep: AnyRecord;
  budget: AnyRecord;
  detailed_budget: {
    items?: AnyRecord[];
    chapter_totals?: AnyRecord[];
    [key: string]: unknown;
  };
  gpr: AnyRecord[];
  sales: AnyRecord[];
  credit: {
    schedule?: AnyRecord[];
    total_interest?: number;
    max_balance?: number;
    [key: string]: unknown;
  };
  cashflow: AnyRecord[];
  dscr: {
    schedule?: AnyRecord[];
    minimum_dscr_after_sales_start?: number | null;
    months_below_1_2?: number;
    [key: string]: unknown;
  };
  economics: AnyRecord;
  risks: AnyRecord[];
  scenarios: AnyRecord[];
  optimization: AnyRecord;
  improvement_plan: AnyRecord;
  excel_filename: string;
  download_url: string;
  input?: AnyRecord;
  metadata?: AnyRecord;
}

export interface ProjectHistoryItem {
  project_id: string;
  calculated_at: string;
  user?: string;
  project_name?: string;
  city?: string;
  total_budget?: number;
  revenue?: number;
  profit?: number;
  margin?: number;
  minimum_dscr?: number | null;
  excel_filename?: string;
  download_url?: string;
}

export interface NavigationItem {
  key: PageKey;
  label: string;
}
