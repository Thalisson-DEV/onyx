## Why

O Prompt Mestre §3 exige um **contrato de dados**: o TON só conclui sobre fonte que atende ao esquema
mínimo de cada base canônica (lançamentos, cadastro mestre, dotação, backlog, frota, abastecimento,
produção, pessoal, medição/faturamento); fonte fora do esquema é lida, mas todo número dela sai
rotulado **[fonte não padronizada]**. §3.4 exige que todo número publicado carregue seu **nível de
confiança** A (documental), B (sistema), C (registro operacional) ou D (declaratória), e que conclusão
dependente de D abra com "Hipótese — necessita validação". Hoje as fontes têm perfis de leitura, mas
não há registro de esquema mínimo por base, nem nível de evidência propagado até relatório, DRE ou
resposta do assistente.

## What Changes

- Registro versionado das **bases canônicas** (§3.1) com campos mínimos e chave de cada uma.
- Verificação de conformidade de cada perfil/fonte contra a base canônica que alimenta; resultado
  persistido no snapshot (conforme / não padronizada, com campos faltantes).
- **Nível de evidência** (A/B/C/D) atribuído por tipo de fonte e propagado para fatos, achados,
  impactos, linhas de relatório e respostas do assistente.
- Rótulos obrigatórios: "[fonte não padronizada]" e "Hipótese — necessita validação"; nível D nunca
  vira A por repetição.

## Capabilities

### New Capabilities
- `data-contract`: bases canônicas, conformidade de fontes e níveis de confiança A–D.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- `backend/onyx/ton/sources`, perfis de importação, `FindingEvidence`, `OccurrenceImpact`, relatórios,
  ferramentas do assistente, componentes de evidência no frontend.

## Dependências

- Nenhuma externa para NG, faturamento e dotação. Novas bases (frota, produção…) nascem conformes a
  este registro nas changes de domínio.

## Estado de dado

Real para as três fontes atuais.
