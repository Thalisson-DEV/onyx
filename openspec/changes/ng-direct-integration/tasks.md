## 1. Acesso (externo)

- [ ] 1.1 Receber da TI: usuário VPN, endereço, SGBD, usuário read-only, dicionário/views
- [ ] 1.2 Testar conectividade do host de desenvolvimento e documentar requisitos de rede de produção
- [x] 1.3 Acesso Keevo do usuário de consulta testado (2026-10-23)
- [ ] 1.4 Entrar no NG com o usuário de consulta (aguarda orientação de instalação) e documentar relatórios/exportações disponíveis, sem automação
- [ ] 1.5 Reunião com o Eric e o desenvolvedor dele; registrar a rota de leitura que usam
- [ ] 1.6 Decidir a rota (Eric × Keevo oficial R$ 7.500 × extrator no servidor) com a Luyla e registrar em `design.md`

## 2. Conector

- [ ] 2.1 Interface de conector + driver do SGBD informado; segredo criptografado
- [ ] 2.2 Consulta oficial versionada por competência (sem dados no repositório)
- [ ] 2.3 Snapshot canônico (ordenado + hash) e perfil `ng-db-financial.v1`
- [ ] 2.4 Bloqueio de qualquer instrução fora das consultas registradas + auditoria

## 3. Operação

- [ ] 3.1 Tarefa Celery agendada (frequência aprovada), retry com backoff, estados de falha
- [ ] 3.2 Fontes UI: última ingestão, próxima execução, falhas, modo sombra × primária
- [ ] 3.3 Relatório de equivalência banco × export "ok" para um período fechado

## 4. Validação

- [ ] 4.1 Testes com banco descartável (fixture sintética no schema real)
- [ ] 4.2 Equivalência real jun/2026 e aceite da Luyla
- [ ] 4.3 Atualizar contexto 08 e `openspec/roadmap.md`
