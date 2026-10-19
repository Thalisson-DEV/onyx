import type { ClientSource } from "@/lib/ton/types";

// The DRE needs the NG export and billing; the budget and the installment
// table are optional.
const OPTIONAL_SOURCES = new Set(["budget", "installments"]);

export interface SourcesSummary {
  /** Sources the closing needs that the user can import. */
  required: ClientSource[];
  /** Required sources with at least one successful import. */
  imported: ClientSource[];
  /** Imported sources whose latest file had rejected rows or failed. */
  attention: ClientSource[];
  latest: string | undefined;
  /** Every required source imported and none needing attention. */
  healthy: boolean;
}

export function summarizeSources(sources: ClientSource[]): SourcesSummary {
  const required = sources.filter(
    (source) => source.source_id && !OPTIONAL_SOURCES.has(source.key)
  );
  const imported = required.filter((source) => !!source.last_success_at);
  const attention = sources.filter(
    (source) => source.status === "ATTENTION" || source.status === "FAILED"
  );
  const latest = sources
    .map((source) => source.last_success_at)
    .filter((value): value is string => !!value)
    .sort()
    .at(-1);
  return {
    required,
    imported,
    attention,
    latest,
    healthy:
      required.length > 0 &&
      imported.length === required.length &&
      attention.length === 0,
  };
}
