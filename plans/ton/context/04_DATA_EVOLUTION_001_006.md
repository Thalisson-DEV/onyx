# TON — EVOLUÇÃO DATA-001 → DATA-006

Este documento consolida a arquitetura de dados construída até o último estado conhecido.

---

# DATA-001 — Sources Foundation

## Objetivo

Criar uma base de ingestão rastreável e imutável.

Conceitos:

```text
Source
→ ImportRun
→ SourceSnapshot
```

Características:
- identidade da fonte;
- tipo de aquisição;
- raw snapshot imutável;
- hash;
- versão/import time;
- tenant isolation;
- permissions;
- audit;
- source history.

Não criar outro modelo paralelo.

---

# DATA-002 — NG Financial Import

## Objetivo

Transformar export do NG em dados estruturados de forma determinística.

Pipeline:

```text
SourceSnapshot
→ ImportProfileExecution
→ ParsedSourceRecord
+ ParseDiagnostic
```

Características:
- parser determinístico;
- moeda brasileira;
- data/unidade com carry-forward;
- hierarquia/detail;
- lineage;
- fingerprints;
- diagnostics;
- versioned profiles;
- batch persistence;
- partial execution.

## Invariantes importantes

- nova data reseta contexto de unidade;
- data inválida não deve “vazar” contexto antigo;
- não inventar significado de janeiro R:V;
- sheets out-of-scope não devem virar lançamentos;
- hierarquia e detalhe não devem ser confundidos.

## Dados reais validados

Original:
`6.306` registros detalhados.

Revisado:
`6.307`.

Cada execução foi PARTIAL.

Principais diagnósticos:
- 4 rows rejeitadas;
- 19 registros com unidade em branco;
- 25 parent sem child;
- 7 child sem parent;
- 18 células R:V preenchidas em janeiro sem semântica confirmada.

## Diferenças históricas

Abril:
- 1 adição;
- 1 alteração;
- 1 registro inalterado conforme conjunto analisado;
- mudança de data pode decorrer do carry-forward após registro adicionado.

Junho:
- 19 alterações;
- sem add/remove.

Grupos de junho:
- 11 interest + final;
- 5 history;
- 1 unit + retention + net + final;
- 1 interest + penalty + final;
- 1 unit + history + interest + final.

O significado completo desses deltas não pôde ser concluído somente pelo export.

Não existe row ID oficial suficiente para diff perfeito; parte do mecanismo é heurístico.

---

# DATA-003 — NG Financial Review Engine

## Objetivo

Transformar parser em revisão financeira rastreável.

```text
ParsedSourceRecord
+ ParseDiagnostic
→ ReviewRun
→ deterministic rules
→ Finding
→ Evidence
→ Recommendation
→ Human Decision
→ Reviewed Financial Dataset
```

## Regras ativas

- `NGF-SRC-ROW-REJECTED`
- `NGF-UNIT-MISSING`
- `NGF-DUP-EXACT`
- `NGF-ACCT-LABEL-DRIFT`
- `NGF-UNIT-LABEL-DRIFT`

Os três primeiros são blockers.
Drift é non-blocking.

## Dataset dispositions

- ACCEPTED
- JUSTIFIED_EXCEPTION
- REVIEW_REQUIRED
- CORRECTION_REQUIRED
- SUPERSEDED_BY_CORRECTION
- EXCLUDED_SOURCE_ERROR

Somente ACCEPTED e JUSTIFIED_EXCEPTION são downstream-safe.

## Smoke real validado

- 4 rejected rows;
- 19 unit missing;
- 0 duplicates;
- 0 account label drift;
- 0 unit label drift.

Total:
`23 findings`, todos blocking.

Dataset:
- 6.287 ACCEPTED;
- 19 REVIEW_REQUIRED;
- 4 EXCLUDED_SOURCE_ERROR.

## Calibração

Foram observadas:
- 21 deltas históricas;
- nenhuma explicada pelas rules ativas;
- não se pode afirmar que isso prova erro de um lado ou outro.

Conclusão correta:
`TON-only candidates` ou `historical changes requiring cross-source/human context`.

## Segurança

DATA-003:
- não usa LLM para detectar erro;
- não escreve em NG;
- não modifica raw source;
- preserva lineage;
- usa audit;
- preserva tenant isolation.

