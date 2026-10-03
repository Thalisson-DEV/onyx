## Why

"Sem ledger de ocorrências não existe acompanhamento, reincidência, escalonamento nem ROI" (Prompt
Mestre, camada 5; §13.1). O TON já tem o modelo completo (`ton_occurrence`, eventos, impactos,
atribuições, notas, domínios impactados), mas nenhuma superfície para operar o ledger: não dá para
atribuir responsável nominal, definir prazo, mudar status, acompanhar ciclos em aberto ou exportar.
Por isso a fila de trabalho nunca mostra dono nem prazo, `actions/overdue` é sempre vazio, e o passo
"Acompanha" do loop (guia de apresentação §9) não existe.

## What Changes

- Tela **Ocorrências** (ledger) com os campos do §13.1: ID, data de detecção, teste, NC,
  contrato/unidade, descrição, evidência (fonte + nível), impacto R$, confiança, criticidade, causa
  provável, ação recomendada, responsável nominal, prazo, status, ciclos em aberto, resolução,
  critério de verificação e resultado da verificação; filtros e exportação Excel.
- API de operação: atribuir responsável (usuário ou cargo nominal), prazo (padrão da régua),
  transições de status, notas, causa provável (rotulada como hipótese), ação recomendada.
- Regras de autonomia do §12.1: encerrar ocorrência 🔴 exige decisão humana; o TON registra, não
  encerra.
- Contador de ciclos em aberto atualizado a cada fechamento (insumo do escalonamento).
- Fila de trabalho e notificações passam a mostrar dono e prazo reais.

## Capabilities

### New Capabilities
<!-- nenhuma -->

### Modified Capabilities
- `occurrence-ledger`: operação do ledger pela UI/API (atribuição, prazo, status, ciclos, exportação).

## Impact

- `backend/onyx/db/ton/{occurrences,occurrence_records,acl}.py`, novos endpoints em
  `backend/onyx/server/ton/`, nova view `web/src/views/ton/OccurrencesPage`, fila de trabalho.

## Dependências

- Definição de responsáveis por tipo de pendência (Luyla). `criticality-and-nc-catalog` para prazos.

## Estado de dado

Real (ocorrências da revisão NG jan–jun/2026 e das novas baterias).
