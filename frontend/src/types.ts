export type AnyRecord = Record<string, unknown>;

export type PageKey =
  | "dashboard"
  | "new"
  | "budget"
  | "gpr"
  | "sales"
  | "credit"
  | "bank"
  | "tech"
  | "ai"
  | "billing"
  | "dscr"
  | "scenarios"
  | "optimization"
  | "improvement"
  | "history"
  | "users";

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
  apartments_count?: number;
  tp_total_cost_override?: number;
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
  max_land_price?: number | null;
  land_verdict?: string | null;
  land_verdict_level?: string | null;
  llcr?: number | null;
  escrow_coverage_at_delivery?: number | null;
  bank_verdict?: string | null;
  bank_verdict_code?: string | null;
  bank_verdict_level?: string | null;
  tech_connection_cost?: number | null;
  tech_connection_deficit?: number | null;
  tech_connection_verdict?: string | null;
  tech_connection_verdict_level?: string | null;
}

export interface EscrowFinancing {
  schedule?: AnyRecord[];
  delivery_month?: number;
  equity_pool?: number;
  equity_used?: number;
  equity_share?: number;
  credit_limit?: number;
  base_rate?: number;
  escrow_covered_rate?: number;
  total_interest?: number;
  max_debt?: number;
  max_debt_month?: number;
  escrow_at_delivery?: number;
  debt_at_delivery?: number;
  escrow_coverage_at_delivery?: number | null;
  ending_debt?: number;
  repayment_finished_month?: number | null;
  funding_gap_total?: number;
  llcr?: number | null;
  llcr_details?: AnyRecord;
  revenue_total?: number;
  profit?: number;
  margin?: number;
  [key: string]: unknown;
}

export interface BankApproval {
  verdict?: string;
  verdict_code?: string;
  verdict_level?: string;
  criteria?: AnyRecord[];
  passed_count?: number;
  failed_critical_count?: number;
  failed_warning_count?: number;
  recommendations?: string[];
  stress_tests?: AnyRecord;
  requirements?: AnyRecord;
  [key: string]: unknown;
}

export interface BillingPlan {
  code: string;
  name: string;
  price_rub: number;
  generate_quota: number;
  ai_quota: number;
  description: string;
  purchasable: boolean;
}

export interface BillingInfo {
  login?: string;
  plan: string;
  plan_name: string;
  paid_until?: string | null;
  active: boolean;
  effective_plan?: string;
  generate_quota: number;
  ai_quota: number;
  usage?: { generate: number; ai: number };
  remaining?: { generate: number; ai: number };
  month?: string;
  plans?: BillingPlan[];
  payment?: { provider: string; configured: boolean; manual_instructions?: string | null };
}

export interface PaymentResult {
  status: string;
  confirmation_url?: string | null;
  instructions?: string | null;
  error?: string | null;
  [key: string]: unknown;
}

export interface AiStatus {
  provider: string;
  configured: boolean;
  model?: string | null;
  detail?: string | null;
}

export interface AiChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface AiChatResponse {
  status: string;
  answer?: string | null;
  model?: string | null;
  generated_at?: string;
  error?: string | null;
  [key: string]: unknown;
}

export interface AiConclusion {
  status: string;
  conclusion?: string | null;
  provider?: string;
  model?: string | null;
  generated_at?: string;
  error?: string | null;
  [key: string]: unknown;
}

export interface TechConnection {
  verdict?: string;
  verdict_code?: string;
  verdict_level?: string;
  items?: AnyRecord[];
  apartments?: number;
  apartments_source?: string;
  residents?: number;
  loads?: AnyRecord;
  calculated_cost?: number;
  total_cost?: number;
  cost_source?: string;
  budget_allocation?: number;
  networks_included_in_budget?: boolean;
  deficit?: number;
  deficit_share_of_budget?: number;
  max_lead_time_months?: number;
  construction_months?: number;
  schedule_issues?: string[];
  [key: string]: unknown;
}

export interface LandValuation {
  verdict?: string;
  verdict_code?: string;
  verdict_level?: string;
  max_land_price?: number;
  break_even_land_price?: number;
  asking_land_price?: number | null;
  safety_reserve?: number | null;
  max_land_price_per_land_m2?: number | null;
  land_share_of_budget?: number | null;
  land_share_of_revenue?: number | null;
  costs_without_land?: number;
  interest_ratio?: number;
  target_margin?: number;
  method?: string;
  [key: string]: unknown;
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
  land_valuation?: LandValuation;
  escrow_financing?: EscrowFinancing;
  bank_approval?: BankApproval;
  tech_connection?: TechConnection;
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
  adminOnly?: boolean;
}

export interface AdminUser {
  login: string;
  role: string;
  plan?: string;
  plan_name?: string;
  paid_until?: string | null;
  active?: boolean;
}
