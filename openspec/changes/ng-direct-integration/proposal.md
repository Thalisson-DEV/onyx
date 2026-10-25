## Why

O maior ganho operacional do TON é encurtar "export manual → upload → análise" para "NG → ingestão →
análise" (contexto 09 §9). Sem dado novo todo dia não existe R1 (varredura diária, §12), "o que
mudou desde ontem" nem acompanhamento real. Em 2026-10-02 a TI da Vale Norte (Celso Passos Soluções
Tecnológicas) começou a liberar VPN até o servidor do NG; foi pedido usuário VPN, endereço do
servidor, SGBD e um usuário **somente leitura** no banco.

## What Changes

- `NgKeevoConnector` somente leitura (banco/view via VPN) que materializa o resultado de uma consulta
  documentada como `SourceSnapshot` imutável e entra no **mesmo** pipeline (perfil → revisão →
  normalização → DRE). Nenhum caminho paralelo.
- Consulta oficial versionada (campos equivalentes ao export "ok": natureza, conta, unidade, data,
  documento, histórico, valores bruto/retenção/líquido/final) e validação de equivalência contra o
  export manual do mesmo período antes de virar fonte primária.
- Agendamento de ingestão (frequência aprovada), frescor da fonte, falha visível, e importação manual
  mantida como fallback.
- Credenciais em armazenamento de segredo criptografado; conexão iniciada pelo host do TON;
  nenhuma escrita, nenhum SQL arbitrário vindo de usuário ou do agente.

## Capabilities

### New Capabilities
- `ng-direct-connector`: ingestão somente leitura do NG/Keevo via banco/view.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- Novo conector em `backend/onyx/ton/sources`, tarefa Celery agendada, Fontes UI, segredos
  (`003a-provider-secret-encryption`), rede do host (VPN no ambiente de produção).

## Dependências

- **Externa:** VPN, endereço, SGBD, usuário read-only, dicionário de dados (Celso/TI). Autorização da
  Luyla para o histórico. Em produção, a rota de rede é do host do TON, não do notebook.

## Estado de dado

Real, após validação de equivalência com o export "ok".

## Atualização da reunião de 2026-10-03

Ata: `plans/ton/ATA_REUNIAO_LUYLA_2026-10-03.md`.

- A TI instalou a VPN num servidor do cliente; teste de acesso do TON com o Celso em 2026-10-03 (~9h).
- A integração resolve na origem as quebras de linha do export (descrições longas) que hoje geram as
  4 linhas rejeitadas e parte dos lançamentos sem unidade.
- A Luyla prefere trazer o histórico de 2025 pela VPN em vez de tratar o export manualmente.
- É pré-requisito do CNPJ do fornecedor (`supplier-nature-consistency`) e da verificação de correção
  frequente (`email-flows`). Prioridade máxima da fase 1.

## Atualização de 2026-10-06 (reunião com o Celso, registrada só agora)

- O NG é da **Keevo** e roda na nuvem da Keevo, em Windows; os usuários entram por **TS Plus**
  (acesso remoto). A Keevo instalou o **Radmin VPN** num servidor Windows da Vale Norte preparado pelo
  Celso (levou ~4 meses por demora do suporte da Keevo).
- O Celso não tem acesso ao banco do NG nem conhece as tabelas, e não aceita abrir porta de entrada.
  Recomendação dele: um **extrator no servidor da Vale Norte**, com usuário somente leitura do banco
  fornecido pela Keevo, rodando à noite e **enviando** os dados ao TON por HTTPS (sem porta aberta).
  O schema do NG muda com frequência (reforma tributária): prever manutenção.
- Em aberto: se o Radmin alcança a porta do banco ou só o TS Plus; credenciais e SGBD da Keevo.

## Atualização da reunião de 2026-10-23

Ata: `plans/ton/ATA_REUNIAO_LUYLA_2026-10-23.md`.

- O **Eric** (contador) criou para o Thalisson um usuário **só de consulta** no NG (o Celso não
  conseguia limitar as permissões) e um acesso Keevo. O acesso à Keevo foi testado com sucesso em
  23/10; falta entender onde/como se acessa o NG (provavelmente o acesso remoto da Keevo, que pede a
  instalação de um componente).
- A **Keevo cobrou R$ 7.500 só para iniciar** uma integração oficial (contato comercial, não técnico).
  A Luyla: "valor muito alto, acredito que não vão aprovar". Rota preferida: a do **Eric**, que diz
  integrar com o NG sem custo. Reunião com o Eric e o desenvolvedor dele a marcar pela Luyla.
- A Luyla disse que "eles têm API", mas não está confirmado: os endpoints que o Thalisson mapeou são da
  documentação do **Zeev**, não do NG.
- O usuário de consulta serve para **explorar e entender como os dados saem** (relatórios,
  exportações, telas), não para automação de tela frágil (RPA) como fonte de produção.
- Prioridade: integração com o NG antes do Zeev.
- A escrita no NG (corrigir no TON e refletir no NG) é tratada à parte, em `ng-write-back`; esta
  change continua só leitura.

## Dependências (revistas em 2026-10-23)

- Reunião com o Eric e o desenvolvedor dele: qual rota usam para ler (API Keevo, banco, relatório).
- Se a rota for o banco: usuário read-only e SGBD vindos da Keevo; extrator no servidor da Vale Norte.
- Se a Vale Norte aceitar a proposta da Keevo: escopo e preço da integração oficial.
