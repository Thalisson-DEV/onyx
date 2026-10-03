## Why

O Prompt Mestre §5 manda que **toda** rotina, pergunta e varredura siga sete passos em ordem fixa —
1 Ingestão, 2 Validação da base, 3 Reconciliação da cadeia, 4 Detecção, 5 Quantificação,
6 Priorização, 7 Publicação e registro — e que a falha de um passo bloqueie os seguintes, dizendo qual
e por quê. Também fixa o teto de saída (7 exceções por varredura diária, 12 por fechamento mensal; o
excedente vai para o ledger sem publicação) e, no §11, exige procurar ativamente **pontos cegos** (o
que não está sendo medido) e publicar lacuna de dado como achado de primeira classe com responsável
nominal. Hoje o R3 registra passos internos (`AnalysisStep`), mas não existe um orquestrador comum
com essa semântica de bloqueio, nem varredura de pontos cegos, nem teto de publicação.

## What Changes

- Orquestrador do protocolo de 7 passos reutilizável por rotinas, análises sob demanda e assistente,
  gravando o estado de cada passo em `AnalysisRun`/`AnalysisStep`.
- Gate: falha crítica no passo 2 (validação/sanidade) bloqueia passos 3–7 de resultado e publica a
  inconsistência e o que ela impede de concluir (S10).
- Passo 1 registra insumos ausentes (por base canônica e calendário de insumos do PAD-CTRL-001) como
  achados com responsável nominal.
- Varredura de pontos cegos (§11) como catálogo de perguntas determinísticas; cada "sim" vira achado
  "indisponível — pendente de informação de campo".
- Teto de publicação 7/12 por criticidade × impacto × urgência; excedente fica no ledger.

## Capabilities

### New Capabilities
- `execution-protocol`: orquestração dos 7 passos, gates, lacunas, pontos cegos e teto de saída.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- `backend/onyx/db/ton/{analysis_runs,analysis_steps,closing}.py`, R3, ferramentas do assistente,
  timeline de raciocínio na UI.

## Dependências

- Calendário D0–D+12 e lista de insumos obrigatórios do **PAD-CTRL-001** (documento a solicitar à
  Luyla). Sem ele, o passo 1 usa as bases canônicas do §3.1 e marca o calendário como pendente.

## Estado de dado

Real.
