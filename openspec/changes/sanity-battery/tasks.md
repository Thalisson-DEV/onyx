## 1. Framework

- [ ] 1.1 Registrar S1–S10 em `Rule`/`RuleVersion` com componentes de identidade e domínio dono
- [ ] 1.2 Executor base com estado "não avaliada — falta <fonte>"
- [ ] 1.3 Plugar a bateria no passo 2 do protocolo

## 2. Regras com dado disponível

- [ ] 2.1 S5 (Σ unidades = consolidado, ao centavo, por linha/período)
- [ ] 2.2 Decisões de sinal por natureza (candidatos pelo grupo DRE) e S6 com NC-03
- [ ] 2.3 S8 (AV% por receita bruta da própria unidade)
- [ ] 2.4 S4 genérico para fontes com subtotal declarado
- [ ] 2.5 S10 integrado ao gate (já operacional; reapontar para a bateria)

## 3. Validação

- [ ] 3.1 Fixtures sintéticas dos padrões do §6.2 e testes
- [ ] 3.2 Rodar sobre jan–jun/2026 real e revisar achados com a Luyla
- [ ] 3.3 Atualizar `capabilities.py` (S4, S5, S6, S8) e `openspec/roadmap.md`
