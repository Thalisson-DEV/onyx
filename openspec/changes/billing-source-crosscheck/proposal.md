## Why

Na reunião de 2026-10-23 a Luyla explicou que o faturamento tem três fontes: o NG (receita
registrada), a planilha do financeiro (feita à mão, hoje a fonte oficial do TON) e o extrato de notas
da prefeitura (sistema de NFS-e), que é o mais confiável ("não tem como errar"). A Controladoria já
confronta pela prefeitura e achou erros na planilha (ata de 20/10: NF 512 com data de emissão errada,
NF 535 cancelada contando valor, NF 446 com INSS de R$ 91.866,19 que deveria ser zero, ISS com
diferença de centavos nas NFs 542 e 545, coluna de competência a revisar; ata de 16/10: faturamento de
Juazeiro do Norte de R$ 5 milhões fora do esperado, NF 429 com redução de base). Todas as notas saem
pela matriz (um CNPJ para todas as unidades), então um único extrato cobre o grupo. A Luciana tem
acesso e consegue tirar o extrato com facilidade; existe histórico desde 2022, mas o foco é 2026.
No futuro a fonte oficial pode passar a ser o extrato da prefeitura.

Arquivo de exemplo na pasta compartilhada: `RECEITAS - Faturamento - Prefeitura/ConsultaNotaFiscalXls
19.10.2026.xls`. Prompt Mestre §3 (contrato de dados, níveis de confiança), §6 (sanidade), T5.

## What Changes

- Nova fonte "Notas da prefeitura (NFS-e)" com perfil determinístico do export da prefeitura
  (número, emissão, competência, tomador, valor do serviço, deduções, base, ISS, retenções, situação
  incluindo cancelada e substituída).
- Conferência por nota entre planilha do financeiro × prefeitura × NG: nota ausente em uma das
  fontes, valor, data, competência, retenções e situação (cancelada contando valor).
- Relatório de divergências para o financeiro (pode entrar no e-mail semanal de inconsistências).
- Fonte oficial do faturamento na DRE como decisão versionada da Controladoria (hoje: planilha do
  financeiro; candidata: prefeitura), sem trocar sozinha.
- Notas substituídas: seguir a cadeia substituída → substituta para não contar duas vezes.

## Capabilities

### New Capabilities
- `billing-crosscheck`: fonte de NFS-e da prefeitura e conferência planilha × prefeitura × NG.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- Novo perfil em `backend/onyx/ton/operational_import`, regras de conferência, Fontes UI, e-mail
  semanal, decisão de fonte oficial na DRE.

## Dependências

- Layout estável do export da prefeitura (o .xls de 19/10 é a primeira amostra); confirmar se todas
  as prefeituras dos contratos exportam no mesmo formato ou se é um único portal da matriz.
- Decisão da Controladoria sobre quando a prefeitura vira a fonte oficial.
- Envio das medições mensais e notas substituídas com cópia para a Controladoria (ata 16/10).

## Estado de dado

Real (2026).
