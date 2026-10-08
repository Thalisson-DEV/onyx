## 1. Motor

- [x] 1.1 Definição v3, tipos de automação, catálogo de nós (registro extensível)
- [x] 1.2 Expressões e condições (parser próprio, funções seguras)
- [x] 1.3 Verificador: erros e avisos por nó, problemas de ativação por tipo
- [x] 1.4 Interpretador durável: replay, run after, retry, escopo, paralelo, para cada, repetir até, esperar, aprovação, encerrar
- [x] 1.5 Modelos e migração: automação, versão, execução, etapa, aprovação, aviso, arquivo
- [x] 1.6 Fila: tarefa de execução com lease, tick (eventos, recorrência, retomada, recuperação, tempo limite)
- [x] 1.7 Testes determinísticos do interpretador, das expressões e do verificador

## 2. Nós

- [x] 2.1 Gatilhos: manual, recorrência, importação NG, inconsistência mudou, conta sem classificação, DRE recalculada, falha de automação
- [x] 2.2 E-mail (compositor e transporte atuais, expressões e blocos com fonte de dados)
- [x] 2.3 TON: inconsistências, contas sem classificação, notificação no sino
- [x] 2.4 Dados: inserir dados (texto, JSON, CSV, arquivo), compor, JSON, filtrar, selecionar, ordenar, agrupar, agregar, tabela HTML, juntar
- [x] 2.5 IA: prompt (texto ou campos), extrair, classificar, resumir
- [x] 2.6 HTTP de saída com proteção de rede
- [x] 2.7 Variáveis: definir, incrementar, anexar

## 3. Migração dos fluxos de e-mail

- [x] 3.1 Converter definições v1/v2 em v3 (tipo EMAIL) e parar o motor v2
- [x] 3.2 `/ton/fluxos` aponta para `/ton/automacoes`

## 4. Chat

- [x] 4.1 `ton_draft_automation` com o catálogo v3; cartão no chat
- [x] 4.2 "Pedir ao TON" dentro do designer (ajusta o rascunho aberto)

## 5. Telas

- [x] 5.1 Lista em tabela, filtro por tipo, aprovações pendentes, nova automação (em branco, modelo, chat)
- [x] 5.2 Detalhe: dados, histórico de execuções, ativar/pausar, executar
- [x] 5.3 Designer: canvas vertical, adicionar ação, arrastar e soltar, painel de configuração, conteúdo dinâmico, verificador ao vivo, desfazer/refazer, testar, salvar
- [x] 5.4 Execução no canvas: estado e duração por etapa, entradas/saídas, reenviar, cancelar
- [ ] 5.5 Validação no navegador (Chrome) com dado real

## 6. Fechamento

- [x] 6.1 Atualizar `openspec/roadmap.md` e `plans/ton/context`
