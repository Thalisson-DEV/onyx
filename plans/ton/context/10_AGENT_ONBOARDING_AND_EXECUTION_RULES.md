# TON — ONBOARDING DO AGENTE E REGRAS DE EXECUÇÃO

## 1. Antes de tocar no código

Executar:

```text
git status --short
git branch --show-current
git rev-parse HEAD
git log -10 --oneline --decorate
```

Depois localizar:
- roadmap atual;
- task tracker atual;
- decisions;
- Prompt Mestre;
- `ton_reference_visual`;
- este pacote de contexto.

---

# 2. Não confiar cegamente nos handoffs

Handoffs históricos podem:
- ter sido escritos antes de outra mudança;
- descrever uma branch;
- descrever sintético como smoke;
- ter sido superseded por rebuild.

Sempre conferir código/API.

---

# 3. O agente deve atuar como

- engenheiro;
- arquiteto;
- product engineer;
- UX reviewer.

Não apenas executor de checklist.

---

# 4. GAP discovery é obrigação

Além das tarefas explícitas:
procure gaps de:

- produto;
- workflow;
- dados;
- UX;
- trust;
- automation;
- presentation.

Registrar evidência e prioridade.

---

# 5. Não quebrar os invariantes

Nunca contornar:
- readiness;
- reviewed dataset;
- versioning;
- audit;
- human decisions;
- source lineage;
- tenant isolation.

---

# 6. Quando adicionar backend

Adicionar apenas se o workflow de produto precisar.

Preferência:
- read models;
- agregações;
- endpoints read-only;
- domain service limpo.

Não criar regra financeira em React.

---

# 7. Quando usar IA

Usar IA para:
- interpretar;
- resumir;
- explicar;
- priorizar;
- orientar.

Não usar IA como:
- detector primário de erro;
- calculadora financeira;
- substituto do mapping aprovado;
- fonte de verdade.

---

# 8. UX acceptance

Uma tela não é pronta porque:
- compila;
- tem teste;
- API responde.

Ela está pronta quando:
- usuário entende;
- ação é clara;
- estado é honesto;
- feedback existe;
- não parece Onyx;
- não parece Markdown;
- não parece AI slop;
- reduz trabalho.

---

# 9. Progress protocol

Após cada slice estável:

1. atualizar tracker;
2. registrar decisões;
3. validar;
4. commit local;
5. continuar.

No tracker, registrar:

```text
Milestone
Commit
What changed
What is demonstrable
Validation
New gaps
Known issues
Next
```

---

# 10. Stop conditions

Parar e perguntar somente para:
- credenciais/acesso externo;
- migration destrutiva;
- mudança de arquitetura com consequências materialmente diferentes e sem evidência suficiente;
- mudança de outro agente;
- necessidade de inventar dado/capability.

Bloqueio de uma tarefa independente:
marcar e seguir.

---

# 11. Demo truth

Para qualquer demonstração:
- sintético precisa estar identificado;
- integração ausente precisa estar ausente;
- READY synthetic não é READY real;
- “operacional” precisa vir do runtime real;
- exemplos não podem virar claims da empresa.

---

# 12. Contexto do cliente

A reunião com Luyla não é “aprovação de uma tela”.

É oportunidade para obter:
- NG access;
- source authority;
- business mappings;
- definitions;
- historical access;
- operating cadence;
- rules;
- owners/deadlines.

O produto deve ser construído de forma que cada novo acesso real caiba no pipeline existente.

---

# 13. Objetivo final

O estado desejado não é:

```text
chatbot + dashboards
```

É:

```text
TON
├─ lê fontes
├─ valida
├─ cruza
├─ encontra
├─ evidencia
├─ quantifica
├─ prioriza
├─ orienta decisão
├─ registra
├─ recalcula
├─ acompanha
└─ comprova resultado
```

O agente deve preservar esta direção em toda decisão de implementação.

---

# 14. OpenSpec é o tracker de execução (desde 2026-10-02)

- Antes de codar: `openspec list`, `openspec/roadmap.md`, `openspec/config.yaml`.
- Escolha uma change desbloqueada; leia `proposal.md`, `design.md` e `specs/`; confira com o código.
- Marque `tasks.md` à medida que entrega; ao concluir, `openspec validate <change> --strict` e
  `openspec archive <change>` (atualiza `openspec/specs/`).
- Mantenha atualizados: a tabela de estado e as fases do roadmap, a cobertura do Prompt Mestre no
  código (`capabilities.py`/`registry.py`) e este pacote de contexto.
- O protocolo de progresso do §9 continua valendo, agora dentro da change.
- Nova necessidade descoberta: crie uma change nova (pasta com proposal/specs/tasks) e inclua-a no
  roadmap — não deixe gaps só em relatório.