---

# DATA-004A/B — Billing + Budget

## Billing

Suporte:
- legacy XLS;
- structural profile;
- diagnostics;
- lineage;
- formula/cache handling.

Smoke:
- 20 sheets;
- 1.871 rows inspecionadas;
- 1.258 records;
- 15 rejeitados;
- 1 warning;
- 0 duplicates.
- 18 invoice sheets;
- 2 reference/summary sheets excluídas.

## Budget

Três estruturas principais:
- Juazeiro;
- Itabirito;
- Mossoró.

Smoke:
- 45 budget facts;
- sem rejeição/warning nas estruturas principais.

Não inferir calendário mensal só pela aparência anual.

---

# DATA-004C/D — Canonical Financial Domain

Criou domínio financeiro canônico para:

- reviewed NG actuals;
- billing;
- billing-derived facts;
- budgets;
- accounts;
- business units;
- mappings;
- mapping revisions;
- normalization;
- reconciliation;
- DRE readiness.

## Invariantes

Somente reviewed NG downstream-safe vira actual fact.

Não confundir:
- emission date;
- competence;
- budget period;
- calendar period.

Mappings são versionados/append-only.

Sem mapping exato:
continua unresolved.

## Real smoke

Reprodução anterior:

```text
NG parsed:                 6306
downstream-safe:           6287
review-required:             19
excluded:                     4
account mappings:          5717
unit mappings usable:         0
billing facts:             1258
billing accounts mapped:   1258
billing entities mapped:     21
derived facts:                 0
budget facts:                 45
budget periods unresolved:   45
```

Conciliação:
- matched: 0;
- NG-only: 0;
- billing-only: 0;
- ambiguous: 0;
- unmapped: 1.909.

DRE-ready actual periods:
`0 / 6`.

Um conjunto de ~4.082 actuals mostrou correspondências com chaves legadas úteis, mas o domínio não deve tratar isso como autorização automática de mapping.

---

# DATA-005A/B — DRE Engine

Criou:
- versioned DRE structure;
- line types/hierarchy;
- approved account assignments;
- declarative formulas;
- Decimal arithmetic;
- monthly/YTD;
- READY/NOT_READY;
- immutable result;
- full provenance.

## Invariantes

NOT_READY:
não gera resultado oficial.

Zero budget:
variance % pode ser null.

Zero denominator de fórmula:
bloqueia.

AV/AH/forecast:
não foram ativados sem semântica comprovada.

## Smoke real

Todos os 6 períodos ficaram NOT_READY.

Bloqueios relevantes em junho:
- 6.287 units unmapped;
- 570 accounts unmapped;
- 5.717 accounts sem DRE line aprovada;
- 6.287 amount bases unresolved;
- 1.909 reconciliation items unresolved.

Nenhum mapping foi inventado para tornar a DRE READY.

---

# DATA-006A/B — Financial Readiness

Criou workspace de aprovação humana para:

- unit mapping;
- account mapping;
- amount basis;
- DRE classification;
- budget period;
- reconciliation authority;
- recompute;
- audit;
- versioning.

## Regra

Candidate != Approved.

Candidatos só podem nascer de evidência determinística aceitável.

Nunca:
- fuzzy inference;
- LLM mapping;
- “non-zero means movement/final”;
- annual/12;
- filename date assumption.

## Smoke

Candidatos legados:
- 122 account codes;
- alcance de 5.717 records.

Sem candidate comprovado para:
- unit;
- amount basis;
- DRE line;
- budget period;
- reconciliation authority.

Nenhuma aprovação foi feita em nome de Finance.

0/6 periods READY permanece válido.

---

# DATA-006C/D — DRE Product

Criou experiência para:
- NOT_READY;
- READY synthetic;
- monthly/YTD;
- hierarchy;
- source facts;
- revision;
- CSV export.

Depois foi incorporado à reconstrução do frontend TON.

---

# Regra de arquitetura DATA

O fluxo correto permanece:

```text
source
→ raw immutable
→ parse
→ deterministic review
→ reviewed dataset
→ canonical financial facts
→ mapping/readiness
→ DRE
→ analysis
```

Não atalhar esse caminho no frontend ou no agente.
