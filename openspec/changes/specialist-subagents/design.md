## Context

Decisão vigente (contexto 05 §3, 07 §2): especialistas são papéis internos do coordenador TON, não nove
Personas, para evitar chats desconexos, prompts editáveis e perda de governança. `SPECIALISTS` em
`registry.py` define objetivo, domínio, capacidades requeridas e ferramentas permitidas.

## Goals / Non-Goals

**Goals:** fronteira por domínio aplicada por código (ferramentas e regras), entrega característica,
handoff único, ativação por fonte, CEO consolidando.

**Non-Goals:** nove chats independentes; prompts de especialista editáveis por usuário final.

## Decisions

- **Manter papéis internos**, mas com execução isolada por especialista (contexto próprio, ferramentas
  restritas, saída estruturada) chamada pelo coordenador; reavaliar se o runtime do Onyx oferecer
  sub-agente nativo sem duplicar o runtime.
- **Ativação derivada**: especialista ativo ⇔ fontes conformes do domínio existem e ao menos uma regra
  do domínio está operacional (cobertura).
- **Handoff**: o registro de ocorrência exige `owning_domain`; o coordenador não cria ocorrência
  duplicada quando dois especialistas veem o mesmo fato (identidade determinística já garante).
- **Saídas estruturadas** (JSON validado) por especialista; o CEO consome as saídas, não texto livre.

## Risks / Trade-offs

- [Latência multiplicada por especialista] → delegar só aos domínios relevantes à pergunta; orçamento
  de etapas do coordenador.

## Open Questions

- O runtime atual do Onyx já tem primitiva de sub-agente adequada?
