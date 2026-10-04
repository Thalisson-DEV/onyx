## Why

Em 2026-10-03 o Thalisson disse que o assistente "esconde" o que faz e que o chat tem pouca
experiência. A auditoria no Chrome (base real, conversa "Fechamento Junho/2026") mostrou:

- o cabeçalho dizia só "Executado em 2m 4s · 24 etapas";
- cada fase de raciocínio aparecia como "Processado", sem conteúdo. O texto do modelo existe,
  mas está em inglês e cita nomes de ferramenta e `run_id`, então não pode ir para a tela
  (TON-VIS-006);
- as consultas paralelas apareciam em abas com nomes técnicos, "11 registros retornados" e
  "Ver dados técnicos (JSON)";
- a resposta não mostrava as fontes;
- o ícone do TON era um "T" cinza de 24 px;
- dois cartões "Situação da DRE" de períodos diferentes pareciam contraditórios, porque nenhum
  dizia o período;
- a parada pelo usuário aparecia em inglês ("The generation was stopped by the user.").

## What Changes

- **Painel de trabalho** (substitui a timeline do Onyx nas rotas `/ton`): marca TON animada
  enquanto trabalha, frase do que está fazendo agora, cronômetro e as etapas ao vivo. Cada
  consulta diz o que leu, com período/unidade pelo nome e um resumo do resultado. Depois da
  resposta, o painel vira uma linha: "Trabalhou por 30 s · 4 consultas · 3 especialistas".
- **Raciocínio**: as fases recebem nome pela posição ("Entendeu a pergunta e planejou as
  consultas", "Analisou o que encontrou", "Organizou a resposta"). O texto privado do modelo
  continua fora da tela.
- **Dados lidos**: "Ver o que foi lido" mostra tabela ou campos com rótulos em português, R$,
  datas e períodos. IDs, hashes e versões ficam ocultos. O JSON bruto fica só como "Copiar dados
  brutos", para administrador.
- **Abaixo da resposta**: os cartões que pedem ação ficam visíveis (relatório publicado,
  evidência com linhas, DRE com bloqueio). Fontes, especialistas e os demais resultados ficam
  recolhidos numa barra ("Fontes · 7", "Especialistas · 3", "Resultados · 2").
- **Fontes**: os chips por tipo de dado levam à tela que mostra o mesmo dado. A seção "De onde
  vêm os dados" mostra o arquivo importado, a data e a forma de aquisição.
- **Especialistas**: ícone no estilo de agente do Onyx para cada um. O quadro mostra quem
  atuou, a faixa das 7 etapas do protocolo, o motivo de cada etapa não executada e o que
  recomenda. Os especialistas que aguardam fonte aparecem esmaecidos.
- **Cartões**: período e escopo no subtítulo; um cartão por período (o mais recente vence);
  estado "Nada impede a publicação neste período".
- **Texto da resposta**: as seções escritas pelo prompt ("SITUAÇÃO", "EVIDÊNCIA") viram rótulos
  discretos. Os separadores `---` ficam ocultos.
- O aviso de parada do backend é mostrado no idioma do leitor.

## Capabilities

### Modified Capabilities
- `ton-assistant`: transparência do trabalho, fontes e especialistas na conversa.

## Impact

- Novo: `web/src/views/ton/chat/*` (painel, fontes, especialistas, marca, visualização de
  dados, CSS), `web/src/lib/ton/{work-log,data-preview,chat-tools,specialists}.ts`, quatro
  ícones pequenos no Opal (`cart-small`, `shield-small`, `truck-small`, `users-small`).
- Alterado: `AgentMessage` (painel TON só em `/ton`), `TonExecutionSummary`, `TonToolCard`,
  `MessageTextRenderer` (aviso de parada), `SpecialistAvatar` (`iconScale` opcional),
  `lib/ton/{copy,api}.ts`.
- Sem mudança de backend.

## Dependências

- Nenhuma externa.

## Estado de dado

Real (validado no Chrome com conversas reais da base Vale Norte). Testes só com dado sintético.
