## Why

Hoje, quando aparece no NG uma conta ou descrição nova, a Controladoria classifica à mão numa
planilha (estrutura do balanço e natureza). Na reunião de 2026-10-03 (ata, pedido 4) a Luyla pediu
que esse cadastro passe a viver no TON, editável **como uma tabela de Excel** na área administrativa,
que o TON **acuse** conta nova sem classificação, **pré-classifique por regras definidas pela
Controladoria** e peça revisão. Hoje a classificação do TON veio do "Banco de Dados (Vale
Norte).xlsm" por script, e 29 códigos foram classificados por semelhança sem evidência dela.

## What Changes

- **Tabela de classificação** na Administração do TON: código NG, descrição, natureza, grupo da DRE,
  origem (Banco de Dados, regra, decisão manual), autor e data; edição em linha com justificativa,
  cada alteração como nova versão (os mapeamentos já são versionados).
- **Importar/exportar** a tabela em Excel, para conferir com a planilha atual.
- **Conta nova** detectada na importação → item "classificação pendente" no TON e no relatório semanal.
- **Regras de pré-classificação** escritas pela Controladoria (ex.: "código começa com 3.1 → FOLHA";
  "descrição contém COMBUSTÍVEL → COMBUSTÍVEL"), determinísticas e versionadas; a pré-classificação é
  sempre uma **sugestão** que exige confirmação.
- Revisão dos 29 códigos classificados por semelhança, marcados como "aguardando confirmação".

## Capabilities

### New Capabilities
- `account-classification`: cadastro editável de classificação NG → natureza → DRE, conta nova pendente e regras de pré-classificação.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- `backend/onyx/db/ton/financial_domain.py` (mapeamentos), novos endpoints, Administração do TON
  (grade editável), importação NG (detecção de conta nova), relatório semanal.

## Dependências

- Regras de pré-classificação escritas pela Luyla. Não-negociável preservado: nada de classificação
  por similaridade ou LLM como **decisão**; a decisão é sempre confirmação humana.
- 2026-10-04: o Thalisson decidiu que a **pré-classificação** pode usar o assistente (IA) sem esperar
  as regras da Luyla, porque é só sugestão com justificativa e passa pela análise dela.

## Estado de dado

Real (178 mapeamentos atuais).
