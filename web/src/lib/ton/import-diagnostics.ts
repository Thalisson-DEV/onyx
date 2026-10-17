// Keep backend codes out of the client view. Unknown codes use one safe label.
export const IMPORT_DIAGNOSTIC_KEYS = {
  SHEET_OUT_OF_SCOPE: "sheetOutOfScope",
  MONTH_SHEET_EMPTY: "emptyMonth",
  ACCOUNT_SECTION_REPEATED: "repeatedSection",
  CELL_OUTSIDE_CONTRACT: "extraCell",
  FORMULA_UNSUPPORTED: "formulaUnsupported",
  UNKNOWN_ROW: "unknownRow",
  INVALID_DATE: "invalidDate",
  INHERITED_DATE_INVALID: "invalidDate",
  MISSING_DATE: "missingDate",
  INVALID_AMOUNT: "invalidAmount",
  MISSING_AMOUNTS: "missingAmount",
  MISSING_AMOUNT: "missingAmount",
  UNIT_BLANK: "unitBlank",
  PARENT_ROW_WITHOUT_CHILD_MATCH: "parentWithoutChild",
  CHILD_ROW_WITHOUT_PARENT_MATCH: "childWithoutParent",
  INVALID_COMPETENCE: "invalidCompetence",
  INVALID_INVOICE: "invalidInvoice",
  INVALID_SHARE: "invalidShare",
  MERGED_DETAIL_UNSUPPORTED: "mergedDetail",
  PAYER_BLANK: "payerBlank",
  RETENTION_TOTAL_MISMATCH: "retentionMismatch",
  FORMULA_CACHE_MISSING: "formulaCacheMissing",
  COMPETENCE_YEAR_GAP: "competenceYearGap",
} as const;

// Structure the reader handled on its own: sheets outside January–December,
// summary rows and repeated headers. Shown as notes, never as pending items.
const INFORMATIONAL = new Set<string>([
  "SHEET_OUT_OF_SCOPE",
  "MONTH_SHEET_EMPTY",
  "ACCOUNT_SECTION_REPEATED",
  "PARENT_ROW_WITHOUT_CHILD_MATCH",
  "CHILD_ROW_WITHOUT_PARENT_MATCH",
  "CELL_OUTSIDE_CONTRACT",
]);

export function isInformationalDiagnostic(code: string): boolean {
  return INFORMATIONAL.has(code);
}
