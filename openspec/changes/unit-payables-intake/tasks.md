## 1. Definição (com a Controladoria)

- [ ] 1.1 Receber a validação do documento "TON — Padrão de informações das unidades" e as respostas às perguntas
- [ ] 1.2 Decidir folha/encargos/impostos fora do contas a pagar da unidade
- [x] 1.3 Relação com o Zeev — decidido em 2026-10-24: o TON **lê** a solicitação de pagamento do Zeev e **concilia** com o título da unidade (exige a integração robusta de `zeev-integration`)
- [ ] 1.6 Piloto em **Toledo e Mossoró** (decidido em 2026-10-24)
- [ ] 1.4 Definir prazo de envio após a chegada da nota e o limiar de "em cima do vencimento" (parâmetro versionado)
- [ ] 1.5 Definir responsáveis: quem mantém o cadastro de fornecedores e quem aprova fornecedor novo

## 2. Cadastro e entrada

- [x] 2.1 Cadastro de fornecedor/favorecido (CPF/CNPJ chave, dados de pagamento no nome do próprio favorecido), compartilhado com `procurement-domain` — 2026-10-24: `ton_payable_supplier`, unidade propõe e o financeiro aprova; nome parecido e conta compartilhada aparecem na aprovação
- [ ] 2.2 Carga inicial dos fornecedores a partir do NG e das planilhas atuais, com revisão humana dos duplicados
- [x] 2.3 Título a pagar com os campos do padrão, parcela "x de y", natureza sugerida pelo fornecedor
- [x] 2.4 Anexos obrigatórios com nome padronizado; leitura de XML/PDF de NF quando possível — XML de NF-e/NFS-e (emitente, número, total) e linha digitável do boleto no PDF (valor e vencimento); o resto vai para conferência manual
  - [x] 2.4.1 Nota que não é XML (2026-10-28): DANFE em PDF pela chave de acesso (DV, modelo e CNPJ validados; total e emissão só quando impressos ao lado do rótulo), sem IA. NFS-e em PDF, PDF escaneado e foto: a IA transcreve e o código valida cada campo (CNPJ, chave, linha do boleto, datas, valores); o resultado fica marcado como lido pela IA (`read_source`), a tela pede confirmação e divergência vira atenção, nunca bloqueio. Amostras em `plans/ton/test-files/teste-leitura-*`; testes em `backend/tests/unit/ton/test_payables_reading.py`
- [x] 2.5 Estimativa como tipo próprio, substituição pela nota

## 3. Fluxo do financeiro

- [x] 3.1 Estados recebido → conferido → liberado → lançado no NG → pago, com histórico (quem, quando, motivo)
- [ ] 3.2 Status de pagamento a partir da baixa no NG e/ou do extrato conciliado
- [x] 3.3 Fila do financeiro e tela da unidade (pendências devolvidas com motivo)

## 4. Conferências

- [x] 4.1 NF/parcela repetida; anexo × linha; conta sem anexo
- [x] 4.2 Favorecido ≠ fornecedor; mesma conta para favorecidos diferentes
- [x] 4.3 Estimativa sem nota; fornecedor novo ou parecido
- [ ] 4.4 Confronto enviado pela unidade × lançado no NG (os dois lados)
- [x] 4.5 Testes determinísticos por conferência, com fixtures sintéticas (`backend/tests/unit/ton/test_payables.py`)

## 5. DRE e validação

- [ ] 5.1 Origem econômica (competência) e de caixa (pago) na DRE
- [ ] 5.2 Piloto real com uma unidade em paralelo à planilha por um mês
- [ ] 5.3 Validação no Chrome (unidade e financeiro, desktop e celular)
- [ ] 5.4 Atualizar `openspec/roadmap.md` e `plans/ton/context`

## Notas da primeira entrega (2026-10-24)

- Tela `/ton/contas-a-pagar` (fila com etapas, detalhe ao clicar) e `/ton/contas-a-pagar/fornecedores`; migração `c4f8a2d6e1b7`.
- Gestor de unidade envia e corrige contas das unidades que vê; não confere nem libera. O texto do perfil em Usuários foi atualizado.
- Prazo "em cima do vencimento": 5 dias úteis (provisório, igual ao Zeev), sem feriados. Estimativa sem nota: alerta 5 dias após o fim do período (provisório).
- Naturezas 2.01–2.05 (folha, encargos, rescisão, provisões, gratificação) geram atenção "Folha no contas a pagar", até a decisão 1.2.
- Status "pago" ainda não existe na tela: depende de 3.2 (baixa do NG ou extrato).

## Segunda entrega no padrão aprovado (2026-10-24)

- Telas refeitas no padrão de página aprovado (protótipo https://claude.ai/artifact/BN7LY14Z3mcVYJGeG7q9cJ; classes `tp-` em ton.css e `views/ton/components/pattern.tsx`).
- Agenda de pagamentos agrupada por vencimento, visões rápidas (vencidos, 7 dias, para conferir, com impedimento, esperando a unidade, prontos para pagar), filtros por unidade, vencimento, natureza e forma de pagamento.
- Ações em lote: conferir, liberar, lote de pagamento em Excel (favorecido, CNPJ, chave PIX ou banco, valor, histórico para o NG, subtotal por dia) e .zip das notas e boletos com nome padronizado.
- Conferência em página própria: nota montada a partir do XML ao lado da lista "conferido pelo TON", histórico sugerido para o NG, anterior/próximo e "conferido, próximo".
- Envio começa pelo documento: o XML preenche fornecedor (pelo CNPJ), número, emissão, competência, total e parcelas; o boleto preenche valor e vencimento; uma nota com N duplicatas vira N títulos de uma vez.
- Achado da planilha de Toledo: o CNPJ da Neto Performance (52.757.567/0001-97) tem dígito verificador inválido; o cadastro novo recusa.
