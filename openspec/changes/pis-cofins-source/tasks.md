## 1. Fonte

- [ ] 1.1 Pedir à Contabilidade a apuração em XLSX/CSV; documentar o layout recebido
- [ ] 1.2 Criar a fonte e o perfil determinístico (competência, receita base, PIS, COFINS, créditos se houver)
- [ ] 1.3 Validação de totais e diagnósticos

## 2. Domínio e DRE

- [ ] 2.1 Tipo de fato de imposto por competência na normalização
- [ ] 2.2 Atribuição versionada para "Impostos s/ faturamento"; item de prontidão quando ausente
- [ ] 2.3 Item de conciliação receita base × receita DRE
- [ ] 2.4 Regra "não rateado" para DRE por unidade

## 3. Validação

- [ ] 3.1 Testes com fixture sintética no layout real (sem valores reais)
- [ ] 3.2 Importar a apuração real e conferir jan–jun/2026 com o PDF (R$ 690.114,39 PIS; R$ 3.172.873,30 COFINS)
- [ ] 3.3 Chrome: Fontes, DRE, conciliação; atualizar `openspec/roadmap.md`
