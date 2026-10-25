## 1. Fontes

- [ ] 1.1 Levantar sistemas/planilhas de frota, abastecimento, manutenção e postos por unidade
- [ ] 1.2 Perfis conformes ao contrato de dados; fatos de domínio de frota

## 2. Regras

- [ ] 2.1 T22 (regras de registro, sem dependência estatística)
- [ ] 2.2 T21 com mínimo de 3 comparáveis e 2 semanas consecutivas
- [ ] 2.3 T23 (valor de reposição aprovado por tipo) e T24 (dotação confirmada)
- [ ] 2.4 Compra fora de posto conveniado

## 3. Operação

- [ ] 3.1 R2 semanal (sexta 07h) no framework de rotinas
- [ ] 3.2 Especialista FROTA ativo com ferramentas; superfície de frota
- [ ] 3.3 Quantificação (litros × preço médio; manutenção acima do previsto)

## 4. Validação

- [ ] 4.1 Testes com fixtures sintéticas
- [ ] 4.2 Validação real com uma unidade piloto (Mossoró)
- [ ] 4.3 Atualizar cobertura (T21–T24, R2, FROTA) e `openspec/roadmap.md`

## 5. Acrescentado em 2026-10-23

- [ ] 5.1 Carga inicial do cadastro a partir do `Gerenciamento de Frota` (prefixo, placa, condição, unidade, status, medidor, proprietário), com revisão humana das placas repetidas entre unidades
- [ ] 5.2 Cadastro de contrato de locação (locador, veículos, valor, cálculo, combustível, vigência, anexo) e migração das listas de locação das unidades e da Vamos
- [ ] 5.3 Eventos de frota com aviso simultâneo e registro do atraso do aviso
- [ ] 5.4 Aluguel mensal gerado pelo contrato; confirmação mensal do gestor; desconto por dias parados; rateio por unidade e por dias
- [ ] 5.5 Perfil do extrato Alelo (layout de 2026-10-21) e do relatório "Venda por Cliente" do posto; normalização de placa
- [ ] 5.6 Conferências novas: sem motorista/hodômetro, sequência acima do tanque, valores redondos, inativo abastecido ou pago, locação sem contrato, aviso atrasado
- [ ] 5.7 Competência do combustível pela data do abastecimento na DRE
- [ ] 5.8 Decidir com a Luyla a solicitação de abastecimento com aprovação (modelo CES)
- [ ] 5.9 Integração com o cartão único quando a empresa for escolhida
- [ ] 5.10 Rateio de veículos de outras empresas do grupo e de uso pessoal (regra da Controladoria)
