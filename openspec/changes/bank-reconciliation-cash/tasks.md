## 1. Fontes

- [ ] 1.1 Obter extratos detalhados por conta e formato disponível (OFX/CNAB/CSV)
- [ ] 1.2 Perfis de extrato e de contas a pagar/receber
- [ ] 1.3 Perfil do "Extrato Bancário Analítico" do NG (PDF, já lido localmente em 19/10) como fonte do pipeline, além do extrato do banco
- [ ] 1.4 Conferência extrato do NG × extrato do banco (saldo e lançamentos)
- [ ] 1.5 Data de pagamento conciliada como origem da DRE de caixa (só pago)
- [ ] 1.6 Juros, encargos e antecipação a partir dos extratos de cartão (ata 20/10)

## 2. Conciliação

- [ ] 2.1 Motor de conciliação banco × NG com tolerância aprovada e quatro tipos de divergência
- [ ] 2.2 Decisão humana para ambíguos (reaproveitar padrão de decisão de conciliação)
- [ ] 2.3 Fluxo de duplicidade de pagamento com evidência
- [ ] 2.4 Fundo fixo e adiantamentos

## 3. Caixa

- [ ] 3.1 DFC gerencial a partir de caixa conciliado (após aceite da conciliação)

## 4. Validação

- [ ] 4.1 Testes com extratos sintéticos
- [ ] 4.2 Piloto real com uma conta
- [ ] 4.3 Atualizar `openspec/roadmap.md`
