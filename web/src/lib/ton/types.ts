export interface SpecialistOutcome {
  key: string;
  name: string;
  status: string;
  reason: string;
  limitations: string[];
  actions: string[];
}

export interface Evidence {
  id: string;
  source_snapshot_id?: string;
  sheet_name?: string;
  row_number?: number;
  confidence_level: string;
}

export interface Finding {
  id: string;
  title: string;
  status: string;
  blocking: boolean;
  recommendations: string[];
  evidence: Evidence[];
}

export interface ClosingOutput {
  period: string;
  scope: string;
  unit_id: string | null;
  normalization_run_id: string | null;
  structure_version_id: string | null;
  data_context: string;
  sources: {
    key: string;
    name: string;
    status: string;
    last_success_at?: string;
    acquisition: string;
    direct_integration: string;
  }[];
  specialists: SpecialistOutcome[];
  findings: Finding[];
  findings_scope: string;
  findings_may_have_more: boolean;
  dre_status: string;
  blockers: Record<string, number>;
  executive_brief: Record<string, string>;
  generated_at: string;
}

export interface Publication {
  run_id: string;
  report_id: string;
  revision_id: string;
  status: string;
  report_url: string;
  download_url: string;
  routine_code: string | null;
  report_type?: string | null;
  output: ClosingOutput;
  steps: {
    specialist: string;
    code: string;
    status: string;
    reason?: string;
  }[];
}

export interface ReportGroup {
  latest: Publication;
  previous_count: number;
}

export interface Routine {
  key: string;
  name: string;
  status: string;
  reason: string;
  schedule: string;
  next_run?: string | null;
  last_run?: string | null;
  last_result?: string | null;
  last_report_url?: string | null;
  manual_available: boolean;
}

export interface ClosingSource {
  key: string;
  name: string;
  status: string;
  last_success_at?: string;
  acquisition: string;
  direct_integration: string;
}

export interface SpecialistView {
  key: string;
  name: string;
  objective: string;
  domain: string;
  status: string;
  reason: string;
  required_sources: string[];
  available_capabilities: string[];
  blocked_capabilities: string[];
  last_execution: string | null;
  interaction: "coordinator";
}

export interface ImportDiagnostic {
  code: string;
  count: number;
}

export interface ClientImport {
  id: string;
  source_id: string;
  status: string;
  filename: string;
  format: string;
  size_bytes: number;
  started_at: string;
  finished_at: string | null;
  imported: number;
  rejected: number;
  warnings: number;
  errors: number;
  needs_review: number | null;
  available_for_analysis: number | null;
  diagnostics: ImportDiagnostic[];
  downstream: string[];
  readiness_status: string;
  readiness_run_id: string | null;
  failure_reason: string | null;
}

export interface ClientSource {
  key: string;
  name: string;
  description: string;
  format: string;
  source_id: string | null;
  can_import: boolean;
  status: "CURRENT" | "PROCESSING" | "ATTENTION" | "FAILED" | "UNCONFIGURED";
  last_success_at: string | null;
  last_attempt_at: string | null;
  latest: ClientImport | null;
  history: ClientImport[];
}
