## Why

O Prompt Mestre §6 diz que a aritmética de sanidade é "a diferença entre um agente que corrige a
Controladoria e um que repete o erro com autoridade": as bases reais da Vale Norte falham nela hoje
(margens de 187% e 1.020% no backlog, saldo maior que o valor do contrato, receita trocada entre
Mossoró, Itabirito e Sento Sé, parcelamento de R$ 90,89 mi num único mês). Das dez regras S1–S10, só
S10 está operacional. As regras que dependem só da base financeira (S4, S5, S6, S8) podem rodar já
sobre o NG/DRE real; S1, S2, S3 e S7 dependem do backlog/cadastro (change `backlog-import-and-sanity`)
e S9 da produção (change `production-domain`).

## What Changes

- Executores determinísticos versionados para **S4** (soma das linhas = subtotal declarado, ±0,5%,
  para fontes com subtotal), **S5** (Σ unidades = consolidado ao centavo), **S6** (sinal por natureza:
  receita ≥ 0, despesa ≤ 0 — NC-03) e **S8** (AV% sobre a receita bruta da própria unidade).
- Framework comum de sanidade para que S1–S3, S7 e S9 se pluguem nas changes que trazem os dados.
- Sanidade roda no passo 2 do protocolo; violação crítica bloqueia publicação de margem (S10).
- Achados de calibração do §6.2 transformados em casos de teste (fixtures sintéticas que reproduzem
  o padrão, sem valores reais no repositório).

## Capabilities

### New Capabilities
- `sanity-battery`: regras S1–S10 como executores determinísticos no passo 2.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- Novo módulo de regras sob `backend/onyx/ton/` registrado em `Rule`/`RuleVersion`; cobertura em
  `onyx/ton/agent/capabilities.py`; protocolo de execução.

## Dependências

- `execution-protocol` (passo 2). Sinal esperado por natureza: decisão da Controladoria sobre o plano
  gerencial (§3.2) — candidatos a partir do grupo DRE.

## Estado de dado

Real para S4/S5/S6/S8 (jan–jun/2026).
