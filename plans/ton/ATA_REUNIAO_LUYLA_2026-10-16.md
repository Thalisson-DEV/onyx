# Ata — Reunião TON × Controladoria Vale Norte (2026-10-16)

Participantes: Thalisson Damião; Luyla (Controladoria), com Eloísa ("Eloía" na transcrição) e Luciana
na sala. Reunião virtual, ~16h30–17h20; a transcrição cobre 00:20:55–00:52:29.
Fonte: transcrição do Google Meet, conferida também contra o estado do TON local. As notas
automáticas do Gemini têm erros; correções na seção 6.

## 1. Decisões

| # | Decisão | Trecho |
|---|---|---|
| D1 | **Homologação em nuvem (Railway) com dados reais**, entregue por Thalisson até a noite de 16/10 ou a manhã de 17/10. A Luyla autorizou explicitamente os dados reais na nuvem ("é tranquilo por nossa parte"). Produção fica em aberto: servidor próprio da Vale Norte, servidor contratado ou a infraestrutura oferecida por Thalisson como serviço. | 00:24, 00:51 |
| D2 | **Duas estruturas de DRE**: uma **econômica** (por competência) e outra **de caixa**, que a Luyla descreveu como "modalidade caixa, que é por vencimento". Particularidades e indicadores de cada uma serão definidos em 17/10. | 00:41–00:42 |
| D3 | **Tratamento por nome de fornecedor**: certos fornecedores (exemplo dado: postos de combustível) devem sair da natureza original e ir para outra natureza gerencial (exemplo dado: "custo de consultoria" em vez de combustível). A natureza de destino **ainda não existe** e será criada pela tela de Naturezas. | 00:28–00:30, 00:47 |
| D4 | **Relatório de inconsistências por e-mail** para o Financeiro, com cópia para a Controladoria, e possivelmente uma versão por unidade (5 unidades). Volume estimado: ~7 e-mails por semana. **A frequência não está fechada** (ver seção 5). | 00:38, 00:43 |
| D5 | **E-mails pelo Resend** (cota grátis de 3.000 por mês). Teste na segunda 19/10 com o e-mail da Controladoria ("núcleo"). | 00:43–00:45 |
| D6 | **Integração com o NG continua prioridade zero.** Caminho: usuário de banco **somente leitura** pela Kivo. Luyla e Thalisson ligam juntos para a Kivo na segunda 19/10. Se a Kivo não liberar, a alternativa é um script de extração na máquina que já tem acesso ao NG. | 00:32–00:34 |
| D7 | **Classificação 3.1.0001 confirmada como FOLHA** ao vivo (registrada no TON às 17:09). A Luyla quer **adiantamento de salários (3.1.0015) em FOLHA**, contra a sugestão do assistente ("movimentos não gerenciais"). **No TON a 3.1.0015 continua aguardando confirmação.** A confirmação em lote das 21 contas em que o assistente concorda **não foi feita**. | 00:48–00:50 |
| D8 | O visual está simples e passará por um **polimento depois**; o foco agora é lógica e funcionalidade. A Luyla concordou. | 00:26–00:27 |

## 2. Pedidos novos da Luyla

1. **Criar gatilhos de automação pelo chat do TON.** Hoje o chat rascunha automações, mas não cria gatilhos ou eventos novos; exige remapear a arquitetura. Thalisson aceitou como próximo passo, sem prazo.
2. **Regra de reclassificação por fornecedor** (D3). O tratamento de fechamento hoje filtra por natureza, unidade e período, **não por fornecedor**: a regra exige um critério novo de fornecedor (nome ou CNPJ), possivelmente com a sugestão da IA e aprovação humana.
3. **DRE de caixa** além da econômica (D2).
4. **Proposta de valor mensal** da infraestrutura do ambiente, para comparar com servidor próprio ou externo.
5. Remetente dos e-mails com o **endereço corporativo** da Vale Norte.

## 3. Fatos de processo aprendidos

- **A reunião com a diretoria mudou.** Na **segunda 19/10** a Luyla apresenta a análise de resultados (DRE) à **Miriam**. A apresentação ao diretor fica para **terça ou quarta**: a fala é ambígua ("vai ser terça-feira, não é, Luciana? … que achei a quarta-feira"). Não é uma reunião sobre o TON: é a reunião financeira, com o TON como complemento (inconsistências, notificações automáticas, ajuste da DRE, exportação em Excel).
- Quase todo mês surge natureza ou conta nova no NG; a Luyla acrescenta à mão no Banco de Dados em Excel.
- Na exportação, o NG permite padronizar as colunas, então mudanças de coluna não devem afetar o export (opinião da Luyla, a confirmar).
- **O export do NG que o TON lê só traz a data de Emissão.** Não há vencimento nem data de pagamento. Isso já bloqueia o tratamento "parcelamentos só pela parcela paga" e afeta diretamente a DRE de caixa (D2).
- Sexta-feira o expediente da Controladoria termina às 17h.

