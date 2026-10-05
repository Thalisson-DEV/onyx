## 1. Insumos

- [ ] 1.1 Pegar com a Luyla os e-mails do Financeiro e da Controladoria e o formato do relatório que ela envia hoje (reunião 2026-10-06)
- [ ] 1.2 Escolher provedor (Resend ou SMTP) e verificar o domínio remetente por DNS (Vale Norte/TI Celso, ou domínio do Thalisson)
- [x] 1.3 Dia e hora do envio semanal: segunda-feira 08:00 de Brasília (Thalisson, 2026-10-05)

## 2. Read model de inconsistências

- [x] 2.1 Inconsistências abertas (ocorrências da revisão NG) com evidência, competência e semanas em aberto
- [x] 2.2 Estado por importação: corrigida, aberta, reaparecida, por competência, a partir do evento "não detectado nesta importação" (`carry-over-decisions-on-reimport`)
- [x] 2.3 Nunca afirmar correção para competência não coberta; INCONCLUSIVE = "conferir à mão"

## 3. Motor de fluxos

- [x] 3.1 Modelos e migração: fluxo, versão imutável, execução idempotente, entrega
- [x] 3.2 Catálogos em código: gatilhos (com campos), operadores de condição, ações e modelos
- [x] 3.3 Outbox de eventos: emitido ao concluir a revisão NG (alimenta importação, mudanças e contas sem classificação)
- [x] 3.3.1 Emitir `DRE_RECALCULATED` no recálculo da DRE (só READY), agrupado por base de normalização e entregue 3 min após o último cálculo: recalcular o ano gera um e-mail só
- [x] 3.4 Tarefa Beat de agendamento (semanal/diário) e consumidor de eventos
- [x] 3.5 Avaliação condição → ramo → renderização → entrega; execução silenciosa com motivo
- [x] 3.6 Transporte `TON_EMAIL_PROVIDER=resend|smtp` (Resend via httpx, SMTP reaproveitando `email_utils`); `NOT_CONFIGURED` sem provedor; 3 tentativas em falha
- [x] 3.6.1 Uma mensagem por execução com Para/Cc/Cco; lotes acima do limite do provedor, registrados
- [x] 3.7 Prévia do e-mail e "Enviar só para mim"
- [x] 3.8 Auditoria de toda alteração e envio de teste

## 4. Fluxo padrão

- [x] 4.1 Modelo `inconsistency_report` em português, legível no celular, com tabela por unidade
- [x] 4.2 Semear "Inconsistências da semana" como sugestão aguardando destinatários

## 5. Tela e sugestões

- [x] 5.1 API de fluxos (listar, detalhar, criar, versionar, ativar, pausar, cadastrar/descartar sugestão, prévia, teste, histórico)
- [x] 5.2 `/ton/fluxos`: tabela de fluxos + `/ton/fluxos/{id}` com canvas de nós (Gatilho → Condição → Sim/Não → Ação) e Construtor ao lado (referência `exemplo-fluxo.png`)
- [x] 5.3 Sugestões do TON ("Pedir sugestões ao TON"): o assistente escolhe itens do catálogo, validados pelo mesmo `FlowDefinition`; viram "Sugerido pelo TON"

## 6. Validação

- [x] 6.1 Testes (unitários + roteiro ponta a ponta numa cópia do banco local): relatório com itens, vazio, sem provedor, falha do provedor, destinatários agrupados, lotes, corrigida, reaparecida, idempotência, ramo "não", sugestão descartada
- [ ] 6.2 Envio real de teste para o e-mail da Luyla e aprovação do formato
- [ ] 6.3 Atualizar `openspec/roadmap.md` e o design do `routine-framework` (reaproveitar o motor)
