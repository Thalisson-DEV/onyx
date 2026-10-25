# Reunião TON × Vale Norte — 23/10/2026 (sexta, manhã)

Participantes: Luyla e Luciana Miranda (Controladoria Vale Norte), Thalisson Damião. Eloía faltou (problema de transporte).
Fontes: resumo do Gemini, transcrição e WhatsApp da tarde. O resumo do Gemini tem erros; as correções estão no §2.

## 1. O que foi dito e decidido

| # | Assunto | Situação |
|---|---|---|
| 1 | Acesso ao NG: Eric (contador) criou um usuário só de consulta para o Thalisson (o Celso não conseguia limitar as permissões) | Credenciais do NG e da Keevo enviadas no WhatsApp; falta testar o acesso e avisar a Luyla. Trocar a senha padrão da Keevo no primeiro acesso |
| 2 | Prioridade de integração: NG antes do Zeev | Alinhado |
| 3 | Zeev: serve para conferir parcelas (quantidade e valor de cada uma), NF, boleto e data de pagamento; o financeiro não alimenta 100%. A Eloía exporta para o Power BI (indicadores: vencimento em menos de 5 dias úteis, volume de solicitações por pessoa, tarefas atrasadas por colaborador) | Thalisson tem a documentação da API do Zeev mapeada; analisar onde entra no TON |
| 4 | Frota e combustível centralizados no TON (não no Zeev) | Alinhado. Thalisson mapeia as necessidades; o grupo padroniza o fluxo e as regras de aviso (mudança, quebra, encerramento de contrato) |
| 5 | Combustível: cada unidade controla de um jeito (Alelo só em Mossoró, guias de papel nas outras); Luyla pesquisa um cartão único para todas as unidades, com limite por pessoa e controle por placa | Luyla manda o nome da empresa do cartão |
| 6 | Locações: Vamos (locadora) e locações diretas de proprietários e funcionários. Hoje o gestor avisa o Jailson, que avisa o Igor, que avisa o financeiro; a informação se perde e a empresa continua pagando o que não devia | Fluxo oficial a definir, com aviso em tempo real e treinamento |
| 7 | Contas a pagar das unidades: 6 unidades mandam Excel (cada uma num modelo) com NF e boleto soltos; 3 pessoas no financeiro conferem, imprimem, lançam no NG e dão baixa | Luyla: "uma das prioridades". Proposta: centralizar no TON |
| 8 | Faturamento: três fontes (NG, planilha do financeiro, extrato da prefeitura). O extrato da prefeitura é o mais confiável; a planilha do financeiro segue como fonte oficial do TON por enquanto. Foco em 2026 | Já é assim |
| 9 | Parcelamentos: Luciana preenche o modelo do TON; junho ficou sem pagamento | Luciana marca as não pagas na coluna em branco (I); o TON considera o resto pago. Pode haver outros parcelamentos (procuradoria, outras pessoas) |
| 10 | DRE de caixa: só o que foi pago. Contas a pagar entra na econômica por competência | Luyla disse "standby", mas a regra ficou clara |
| 11 | Eric também desenvolve um sistema com IA para a contabilidade e diz que escreve direto no NG | Não verificado; Luyla vai marcar reunião com o Eric e o desenvolvedor dele |
| 12 | Modelo comercial: Thalisson ofereceu por hora (com plataforma de transparência das horas); Luyla prefere por projeto/resultado ("nunca vi fechar por hora") | Luyla consulta o gestor. Uma proposta anterior (não ficou claro de quem) foi recusada pelo valor |
| 13 | Luyla vai refazer o levantamento dos sistemas pagos (frota, rastreamento, ponto, BPM, almoxarifado) para mostrar a economia com o TON | Com a Luyla |
| 14 | Apagar linha da DRE pelo chat: hoje só dá para ocultar ou tirar do resultado | Thalisson disse que consegue colocar |
| 15 | Usuário da Luciana criado em Administração → Usuários e acessos (administradora) | Feito na reunião |

Arquivos novos no Drive: DRE teste (Excel com as macros do Power BI), custos fixos, apuração de PIS/COFINS, extratos bancários (NG e bancos), faturamento da prefeitura, dotações, combustível, locações e contas a pagar (NG e unidades).

## 2. Correções ao resumo do Gemini

- **Locadora**: é a **Vamos**. A Luyla só disse que é "como se fosse a Movida".
- **Endpoints mapeados**: são do **Zeev**, não do NG. Que o NG "tem API" foi só uma fala dela, não confirmada.
- **"Eric vai criar o usuário"**: o usuário já foi criado no mesmo dia (WhatsApp).
- **Nomes**: "Spel/Cipel" é a Sipel; "Ziv" é o Zeev.
- **Números de combustível**: "200, 300, 1000" ficou embaralhado. Os de Juazeiro do Norte (maio 100 mil → junho 326 mil) são mais confiáveis.

## 3. WhatsApp da tarde (23/10)

- O contato da **Keevo** (empresa do NG) era o comercial, não o técnico, e cobrou **R$ 7.500 só para iniciar** a integração. Luyla: "valor muito alto, acredito que não vão aprovar"; o caminho é conversar com o **Eric**, que integrou sem custo.
- O **financeiro não sai do NG** por enquanto: o NG é ligado à contabilidade, ao fiscal e à folha. Um sistema financeiro à parte "pode amadurecer" depois.
- Thalisson respondeu às 19h47–20h23: o acesso à Keevo e ao Núcleo Controller (o Zeev da Vale Norte) funcionou; perguntou onde fica o NG (se o Eric vai ajudar a instalar) e pediu a conversa com o Eric e o desenvolvedor dele.

## 4. Pendências

- Thalisson: entrar no NG (aguarda a orientação de instalação); responder sobre o financeiro continuar no NG; enviar o documento do padrão das unidades; analisar a integração com o Zeev; mapear as necessidades de frota; avaliar os arquivos novos do Drive; colocar o status da parcela no modelo de parcelamentos; apagar linha da DRE; montar a proposta por projeto.
- Luyla: nome da empresa do cartão de combustível; reunião com o Eric e o desenvolvedor dele; levantamento dos sistemas pagos; retorno do gestor sobre orçamento.
- Grupo: padronizar o fluxo da frota e as regras de aviso.
