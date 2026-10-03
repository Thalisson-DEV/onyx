## 1. Insumos

- [ ] 1.1 Pegar com a Luyla os e-mails do Financeiro e da Controladoria e o formato do relatório que ela envia hoje
- [ ] 1.2 Configurar SMTP no ambiente

## 2. Relatório

- [ ] 2.1 Read model das inconsistências abertas (ocorrências da revisão NG) com evidência e semanas em aberto
- [ ] 2.2 Modelo de e-mail em português, legível no celular, com tabela por unidade
- [ ] 2.3 Rotina agendada (semanal por padrão) com idempotência e registro de execução

## 3. Verificação

- [ ] 3.1 A cada importação/extração do NG: corrigida, aberta ou reaparecida, por competência
- [ ] 3.2 Usar o evento "não detectado nesta importação" (`carry-over-decisions-on-reimport`)

## 4. Administração

- [ ] 4.1 Tela: regras incluídas, frequência, destinatários, histórico de envios e falhas
- [ ] 4.2 Auditoria de cada alteração

## 5. Validação

- [ ] 5.1 Testes: relatório com itens, vazio, falha de SMTP, corrigida, reaparecida
- [ ] 5.2 Envio real de teste para o e-mail da Luyla e aprovação do formato
- [ ] 5.3 Atualizar `openspec/roadmap.md`
