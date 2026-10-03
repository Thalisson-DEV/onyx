## Why

Tudo roda hoje num ambiente de validação no notebook do desenvolvedor (Docker em WSL com 6 GB), com
acesso só dele, imagens reconstruídas à mão e backups manuais. A equipe da Luyla não consegue usar o
TON no dia a dia, e a integração com o NG exige que o **host do TON** tenha rota pela VPN da Vale Norte.
As decisões abertas do decision-log (papéis de acesso, retenção) e o plano `007-deployment-hardening`
ainda não foram executados.

## What Changes

- Ambiente de produção (cloud ou servidor do cliente) com topologia definida, TLS, domínio, rota de
  rede à VPN do NG, SMTP.
- Build de imagens a partir do repositório (pipeline), migrações controladas, sem `docker cp` nem
  `docker compose pull` das imagens próprias.
- Backups automáticos do Postgres e do file store com teste de restauração; monitoramento e alertas.
- Papéis de acesso (admin / controladoria / gestor / leitura) com escopo por unidade/contrato, usuários
  da equipe da Luyla, política de retenção (fontes, evidências, relatórios, dados pessoais — LGPD).
- Segredos (provider LLM, conector NG, SMTP) em armazenamento criptografado.

## Capabilities

### New Capabilities
- `production-deployment`: ambiente de produção, operação, acesso e retenção.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- `deployment/`, pipeline de build, `plans/ton/backend/007-deployment-hardening.md`, configuração de
  RBAC/grupos, documentação de operação.

## Dependências

- Escolha de hospedagem e orçamento (Vale Norte), acesso de rede à VPN a partir do host, definição de
  usuários e papéis pela Luyla, aprovação da política de retenção.

## Estado de dado

Real.