## 4. Próximos passos

| Responsável | Ação | Quando |
|---|---|---|
| Thalisson | Subir a homologação no Railway e enviar link, usuário e senha | 16/10 à noite ou 17/10 cedo |
| Thalisson + Luyla | Reunião para guiar a Luyla a carregar as fontes (jan–set) na homologação **e** detalhar as duas DREs (econômica e caixa) | **Sábado 17/10, 9h** |
| Luyla | Liberar acesso à pasta do Drive com o export de setembro | 16/10 (ela disse que liberaria na hora) |
| Luyla | Enviar o e-mail da Controladoria ("núcleo") para o teste do Resend | 16/10 |
| Luyla | Enviar o WhatsApp da equipe da Kivo | antes de 19/10 |
| Luyla + Thalisson | Ligar para a Kivo pedindo usuário de banco somente leitura | **Segunda 19/10** |
| Thalisson | Configurar Resend (chave e domínio) e testar o envio | até 19/10 |
| Thalisson | Enviar proposta de valor mensal da infraestrutura | a combinar |
| Thalisson | **Tentar** adiantar o módulo e o especialista de contratos | fim de semana 17–18/10 |
| Thalisson | Cadastrar com a Luyla a natureza "consultoria" e a regra por fornecedor; aplicar e mostrar a DRE recalculada | 17/10 |

## 5. Perguntas em aberto (levar para 17/10)

- **E-mail de inconsistências: segunda e quarta 9h ou sexta?** No TON a automação está como "seg e qua 9h", **pausada**. Esse horário foi o exemplo que Thalisson mostrou; depois a Luyla disse "toda sexta-feira… para o financeiro com cópia para a controladoria".
- **DRE de caixa "por vencimento"**: regime de caixa costuma usar a **data de pagamento**; vencimento é a data prevista. Qual das duas ela quer? Como o export atual não tem nenhuma das duas, qual relatório do NG traz essas datas?
- **Reclassificação de fornecedor**: o exemplo "posto de combustível → consultoria" foi dito assim pela Luyla e confirmado pelo Thalisson (não é erro da transcrição). Falta saber: quais fornecedores entram? Por nome ou por CNPJ? Vale para todas as unidades e todos os meses?
- Adiantamento de salários (3.1.0015): confirmar FOLHA no TON junto com ela.
- Reunião com o diretor: terça ou quarta?
- Remetente corporativo: o domínio da Vale Norte precisa ser verificado no Resend (registros DNS SPF/DKIM). Quem cuida do DNS? Provavelmente o Celso.

## 6. Correções às notas automáticas do Gemini

- **"Reunião com a diretoria transferida para 4ª-feira"**: a fala diz terça e quarta; não está claro. Na segunda a reunião é com a Miriam.
- **"Relatórios de inconsistências… segundas e quartas, 9h" como decisão**: isso é o que estava configurado na demonstração, e a automação está **pausada**. A Luyla citou depois **sexta-feira**. Frequência em aberto.
- **"Resend dispensa burocracias de IP e DNS"**: dispensa IP e servidor de e-mail próprios, **mas não o DNS**. Para enviar com o endereço da Vale Norte, o domínio precisa ser verificado com registros DNS (SPF/DKIM). Essa parte da fala do Thalisson estava imprecisa.
- **"Aplicação de regras de tratamento para fornecedores" como algo que o TON já faz**: hoje o tratamento não filtra por fornecedor; precisa ser desenvolvido (pedido 2). Também falta criar a natureza de destino.
- **"Implementar o módulo de contratos durante o fim de semana"**: o compromisso foi **tentar adiantar**. A Luyla tratou contratos e frota como "etapa dois".
- **"Orientar configuração da DRE"**: a reunião de 17/10 às 9h tem dois objetivos: guiar a Luyla a carregar as fontes na homologação **e** definir as duas estruturas de DRE.
- **"Hospedagem do ambiente em nuvem privada… Railway"** como decisão geral: vale para a **homologação**; produção está em avaliação (D1).
- **O Gemini não registrou**: a confirmação da 3.1.0001 e o pedido de FOLHA para o adiantamento de salários (D7); que a natureza de consultoria ainda não existe; que o export do NG não tem vencimento nem pagamento.
- Nomes: "Miram/Mira" na transcrição = Miriam (grafia do Gemini, a confirmar); "Eloía" = Eloísa.
