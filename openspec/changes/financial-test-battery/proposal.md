## Why

O Prompt Mestre §7 herda do PAD-CTRL-001 a bateria T1–T12, executada sobre toda competência antes de
qualquer relatório, com códigos e NCs idênticos ao padrão. Hoje só existem as regras NGF (rejeição,
unidade ausente, duplicidade exata/formato) — T4 é parcial (conciliação NG × faturamento sem o teste
por unidade) e T1–T3, T5–T12 não existem. Vários testes pegariam sozinhos os problemas reais já
conhecidos: T10 (lançamento > 5% da despesa do mês) pegaria os parcelamentos de abril/maio; T4/T14
a receita de Mossoró de abril; T1/T2 o combustível de Mossoró em mar–abr; T11 os mútuos/Chácara;
T9 os lançamentos concentrados no fechamento. T2 e T5 já têm histórico suficiente em 2026 (a partir de
abril).

## What Changes

- Executores determinísticos para os testes viáveis com NG + faturamento: **T1** grupo contratual
  zerado (NC-05), **T2** desvio > 15% contra média dos 3 meses anteriores (NC-07), **T3** duplicidade
  NF/valor/fornecedor entre unidades ou meses (NC-01/06), **T4** receita NF × NG > 1% por unidade
  (NC-14), **T5** receita idêntica ao centavo em meses distintos (NC-14), **T6** sinal invertido
  (NC-03), **T7** pagamento sem centro de custo/natureza/competência (NC-03/08), **T9** competência
  retroativa > 30 dias com acúmulo > 5% (NC-02), **T10** lançamento individual > 5% da despesa total do
  mês (NC-03/12), **T11** partes relacionadas (NC-09/13).
- **T8** (fornecedor × unidade) só se o NG trouxer CNPJ/endereço do fornecedor; **T12** (rescisão sem
  multa FGTS) fica na change `hr-payroll-domain`.
- Parâmetros (janela, limiares, lista de grupos contratuais, lista de partes relacionadas) como
  configuração versionada aprovada; os valores do Prompt Mestre são o padrão proposto.
- Cada disparo vira ocorrência no ledger com código T, NC, evidência e domínio dono.

## Capabilities

### New Capabilities
- `financial-test-battery`: testes T1–T12 do PAD-CTRL-001 sobre cada competência.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- Novo módulo de testes (reutilizando `Rule`/`RuleVersion`, `record_detection__no_commit`),
  passo 4 do protocolo, cobertura, relatórios.

## Dependências

- `execution-protocol`, `criticality-and-nc-catalog` (NC e régua), `unit-classification-and-consolidation`
  (T4 por unidade operacional). T4 depende do de/para contrato/tomador → unidade (929 notas de
  faturamento sem unidade correspondente hoje — pergunta R2 à Luyla). Lista de partes relacionadas
  (sócios, coligadas, mútuos) e de grupos contratuais por unidade: Controladoria.

## Estado de dado

Real (jan–jun/2026).
