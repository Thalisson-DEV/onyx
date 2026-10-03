## Why

"Sem valor, não há prioridade — e sem prioridade, o relatório vira lista" (Prompt Mestre §5, passo 5).
O §9 define o método: impacto = diferença operacional × custo unitário de referência, com a ordem de
preferência do custo (1. composição da dotação do próprio contrato; 2. realizado médio dos últimos 3
meses da unidade; 3. mediana das unidades comparáveis), sete categorias (economia potencial, perda
evitada, receita recuperável, receita não faturada, custo excedente, risco financeiro, oportunidade de
margem), grau de confiança Alta/Média/Baixa e o rótulo obrigatório "Estimativa — premissa: [x];
sensibilidade: ±[y]%". `OccurrenceImpact` já modela categoria, confiança, método e fonte do custo
unitário, mas nada calcula impacto hoje: todos os achados saem "não quantificado".

## What Changes

- Serviço de quantificação determinístico por tipo de ocorrência (cada regra declara como calcula a
  diferença operacional e qual custo unitário usa).
- Seleção do custo unitário na ordem do §9, registrando qual foi usado.
- Confiança derivada dos níveis de evidência (A/B completo = Alta; B/C com uma premissa = Média;
  duas ou mais premissas = Baixa).
- Rótulo de estimativa com premissa e sensibilidade; impacto Baixa nunca entra em meta nem ROI.
- Impactos diretos (valor monetário já é a diferença, ex.: duplicidade, receita não faturada) sem
  custo unitário.

## Capabilities

### New Capabilities
- `impact-quantification`: método §9, categorias, confiança e rótulo de estimativa.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- `backend/onyx/db/ton/occurrence_records.py` (`record_impact__no_commit`), regras S/T, relatórios,
  Dinheiro Escondido, régua de criticidade.

## Dependências

- `data-contract-and-trust-levels` (níveis). Custo de dotação depende de `dotacao-composition-import`;
  até lá a ordem cai para o realizado da unidade.

## Estado de dado

Real.
