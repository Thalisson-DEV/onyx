## Why

O Prompt Mestre §3.3 separa unidades **operacionais** (Itabirito, Juazeiro do Norte, Juazeiro-BA,
Mossoró-RN, Mossoró Aterro, Sento Sé-BA, Toledo-PR), **em implantação/prospecção** e **não
operacionais** (Administração Central, Diretoria, Chácara, Shopping, mútuos, Vale Norte Obra), com a
regra: margem de não operacional nunca entra em ranking nem benchmark; Administração Central entra
só no consolidado, com a distorção explicitada na mesma página. §6.2 completa: o consolidado com
parcelamentos (−R$ 128,2 mi acumulado na DRE real de jun/2026) **não é resultado operacional** e
nunca pode aparecer sem ressalva na mesma linha. Hoje o TON trata as 22 unidades do NG + "(sem
unidade)" igualmente e apresenta o consolidado sem essa leitura.

## What Changes

- Classificação versionada de unidade (operacional / implantação-prospecção / não operacional /
  sem unidade), decidida pela Controladoria, com sugestão inicial a partir do §3.3.
- Visão "Resultado operacional" (soma das operacionais) ao lado do consolidado, com Administração
  Central e satélites segregados e a distorção explicada na mesma linha.
- Rankings e comparações entre unidades excluem não operacionais.
- Ressalva obrigatória quando o consolidado contém evento não recorrente material (insumo do T10).

## Capabilities

### New Capabilities
- `unit-classification`: classificação de unidades e regras de consolidação do §3.3/§6.2.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- `backend/onyx/db/ton/financial_domain.py` (unidades), `backend/onyx/ton/dre/engine.py` (escopo
  operacional), DRE UI, Visão Geral, ferramentas do assistente.

## Dependências

- Pergunta C3 à Luyla (mútuos/Chácara no resultado). Lista do §3.3 pode estar desatualizada
  (ex.: Canoas-RS em julgamento).

## Estado de dado

Real.
