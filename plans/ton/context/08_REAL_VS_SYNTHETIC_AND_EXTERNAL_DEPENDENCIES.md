# TON — DADOS REAIS, SINTÉTICOS E DEPENDÊNCIAS EXTERNAS

## 1. Regra de leitura

Existem três estados diferentes e eles NÃO podem ser misturados.

### A. Validado com dado real
Ocorreu um smoke/inspeção real controlada.

### B. Implementado mas sem fonte real atual
Código existe, mas não houve validação real recente.

### C. Sintético/demonstração
Fixture local para provar a UI/flow.

O agente deve sempre saber em qual estado está.

---

# 2. NG/Keevo

Estado atual conhecido:
**manual file acquisition**.

O TON suporta import de arquivo.

Integração direta ainda não foi feita.

Dependências para avançar:
- acesso VPN;
- API ou DB/view read-only;
- autorização;
- documentação;
- possivelmente usuário técnico dedicado;
- definição da consulta/relatório oficial;
- acesso ao histórico necessário.

A integração não deve ser inventada.

A arquitetura planejada para futuro é:

```text
NgKeevoConnector
→ source adapter
→ Source
→ Snapshot
→ parser/profile
→ existing financial pipeline
```

Também é desejável manter manual upload como fallback.

---

# 3. Zeev

Existem fundações de leitura/discovery.

Commits conhecidos:
- `8259239cf0` — BE-004A
- `c38c3692e1` — BE-004B

Zeev é fonte de:
- workflow;
- SLA;
- produtividade;
- processos.

Ele NÃO é o núcleo da DRE.

Estado live/sync/semântica oficial:
ainda não totalmente validado.

Não anunciar integração completa sem prova.

---

# 4. Faturamento

Manual file import suportado.

Smoke sintético já comprovou parser/API.

Real current validation:
não disponível no último handoff.

---

# 5. Dotação

Manual file import suportado.

Estruturas de três workbooks já foram inspecionadas.

Calendário mensal/budget periods continuam dependentes de decisões reais.

---

# 6. Especialistas

CFO/AUDITOR/CEO têm fundação operacional com dados disponíveis.

Outros domínios aguardam fontes específicas:

- COO: produção;
- FROTA: frota/abastecimento/manutenção;
- CONTRATOS: contrato/cadastro mestre;
- COMPLIANCE: documentos/obrigações;
- PROCUREMENT: compras/fornecedores;
- RH: folha/quadro/ponto etc.

Isso não significa “o especialista está errado”.

Significa que o domínio ainda não tem fonte/capability suficiente.

---

# 7. Current real DRE

No smoke real de readiness:
`0/6` períodos ficaram READY.

Isso é esperado enquanto as decisões de mapping/readiness ainda não tiverem sido aprovadas.

A UI de READY existente é de demonstração/synthetic only.

---

# 8. Sintético conhecido

O projeto usa fixtures sintéticas para provar:
- READY DRE;
- blocked DRE;
- sources;
- reports;
- R3;
- chat tools;
- specialist statuses.

Esses valores não são desempenho real da Vale Norte.

---

# 9. O que falta a Luyla fornecer

Perguntas de integração NG:

- como NG/Keevo é acessado hoje?
- existe VPN disponível para o servidor?
- existe API?
- existe banco/view read-only?
- qual DBMS?
- existe usuário técnico?
- quais relatórios/queries são oficiais?
- qual sistema/contato mantém a integração?
- histórico 2025 está autorizado?
- quais campos significam o quê?

Perguntas Zeev:
- fluxos oficiais;
- campos;
- statuses;
- SLA;
- ownership;
- deadline semantics.

Perguntas de outros especialistas:
- fonte oficial;
- periodicidade;
- responsável;
- regras;
- limites.

---

# 10. Regra de demo

A demo deve dizer a verdade:

```text
Hoje:
NG → importação manual

Próximo passo:
NG → integração autorizada

Depois:
NG → atualização automática
```

Isso é melhor do que simular conectividade.

