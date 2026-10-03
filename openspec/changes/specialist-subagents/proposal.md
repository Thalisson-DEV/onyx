## Why

"Você é um sistema, não um chatbot" (Prompt Mestre §15). Cada subagente tem fronteira e entrega
própria (CFO: margem prevista × real e forecast; COO: ranking de produtividade; FROTA: exceções de
consumo e decisão consertar/substituir; CONTRATOS: reconciliação da cadeia; COMPLIANCE: matriz de
obrigações; PROCUREMENT: benchmark de preço; RH: quadro × dotação; AUDITOR: bateria completa e base
aprovada/reprovada; CEO: resposta em 5 linhas a "como estão nossos contratos?"), todos escrevendo no
mesmo ledger com a mesma régua, e a regra de handoff: achado que atravessa fronteira é registrado uma
única vez, pelo elo onde a quantidade mudou. Hoje os especialistas são papéis com listas de
ferramentas; só CFO/AUDITOR/CEO atuam, sem entrega característica nem handoff aplicado.

## What Changes

- Contrato de especialista: domínio, ferramentas, regras/baterias que possui, entrega característica,
  fontes requeridas (ativação automática quando as fontes do domínio existem).
- Orquestração pelo coordenador TON: delegação por domínio, execução dentro do protocolo, e
  consolidação pelo CEO.
- Handoff no ledger: ocorrência registrada uma vez pelo domínio dono; outros especialistas aparecem
  como impactados (`OccurrenceImpactedDomain`).
- Entregas características implementadas à medida que os domínios chegam; especialista sem fonte
  continua "aguardando fonte" com a fonte nomeada.

## Capabilities

### New Capabilities
- `specialist-subagents`: contrato de especialista, delegação, handoff e entregas características.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- `backend/onyx/ton/agent/{registry,service,closing_models}.py`, prompt do TON, timeline de
  raciocínio, página Especialistas.

## Dependências

- Decisão de runtime (papéis internos × sub-agentes do Onyx) a reavaliar contra o código atual
  (contexto 05 §3). Domínios das fases 3–4 para os especialistas além de CFO/AUDITOR/CEO.

## Estado de dado

Real.
