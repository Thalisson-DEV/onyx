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
  output: ClosingOutput;
  steps: {
    specialist: string;
    code: string;
    status: string;
    reason?: string;
  }[];
}

export interface Routine {
  key: string;
  name: string;
  status: string;
  reason: string;
  schedule: string;
  manual_available: boolean;
}
