## Why

Hoje o chat do TON só lê e analisa. Das 21 ferramentas, 20 são de leitura; a única escrita é o
rascunho de automação. Para corrigir a DRE, a Controladoria sai do chat e usa Fontes, Classificação,
Pendências, Tratamentos e a estrutura da DRE, tela por tela.

Em 2026-10-20 a Luyla pediu (WhatsApp):

- "incluir o faturamento bruto e o imposto sobre faturamento [na DRE], conforme o Power BI";
- "uma alternativa da gente mesmo ir ajustando no chat";
- "no chat a gente ter mais opções de trabalhar e inclusive conseguir enviar as correções que
  enviarmos pela fonte".

Em 2026-10-21 o Thalisson pediu também um chat próprio para cada especialista, com foco exclusivo no
que aquele especialista pode fazer.

Os serviços de escrita já existem e já são auditados (tratamentos de fechamento, versões da
estrutura da DRE, classificação de contas, decisões de pendência, atribuição de unidade, importação
de fontes, cálculo da DRE, automações). O chat não os usa.

## What Changes

O chat passa de "analista" para "agente da Controladoria": ele lê, propõe, mostra o efeito antes e,
com o clique da pessoa, aplica.

1. **Ações com confirmação (fundação).** Toda escrita pelo chat é uma *proposta de ação*: o agente
   monta o pedido, o backend valida, calcula o antes × depois e grava a proposta. O chat mostra um
   cartão com o efeito e os botões **Aplicar** e **Cancelar**. Só o clique da pessoa aplica, com as
   permissões dela, pelo mesmo serviço que a tela usa. A auditoria registra a origem "chat" e a
   conversa. Quando o serviço é versionado, o cartão aplicado oferece **Desfazer**.
2. **Faturamento bruto e impostos na DRE (pedido da Luyla).** Novas origens de linha na estrutura
   da DRE, além das contas do NG:
   - **Faturamento bruto** a partir da fonte de faturamento (valor do serviço da nota);
   - **Impostos sobre faturamento** a partir da mesma fonte (ISS da nota) e, quando importada, da
     planilha de cálculo de PIS/COFINS da Luyla;
   - **Ajuste da Controladoria**: valor informado por mês e unidade, com justificativa e versão.
   O agente monta a mudança de estrutura ("abrir a receita em bruta − impostos = líquida") e mostra
   a DRE antes × depois antes de aplicar.
3. **Correções por arquivo no chat.** A pessoa anexa o Excel corrigido na conversa. O agente
   reconhece a fonte, mostra a prévia da importação (linhas, diagnósticos, o que muda) e importa e
   recalcula após o clique.
4. **Mais ações pelo chat, reaproveitando os serviços existentes.** Decidir pendência, atribuir
   unidade, classificar contas em lote, criar e versionar tratamento, decidir item de conciliação,
   recalcular a DRE (mês ou ano), exportar o Excel da DRE, ativar ou rodar automação, publicar
   relatório. Novas leituras: lançamentos de uma linha da DRE, busca de lançamentos (fornecedor,
   documento, valor), comparação entre meses e unidades.
5. **Chat por especialista.** Cada especialista (CFO, AUDITOR, CEO e os demais quando suas fontes
   chegarem) ganha uma conversa própria em `/ton/especialistas/{chave}`, com prompt, ferramentas e
   sugestões iniciais só do seu domínio. O chat geral do TON continua com todas as ferramentas e
   pode indicar o especialista certo. Especialista sem fonte abre a conversa dizendo o que falta
   para atuar e usa só leituras.
6. **Experiência do chat.**
   - cartão de ação com antes × depois e Aplicar / Cancelar / Desfazer;
   - período e unidade fixados na conversa (seletor no campo de mensagem), para o agente não
     perguntar de novo;
   - tabela da DRE na resposta, com clique na linha para ver os lançamentos;
   - sugestões de próximo passo depois de cada resposta;
   - "O que o TON alterou nesta conversa": lista das ações aplicadas, com Desfazer;
   - anexar arquivo arrastando para a conversa.
7. **Regras da Controladoria lembradas.** Quando a pessoa diz uma regra ("a receita é sempre
   bruta", "parcelamento fica fora do resultado"), o agente propõe gravá-la. Regras gravadas entram
   no contexto de todas as conversas e aparecem numa lista editável.

## Capabilities

### New Capabilities
- `ton-agent-actions`: propostas de ação, confirmação, aplicação, desfazer e auditoria pelo chat.
- `ton-specialist-chat`: conversa própria por especialista.

### Modified Capabilities
- `ton-assistant`: ferramentas de ação, anexos, contexto fixado, cartões, regras lembradas.
- `ton-dre`: origens de linha "faturamento bruto", "impostos sobre faturamento" e "ajuste da
  Controladoria".

## Impact

- Backend: `onyx/tools/tool_implementations/ton/` (ferramentas de proposta e novas leituras),
  `onyx/ton/agent/` (serviço de ações, especialistas), `onyx/db/ton/` (tabela de propostas, regras
  lembradas), `onyx/ton/dre/engine.py` (novas origens de linha), `onyx/server/ton/agent.py`
  (aplicar, cancelar, desfazer), prompt do TON e prompts dos especialistas, uma migração Alembic.
- Frontend: `web/src/views/ton/chat/*` (cartão de ação, contexto fixado, tabela da DRE),
  `TonToolCard`, `/ton/especialistas/[key]`.
- Sem escrita no NG/Keevo. Sem aplicação automática: toda escrita depende do clique.

## Dependências

- Definição de "imposto sobre faturamento" no Power BI da Luyla: ISS da nota, PIS/COFINS da
  planilha dela, ou os dois. A origem por fonte fica configurável; o ajuste manual cobre o intervalo.
- Planilha de cálculo de PIS/COFINS (change `pis-cofins-source`) para a parte automática do PIS/COFINS.
- Relaciona-se com `specialist-subagents` (contrato de especialista) e `assistant-transparency`
  (painel de trabalho), que continuam válidos.
