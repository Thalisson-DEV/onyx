## Context

A arquitetura DATA-001 prevê `connector → source adapter → Source → Snapshot → parser/profile →
pipeline`. O parser atual lê o layout do export Excel. O SGBD do NG ainda é desconhecido. O export
"ok" é uma versão **revisada** pela Controladoria; o banco tem o dado bruto — os números podem
diferir legitimamente (o TON já trata a revisão humana como calibração, não verdade — decisão 07 §4).

## Goals / Non-Goals

**Goals:** leitura direta reprodutível; snapshot imutável do resultado; mesmo pipeline; equivalência
demonstrada; fallback manual.

**Non-Goals:** escrita no NG; CDC/tempo real na primeira versão; consultas ad hoc do agente ao NG.

## Decisions

- **Snapshot do resultado da consulta** (Parquet ou JSONL canônico ordenado + hash), não leitura ao
  vivo pelas regras. Mantém imutabilidade e reprocessamento.
- **Perfil próprio `ng-db-financial.v1`** que produz o mesmo `ParsedSourceRecord` do perfil de
  export; diferenças de semântica (bruto × "ok") ficam explícitas no perfil.
- **Consulta versionada no repositório** (sem dados), parametrizada por competência; o conector só
  executa consultas registradas.
- **Equivalência:** para um período, comparar contagem, somas por natureza/unidade e chaves de
  documento entre snapshot do banco e export "ok"; divergências viram relatório para a Controladoria
  explicar antes de trocar a fonte primária.
- **Driver** escolhido pelo SGBD informado (ex.: `pyodbc` para SQL Server, `psycopg` para
  PostgreSQL, `oracledb` para Oracle), isolado atrás de uma interface.

## Risks / Trade-offs

- [Banco bruto ≠ export revisado] → manter ambos; regras de revisão e tratamentos cobrem a diferença.
- [VPN instável] → retry com backoff, estado "falha de conexão" visível, fallback manual.
- [Credencial exposta] → segredo criptografado, nunca em log; usuário só leitura com escopo mínimo.

## Migration Plan

Fase 1 em paralelo ao upload manual (sombra); fase 2 vira fonte primária após aceite da Luyla.
Rollback: desativar o agendamento.

## Open Questions

- SGBD, schema e views disponíveis; existe view "lançamentos financeiros" equivalente ao export?
- Frequência desejada (diária às 05h para alimentar R1 às 06h?).
