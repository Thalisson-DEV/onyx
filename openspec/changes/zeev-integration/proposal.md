## Why

A Luyla usa o Zeev para processos, SLA e produtividade (contexto 03 §1), e boa parte do controle
financeiro da Vale Norte passa por ele: pedidos e liberações financeiras (fluxos 108, 130, 154, 148),
aprovações da Controladoria (121, CCP 123), solicitação de pagamento (119), envio de contas a pagar
(141), análise jurídica de contratos (136), certidões (126), desligamento de funcionários (120),
manutenção (139), recrutamento (107). Isso alimenta várias exigências do Prompt Mestre que nenhuma
outra fonte cobre: o ponto cego "processo sem rastreabilidade — decidido por WhatsApp, aprovado sem
registro" (§11), pagamento sem aprovação (regra catalogada `NGF-XS-APPROVAL-MISSING`), evidência de
contrato assinado para o cadastro mestre (§4), rescisões para o T12, manutenção para o T23, certidões
para a matriz de compliance, e SLA/produtividade da própria Controladoria.

O adaptador somente leitura (BE-004A) e o catálogo (BE-004B: 35 fluxos, 916 campos, 401 elementos de
desenho, zero mutações) **já existem no código**. Falta o passo BE-004C: sincronizar os fluxos
escolhidos para dentro do pipeline do TON e usá-los nas regras.

## What Changes

- **Escopo de sincronização** decidido com a Luyla a partir do catálogo (quais flow IDs são vigentes;
  cópias, testes e standby excluídos ou mantidos como histórico) e registrado como configuração
  versionada.
- **Sincronização** dos fluxos escolhidos: instâncias, valores de formulário e tarefas (com tempos,
  executor, resultado e SLA) por janela de datas, materializadas como `SourceSnapshot` imutável e
  canônico, com checkpoint, backfill histórico definido e validação de que a janela captura as
  atualizações (o contrato da API não garante isso).
- **Perfis por fluxo** que mapeiam campos do formulário para fatos de processo do TON (ex.: pedido de
  liberação financeira: fornecedor, CNPJ, valor, vencimento, NF, unidade, aprovadores e datas),
  mapeamento campo → fato aprovado por humano, nunca por similaridade.
- **Usos no TON:** fatos de aprovação para cruzar pagamento NG × liberação aprovada no Zeev;
  SLA/tempo de ciclo por fluxo e etapa; referência de documento (contrato assinado, certidão) como
  evidência; desligamentos para o T12; manutenção para frota.
- Dados pessoais (solicitante, executor) mascarados por padrão; anexos continuam só como referência
  até existir rota de leitura autorizada.
- Fonte "Zeev" no Fontes UI com escopo, última sincronização, falhas e estado de validação.

## Capabilities

### New Capabilities
- `zeev-source`: sincronização dos fluxos Zeev escolhidos para o pipeline de fontes e fatos de processo.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- `backend/onyx/ton/zeev/*` (reutiliza `ZeevClient`, `ZeevCatalogService`), `backend/onyx/ton/sources`,
  nova tarefa Celery de sincronização, fatos de processo no domínio, Fontes UI, cobertura
  (`SOURCE_ZEEV`), regras que consomem aprovação/SLA.

## Dependências

- Respostas da Luyla às 8 perguntas do catálogo (`plans/ton/integrations/zeev-source-catalog.md`):
  fluxos vigentes da Controladoria, diferença entre variantes CCP/NÚCLEO/NVC/VALE NORTE, fluxo de
  fechamento mensal, status de 141/147, origem dos arquivos que chegam em Excel/PDF, local dos
  contratos assinados, tratamento de cópias/testes, dados de responsável necessários.
- Credencial de serviço dedicada (de preferência somente leitura) para produção.
- Consumidores: `financial-test-battery` (aprovação × pagamento), `execution-protocol` (ponto cego),
  `contract-master-registry`, `hr-payroll-domain` (T12), `fleet-fuel-domain` (T23),
  `compliance-regulatory-domain`.

## Estado de dado

Real (tenant da Vale Norte), com mascaramento de dados pessoais.

## Atualização da reunião de 2026-10-23

Ata: `plans/ton/ATA_REUNIAO_LUYLA_2026-10-23.md`. A Luyla mostrou o Zeev ao vivo.

- **Prioridade:** NG primeiro; o Zeev vem depois.
- **Para que a Controladoria usa o Zeev hoje:**
  - conferir parcelamentos: quantas parcelas e o valor de cada uma, quando o NG só tem o valor total
    (às vezes os valores não batem 100% com o NG);
  - consultar NF, boleto e **data de pagamento** (o financeiro não alimenta 100%). Pode ser fonte de
    data de pagamento para a DRE de caixa, junto com o extrato bancário.
- **Indicadores que a Eloía hoje leva do Zeev ao Power BI:** solicitações com vencimento em menos de 5
  dias úteis (monitoramento e notificação), volume de solicitações por pessoa, tarefas pendentes e
  atrasadas por colaborador (cores: verde no prazo, amarelo vence hoje, vermelho vencido). A Luyla
  quer notificar automaticamente o solicitante com as regras financeiras quando o prazo não for
  cumprido. Indicadores a receber da Eloía.
- **Estrutura do Zeev:** apps (BPM) criados pela Luyla, Luciana e Eloía, por empresa do grupo (MC3,
  Vale Norte, NVC, Núcleo, CCP); "executar tarefas", "acompanhar solicitações" (a Controladoria vê as
  de todos), chamados de TI (com triagem e autorização do gestor), regras de negócio e integrações
  (a lista de unidades é atualizada à mão em cada app quando entra uma unidade nova).
- **Chave com o NG:** a ata de 20/10 pede ao financeiro para colocar o número da solicitação do Zeev
  no histórico do lançamento do NG (ex.: "Det. #2318"). Isso vira chave de ligação NG × Zeev.
- **API:** o Thalisson já mapeou os endpoints a partir da documentação do Zeev (a Eloía mandou); a
  documentação é boa. O adaptador e o catálogo já existem no código.
- **Futuro (Luyla):** levar o BPM do Zeev para dentro do TON e deixar de pagar o Zeev; chamados também
  entram no TON. Fica em `platform-ces-foundation`; esta change continua sendo leitura.
- Contas a pagar das unidades: parte já vai pelo Zeev (solicitação de pagamento, reembolso), parte por
  planilha. **Decidido em 2026-10-24:** o TON lê a solicitação de pagamento do Zeev e concilia com o
  título de `unit-payables-intake`. Isso exige uma integração robusta: sincronização confiável e
  frequente desses fluxos, frescor visível, re-leitura de instâncias ativas e alerta de falha.
- O Zeev da Vale Norte é o tenant **"Núcleo Controller"** (`nucleo.zeev.it`); o Thalisson tem acesso
  desde 2026-10-23.

## Dependências (acrescentadas em 2026-10-23)

- Indicadores e regras de notificação que a Eloía usa no Power BI.
- Adoção pelo financeiro do número do Zeev no histórico do NG (ata 20/10).
