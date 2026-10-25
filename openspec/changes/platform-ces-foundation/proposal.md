## Why

Na reunião de 2026-10-23 o Thalisson mostrou o CES, o sistema interno que ele desenvolve para a
Sipel desde janeiro. A Luyla gostou do layout ("muito simples"), da linha do tempo de alterações
(quem pediu, quem aprovou, o que mudou, quem entregou) e do assistente como analista em cada gráfico.
Ela disse que a Vale Norte precisa "basicamente desse mesmo controle": frota, almoxarifado (há
empresas de construção civil no grupo), solicitações financeiras centralizadas, chamados (hoje no
Zeev) e, no futuro, migrar o BPM do Zeev para um "sistema próprio da Vale Norte" e deixar de pagar
sistemas terceiros. Ela vai levantar os sistemas pagos (frota, rastreamento, ponto, BPM,
almoxarifado) para mostrar a economia.

No mesmo dia o Thalisson decidiu que o melhor cenário é o TON ficar parecido com o CES. Ele tem
autorização explícita da Sipel para usar o código do CES, mas quer usá-lo só como base (arquitetura,
padrões, módulos), não como cópia. Também quer limpar do fork tudo o que o TON não usa do Onyx.

Hoje o TON é um fork do Onyx (Python/FastAPI + Next.js) com o produto em `onyx/ton` e `web/src/app/ton`.
O CES usa outra stack (Java/Spring + Angular + PWA, repositório em `~/Documents/ces`).

## What Changes

- **Decisão de stack** registrada antes de qualquer migração: (a) manter o fork Onyx limpo e trazer
  os padrões do CES para Python/Next.js; (b) migrar o TON para a stack do CES; (c) outra. Critérios:
  o que já existe no TON (DRE, fontes, agente, automações), custo de migração, manutenção, app no
  celular, quem mantém.
- **Inventário do Onyx**: o que o TON usa (auth, RBAC, chat/streaming, providers, ferramentas, Code
  Interpreter, Celery, file store) e o que pode sair (conectores, busca/indexação, Vespa, telas
  genéricas, marcas do Onyx), com plano de remoção que não quebre o TON.
- **Base de plataforma modular** inspirada no CES:
  - histórico de alterações em todo registro (linha do tempo: quem criou, aprovou, alterou, entregou);
  - solicitações com aprovação (combustível, pagamento, material) e fila por responsável;
  - comunicados da Controladoria (modal/notificação, com imagem, PDF e vídeo);
  - chamados internos e acompanhamento de tarefas por colaborador (prazo, atraso, volume);
  - app no celular (PWA) para gestores e equipes de campo;
  - assistente com contexto do gráfico ou registro clicado.
- **Módulos candidatos** em ordem a definir com a Luyla: frota (`fleet-fuel-domain`), contas a pagar
  das unidades (`unit-payables-intake`), almoxarifado/estoque, solicitações financeiras, chamados e
  BPM (substituição do Zeev), comunicados, DP (descontos, ponto, sanções, folha), segurança do
  trabalho (CIPA, acidentes, inspeções).
- Identidade visual do TON (sem marca do Onyx nem da Sipel).

## Capabilities

### New Capabilities
- `platform-foundation`: decisão de stack, limpeza do fork, histórico de alterações, solicitações com
  aprovação, comunicados, chamados, PWA e contexto do assistente por tela.

### Modified Capabilities
<!-- `ton-product-experience` (navegação por módulos) entra como delta quando a stack for decidida -->

## Achados que este padrão precisa resolver (análise de 2026-10-23)

- Controles em Excel editáveis por qualquer um, sem histórico de quem mudou nome ou valor (combustível
  e frota; dito pela Luyla e pela Luciana).
- Aprovações feitas fora do sistema, por WhatsApp (a Luyla já viu isso acontecer mesmo com o Zeev).
- Informação que "morre" no meio da cadeia de avisos (gestor → diretoria operacional → frota →
  financeiro).

## Impact

- Potencialmente todo o repositório (decisão de stack); remoção de partes do Onyx; novo shell modular.

**Decisão de 2026-10-24:** fork Onyx limpo, sem mudar a stack agora. Os padrões e módulos do CES
são reimplementados em Python/Next.js dentro do TON.

## Dependências

- ~~Decisão de stack~~ — decidida em 2026-10-24 (Onyx limpo).
- Autorização da Sipel por escrito (guardar) e definição de quem é dono do código do TON.
- Levantamento dos sistemas pagos pela Luyla e prioridade dos módulos.
- Modelo comercial por projeto (fases com preço fixo) aprovado pelo gestor da Vale Norte.

## Estado de dado

Sem dado novo; reaproveita os dados reais já no TON.
