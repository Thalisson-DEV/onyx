## Why

Na reunião de 2026-10-23 a Luyla contou que o Eric (contador) desenvolve um sistema com IA para a
contabilidade e diz que consegue fazer modificações direto no NG. Ela quer o mesmo no TON, como
"atalho e economia de tempo": corrigir no TON e o NG ficar corrigido. O Thalisson confirmou (mesmo
dia) que o TON terá autorização para modificar os dados. A Keevo cobrou R$ 7.500 só para iniciar uma
integração oficial; a Luyla acha que não aprovam e indicou a rota do Eric, sem custo.

Hoje as correções que o TON encontra (natureza errada, lançamento sem unidade, duplicidade, NF 392,
parcelamentos) viram pendência e alguém refaz no NG à mão; o TON só confere na reimportação seguinte
(`carry-over-decisions-on-reimport`, `action-verification`).

O NG é o sistema contábil e fiscal da Vale Norte, integrado à contabilidade, ao fiscal e à folha. Um
erro de escrita vira lançamento errado na contabilidade; uma atualização do NG pode mudar o
comportamento sem aviso. Por isso a escrita só existe com rota comprovada e controles fortes.

Prompt Mestre §12 (autonomia com aprovação), §13 (ledger e verificação), não negociáveis de
`openspec/config.yaml`.

## What Changes

- **Descoberta da rota (sem escrita):** reunião com o Eric e o desenvolvedor dele para entender como
  ele lê e escreve no NG (API da Keevo, banco, automação de tela); exploração com o usuário de
  consulta para entender como os dados saem; parecer escrito sobre risco, manutenção e o que o
  contrato com a Keevo permite.
- **Somente depois de aceite escrito da Vale Norte**, um conector de escrita isolado do de leitura,
  com:
  - escrita só a partir de uma proposta de ação do TON aplicada por uma pessoa com permissão
    (mesmo padrão do `agentic-assistant`);
  - lista fechada de operações permitidas (ex.: trocar natureza, preencher unidade, complementar
    histórico com o número do Zeev), cada uma com validação antes;
  - registro de quem aprovou, valor antes e depois, horário e resposta do NG;
  - leitura de volta no NG depois de cada escrita para confirmar o resultado; divergência vira
    ocorrência crítica;
  - chave para desligar a escrita sem afetar a leitura;
  - primeiros testes numa empresa ou base de teste do NG, se existir;
  - permissão de escrita pedida abertamente à Vale Norte (o usuário atual é só de consulta).
- Manutenção da rota não oficial prevista em contrato (quebra quando o NG muda).

## Capabilities

### New Capabilities
- `ng-write-back`: escrita controlada no NG a partir de propostas aprovadas, com verificação e desligamento.

### Modified Capabilities
<!-- `ng-direct-integration` continua só leitura -->

## Impact

- Novo conector em `backend/onyx/ton/sources` (ou módulo próprio), extensão das propostas de ação
  (`onyx/db/ton/agent_actions.py`), auditoria, ledger (verificação), configuração por ambiente.

## Dependências

- Reunião com o Eric e o desenvolvedor dele (Luyla vai marcar).
- Autorização escrita da Vale Norte (Luyla ou gestor) e verificação do contrato com a Keevo.
- Usuário com permissão de escrita no NG, concedido pela Vale Norte.
- Ambiente ou empresa de teste no NG (a confirmar).

## Estado de dado

Real, só após aceite; antes disso, apenas descoberta e documentação.
