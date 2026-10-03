## 1. Base visual

- [x] 1.1 Tokens: superfície plana, borda fina, sem sombra, raio menor, sem hover lift, sem gradiente decorativo
- [x] 1.2 Componentes: Metric sem quebra para valores numéricos, ícones em contorno (sem quadrado verde preenchido), pílulas com raio menor
- [x] 1.3 Tom de status de execução/relatório correto (`runTone`: Concluído = sucesso)
- [ ] 1.4 Revisar o restante dos usos de IconTile/eyebrow tela a tela (manter só onde informa)

## 2. DRE

- [x] 2.1 Backend: contribuintes com nome da unidade, conta do NG, histórico; ordem por data
- [x] 2.2 Gaveta larga com tabela de lançamentos, valores sem quebra, origem do arquivo uma vez
- [x] 2.3 Renome "Escopo" → "Unidade/filial"; cabeçalho "Linha" alinhado
- [ ] 2.4 Carregamento da DRE (~15 s na base real): investigar e reduzir

## 3. Telas

- [x] 3.1 Visão Geral: hero sem gradiente, indicadores sem quadrado de ícone, relatórios com status correto, autor pelo nome
- [x] 3.2 Fechamento: achados mostram a situação real (ex.: "Risco aceito") e planilha/linha
- [ ] 3.3 Pendências e diálogo de decisão (sem pendências na base atual; revisar com dado de teste)
- [ ] 3.4 Fontes e janela de envio (indicador de integração direta ok; revisar janela)
- [x] 3.5 Automações (status Concluído em verde)
- [x] 3.6 Relatórios (status correto); [ ] visualizador
- [x] 3.7 Especialistas: sem "run_id"; PROCUREMENT → "Compras/Suprimentos"
- [ ] 3.8 Administração do TON (corrigir erro de lint `useDecisionLog` condicional, pré-existente)
- [x] 3.9 Assistente: cabeçalho sóbrio (sem brilho/dourado), trilho lateral sem cortar nomes; [ ] ponto de status das fontes no trilho

## 4. Validação

- [x] 4.1 tsc e jest TON (22/22); oxlint sem erros novos
- [~] 4.2 Chrome 1440 claro e escuro (DRE, Visão Geral, Fechamento, Fontes, Automações, Relatórios, Especialistas, Administração, Assistente); falta 1024/390
- [ ] 4.3 Aplicado no backend por cópia no contêiner; reconstruir imagens (`stabilize-real-data-runtime`)
- [ ] 4.4 Atualizar `openspec/roadmap.md`
