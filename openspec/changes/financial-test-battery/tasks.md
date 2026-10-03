## 1. Base

- [ ] 1.1 Registrar T1–T12 em `Rule`/`RuleVersion` com parâmetros padrão do Prompt Mestre, NC e domínio dono
- [ ] 1.2 Executor por competência sobre fatos canônicos; identidade por teste; integração com `record_detection__no_commit`
- [ ] 1.3 Fluxo de aprovação de parâmetros (Administração do TON) com versão

## 2. Testes

- [ ] 2.1 T10 evento não recorrente
- [ ] 2.2 T6 sinal invertido (reutiliza decisões de sinal da sanidade)
- [ ] 2.3 T2 desvio de média móvel (janela 3) e T1 grupo zerado (lista de grupos contratuais aprovada)
- [ ] 2.4 T5 receita replicada
- [ ] 2.5 T3 duplicidade entre unidades/meses (sem duplicar NGF-DUP)
- [ ] 2.6 T9 competência retroativa (30 dias / 5%)
- [ ] 2.7 T7 sem apropriação
- [ ] 2.8 T11 partes relacionadas (lista aprovada; mútuos/Chácara)
- [ ] 2.9 T4 por unidade operacional com de/para tomador → unidade aprovado
- [ ] 2.10 T8 condicionado à existência de CNPJ do fornecedor; senão "não avaliado"

## 3. Validação

- [ ] 3.1 Testes unitários por teste (disparo, não disparo, não avaliado) e fixtures de calibração §6.2
- [ ] 3.2 Rodar sobre jan–jun/2026 real; revisar os achados com a Luyla antes de publicar
- [ ] 3.3 Atualizar `capabilities.py` (T1–T11) e `openspec/roadmap.md`
