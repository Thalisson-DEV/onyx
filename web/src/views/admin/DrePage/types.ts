export interface Normalization {
  id: string;
  started_at: string;
}

export interface Structure {
  id: string;
  label: string;
}

export interface Unit {
  id: string;
  code: string;
  name?: string;
}

export interface DreDefinition {
  code: string;
  label: string;
  position: number;
  parent_code: string | null;
  line_type: "SOURCE_SUM" | "CALCULATED" | "SUBTOTAL" | "RESULT" | "PERCENTAGE";
}

export interface DreVersion {
  id: string;
  number: number;
  lines: DreDefinition[];
}

export interface PeriodReadiness {
  status: "READY" | "NOT_READY";
  scope: { period: string };
  blockers: Record<string, number>;
}

export interface ReadinessOverview {
  periods: PeriodReadiness[];
}

export interface DreRun {
  id: string;
  status: "READY" | "NOT_READY";
  scope: {
    normalization_run_id: string;
    structure_version_id: string;
    period: string;
    unit_id: string | null;
  };
  blockers: Record<string, number>;
  provenance: Record<string, string | number | string[]>;
  finished_at: string;
}

export interface DreLine {
  code: string;
  label: string;
  position: number;
  realizado: string;
  orcado: string;
  variance: string;
  variance_percent: string | null;
  realizado_ytd: string;
  orcado_ytd: string;
  variance_ytd: string;
  variance_percent_ytd: string | null;
}

export interface DreStatement {
  run: DreRun;
  version: DreVersion;
  lines: DreLine[];
}

export interface PeriodPoint {
  period: string;
  result_id: string;
  realizado: string;
  orcado: string;
  variance: string;
}

export interface Contributor {
  id: string;
  fact_type: "ACTUAL" | "BUDGET";
  period: string;
  account_code: string;
  account_label: string;
  unit_code: string;
  amount: string;
  amount_basis: string;
  record_date: string | null;
  source_name: string;
  original_filename: string;
  source_id: string;
  source_snapshot_id: string;
  source_execution_id: string;
  sheet_name: string;
  source_row_number: number;
  reference: string | null;
  review_status: string | null;
  unit_name?: string | null;
  source_account_code?: string | null;
  source_account_label?: string | null;
  description?: string | null;
  treatment_title?: string | null;
  treatment_effect?: string | null;
  treatment_version?: number | null;
  original_amount?: string | null;
  original_account_label?: string | null;
}

export interface ContributorPage {
  total: number;
  rows: Contributor[];
}
