## Context

`Contract` foi propositalmente mínimo (readiness §15): campos entram quando uma regra precisa. Agora o
cadastro mestre é pré-condição para S1–S3, S7, T13–T20, T24, T25, T27, T28, margem prevista × real e
ISC. A Vale Norte tem ~7 contratos operacionais e alguns em implantação — volume pequeno, alto valor.

## Goals / Non-Goals

**Goals:** estrutura completa do §4, versionada, com evidência por campo; valor vigente derivado de
eventos; completude computável; vínculo com unidade e tomador.

**Non-Goals:** extração automática de PDF por LLM como fonte de verdade (pode sugerir, humano
confirma); gestão documental completa (o arquivo fica no file store como snapshot).

## Decisions

- **Snapshot de cadastro + eventos.** `ContractMasterVersion` (blocos como colunas tipadas/JSON
  validado por schema Pydantic) append-only; `ContractEvent` (aditivo, apostilamento, reajuste,
  repactuação, prorrogação) com valores e documento. Valor mensal vigente = original + eventos
  aplicados até a data. Alternativa rejeitada: editar colunas in-place (perde histórico).
- **Evidência por campo**: cada campo preenchido referencia documento (snapshot) e nível A/B/C/D.
- **Completude por bloco** definida pelas regras que dependem dele (ex.: T19 exige vigência; S2 exige
  valor mensal e prazo); a análise de cada regra consulta a completude do que precisa.
- **Sugestão assistida por LLM opcional**: o assistente pode ler o PDF e propor valores, marcados
  "proposto — confirmar"; só confirmação humana grava no cadastro.
- **Vínculos** contrato ↔ `BusinessUnit` e contrato ↔ tomador (texto do faturamento) como mapeamentos
  versionados, mesmo padrão do domínio financeiro.

## Risks / Trade-offs

- [Cadastro trabalhoso] → começar por Mossoró 02/2023 (caso-padrão do §4.1) e importar o backlog para
  pré-preencher identificação/valores como nível C, a confirmar.
- [Unidade com mais de um contrato] → DRE por contrato exige rateio aprovado; até lá margem por
  contrato só onde unidade = contrato.

## Open Questions

- Quais contratos têm documentação digital acessível? Quem é o gestor nominal de cada um?
