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
