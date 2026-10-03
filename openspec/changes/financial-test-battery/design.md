## Context

`Rule`/`RuleVersion` já suportam parâmetros versionados, componentes de identidade e domínio dono;
`record_detection__no_commit` deduplica e versiona ocorrências. As regras NGF rodam por revisão de
snapshot; T1–T12 rodam por **competência** sobre fatos canônicos (pós-revisão) — outra granularidade.

## Goals / Non-Goals

**Goals:** testes por competência e unidade, parâmetros aprovados, ocorrência única por identidade,
evidência navegável.

**Non-Goals:** detecção estatística/ML; limiares inventados; T12 (folha) nesta change.

## Decisions

- **Testes sobre fatos canônicos** (`FinancialActualFact`, `FinancialBillingFact`), não sobre linhas
  brutas, para respeitar o dataset revisado; evidência aponta para o registro de origem.
- **Identidade por teste:** ex. T2 = (teste, unidade, grupo, competência); T3 = (teste, documento
  normalizado, valor, fornecedor); T10 = (teste, fato). Reexecução da mesma competência repete a
  ocorrência em vez de duplicar.
- **Parâmetros como `RuleVersion.parameters`**, com o padrão do Prompt Mestre e aprovação registrada;
  mudar limiar = nova versão (supersede forçado, já suportado).
- **Relação NGF × T3:** NGF-DUP-* continua bloqueando a revisão da importação; T3 cobre o cruzamento
  entre unidades e meses. Um mesmo par de registros não gera duas ocorrências (handoff §15).

## Risks / Trade-offs

- [T2 dispara demais em unidades pequenas] → régua de criticidade por % da receita filtra; teto 7/12.
- [T10 com despesa total do mês ≈ 0] → não avaliado, com motivo.

## Open Questions

- O export do NG traz CNPJ/endereço do fornecedor (T8)? Qual campo identifica "pagamento" × "provisão" (T7)?
