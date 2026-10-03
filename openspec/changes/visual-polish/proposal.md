## Why

Na reunião de 2026-10-03 o Thalisson disse que o polimento visual ainda não foi feito; ao abrir a
composição de uma linha da DRE, a gaveta é estreita (440 px), os valores quebram e os lançamentos
ficam pouco claros. Ele também quer tirar a cara de "vibe coding"/AI slop do produto antes de
mostrar de novo à Controladoria (segunda, 2026-10-05). A auditoria tela a tela (Chrome, 1440 px,
dados reais) mostrou que o problema vem principalmente da base visual, repetida em todas as telas:

- todo bloco é um cartão arredondado (14 px) com sombra suave; cartões "sobem" no hover;
- quadrado verde com ícone ao lado de quase todo título e de cada indicador;
- rótulos em maiúsculas ("eyebrow") em excesso; pílulas coloridas em toda linha;
- gradiente decorativo no topo da Visão Geral;
- cor de status errada: relatório "Concluído" aparece em laranja (tom de alerta);
- textos técnicos vazando (e-mail como autor, "run_id" nas limitações do CFO, códigos de unidade
  "000026" no lugar do nome);
- números de indicadores quebrando em duas linhas em espaços estreitos.

## What Changes

- **Base (tokens e componentes TON):** superfícies planas com borda fina e sem sombra; raio menor;
  sem "subir" no hover; ícone decorativo só onde ajuda a reconhecer algo; rótulos em maiúsculas só em
  cabeçalhos de tabela e grupos; pílula só para estado; cores de estado corretas; números sempre em
  uma linha com algarismos tabulares.
- **DRE:** gaveta de composição larga (até 960 px) com tabela de lançamentos (data, unidade pelo nome,
  conta do NG, documento, histórico, valor, origem planilha/linha), total da linha, origem do arquivo
  uma vez só; indicadores sem quebra.
- **Tela a tela:** Visão Geral, Fechamento, Pendências (e diálogo de decisão), Fontes (e janela de
  envio), Automações, Relatórios (e visualizador), Especialistas, Administração, Assistente.
- **Textos:** nomes no lugar de códigos e e-mails onde houver nome; nada técnico (run_id, enums).
- Renomes pedidos: "Escopo" → "Unidade/filial"; PROCUREMENT → "Compras/Suprimentos".

## Capabilities

### New Capabilities
- `ton-visual-system`: linguagem visual TON (superfícies, tipografia numérica, estados, densidade) e o padrão de gaveta de composição.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- `web/src/views/ton/shell/ton.css`, `web/src/views/ton/components/*`, todas as views em
  `web/src/views/ton/*`; backend: `DreContributorView` ganha `unit_name`, `source_account_code`,
  `source_account_label`, `description` (somente leitura) e ordenação por data.

## Dependências

- Nenhuma externa. Validação no Chrome em 1440/1024/390 px, claro e escuro.

## Estado de dado

Real.
