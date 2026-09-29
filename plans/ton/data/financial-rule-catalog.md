# Financial review rule catalog

The canonical catalog is `backend/onyx/ton/financial_review/catalog.py`. `GET /api/ton/financial-review/rules` returns it. Every entry is version 1 and runs on the NG financial export (`ng_financial_export` v1). Engine status controls evaluation; `RuleVersion.status` controls publication.

## Active

Active rules create findings. All are deterministic.

| Rule | POP | Type | Blocking | Recommendation | Evidence | Known limitation |
| --- | --- | --- | --- | --- | --- | --- |
| NGF-SRC-ROW-REJECTED | 08 | DETERMINISTIC | yes | SOURCE_CORRECTION_REQUIRED, HIGH_EVIDENCE | parse diagnostic and locator | location-only identity; origin unresolved |
| NGF-UNIT-MISSING | 08 (04) | DETERMINISTIC | yes | SOURCE_CORRECTION_REQUIRED, no value | parsed record | no unit inference; correspondence needs all other fields unchanged |
| NGF-DUP-EXACT | 01 (06) | DETERMINISTIC | yes | REQUEST_JUSTIFICATION, AMBIGUOUS | every member record | equal content is not proof; cross-month not evaluated |
| NGF-ACCT-LABEL-DRIFT | 03 | DETERMINISTIC | no | REVIEW_CLASSIFICATION, AMBIGUOUS; DETERMINISTIC_CORRECTION only with a mapping | one record per month and label | a rename inside the period is legitimate; no mapping configured |
| NGF-UNIT-LABEL-DRIFT | 04 | DETERMINISTIC | no | REQUEST_INFORMATION, AMBIGUOUS | one record per month and label | only units written as "code - label" |

## Experimental

Experimental rules run and store counts in the review run. They create no finding and block nothing.

| Rule | POP | Observes | Why not active |
| --- | --- | --- | --- |
| NGF-HIER-RECONCILIATION | technical | parent and child reconciliation differences per sheet | parent-block semantics unproven |
| NGF-DUP-NEAR | 06 (01) | same account, date, document and amounts, different history or unit | split launches are legitimate |
| NGF-DATE-EMISSION-AFTER-SHEET | 02 | emission month later than the sheet month | sheet has no year; sheet-month meaning unconfirmed |
| NGF-AMT-FINAL-ABSENT | 08 | non-zero movement with zero or blank final amount | retentions settled at invoicing can zero the final amount |
| NGF-DOC-MISSING | 13 | records without a document number | some launch types have no document |

## Blocked

Blocked rules are registered and recorded as `SKIPPED_MISSING_DATA` in every run.

| Rule | POP | Type | Required source |
| --- | --- | --- | --- |
| NGF-HIST-RECURRING-OMISSION | 05 | STATISTICAL | financial history (2025 onwards) |
| NGF-HIST-ATYPICAL-VALUE | 07 | STATISTICAL | financial history; median/MAD, IQR, rolling baselines by unit, nature, account |
| NGF-XS-DOTACAO-OVERRUN | not in POP | CROSS_SOURCE | normalised dotação |
| NGF-XS-APPROVAL-MISSING | 09 | CROSS_SOURCE | approval workflow (Zeev); SLA rules stay outside |
| NGF-XS-SUPPORT-DOC | 13 | CROSS_SOURCE | invoice or receipt source |
| NGF-XS-PAYROLL-DUP | 10 | CROSS_SOURCE | NG Folha |
| NGF-XS-UNRECORDED-LOSS | 11 | CROSS_SOURCE | human context |
| NGF-XS-FIN-VS-ACCOUNTING | 12 | CROSS_SOURCE | accounting ledger |
| NGF-XS-REVENUE-CLASSIFICATION | 14 | CROSS_SOURCE | billing and accounting ledger |
| NGF-XS-PAYMENT-DUP-BANK | 06 | CROSS_SOURCE | detailed bank statements |
| NGF-XS-COMPETENCE | 02 | CROSS_SOURCE | service competence in documents |
| NGF-XS-CLASSIFICATION-NATURE | 03 | CROSS_SOURCE | approved account-to-nature mapping |
| NGF-AMT-COMPOSITION | technical | DETERMINISTIC | Finance confirmation of the F:Q formula and signs |

## POP capability matrix

| POP | Category | Status | Rules |
| --- | --- | --- | --- |
| 01 | Lançamento Duplicado | PARTIAL | NGF-DUP-EXACT; NGF-DUP-NEAR (experimental) |
| 02 | Competência Incorreta | REQUIRES_DOCUMENT_SOURCE | NGF-DATE-EMISSION-AFTER-SHEET (experimental); NGF-XS-COMPETENCE |
| 03 | Classificação Contábil/Gerencial Incorreta | PARTIAL | NGF-ACCT-LABEL-DRIFT; NGF-XS-CLASSIFICATION-NATURE |
| 04 | Centro de Custo ou Unidade Incorreta | PARTIAL | NGF-UNIT-MISSING; NGF-UNIT-LABEL-DRIFT |
| 05 | Omissão de Despesas Recorrentes | REQUIRES_HISTORY | NGF-HIST-RECURRING-OMISSION |
| 06 | Pagamento em Duplicidade | PARTIAL | NGF-DUP-EXACT; NGF-XS-PAYMENT-DUP-BANK |
| 07 | Valores Atípicos ou Fora do Padrão | REQUIRES_HISTORY | NGF-HIST-ATYPICAL-VALUE |
| 08 | Informações Incompletas ou Ausentes | IMPLEMENTABLE_NOW | NGF-SRC-ROW-REJECTED; NGF-UNIT-MISSING |
| 09 | Despesas sem Formalização ou Aprovação | REQUIRES_ZEEV | NGF-XS-APPROVAL-MISSING |
| 10 | Folha de Pagamento com Risco de Duplicidade | REQUIRES_PAYROLL | NGF-XS-PAYROLL-DUP |
| 11 | Ocorrências, Sinistros e Perdas Não Registrados | REQUIRES_HUMAN_CONTEXT | NGF-XS-UNRECORDED-LOSS |
| 12 | Divergência entre Financeiro e Contábil | REQUIRES_ACCOUNTING_SOURCE | NGF-XS-FIN-VS-ACCOUNTING |
| 13 | Documentação de Suporte Ausente | REQUIRES_DOCUMENT_SOURCE | NGF-XS-SUPPORT-DOC; NGF-DOC-MISSING (experimental) |
| 14 | Receitas Não Registradas ou Classificadas Incorretamente | REQUIRES_ACCOUNTING_SOURCE | NGF-XS-REVENUE-CLASSIFICATION |

## Sources that unlock blocked rules

Normalised financial history, dotação, approval workflow, invoices and receipts, accounting ledger, billing, bank statements, NG Folha, an approved chart-of-accounts mapping, a unit or contract master, and Finance confirmation of the F:Q composition.
