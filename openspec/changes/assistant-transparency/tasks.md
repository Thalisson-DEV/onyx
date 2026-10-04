## 1. Modelo

- [x] 1.1 `work-log.ts`: pacotes → etapas, consultas (assunto, resumo), especialistas, fontes, origens; sem texto privado do modelo
- [x] 1.2 `data-preview.ts`: dados lidos em tabela/campos com rótulos pt-BR; IDs e hashes ocultos
- [x] 1.3 `chat-tools.ts` (frase, rótulo, página, ícone por ferramenta) e `specialists.ts` (identidade)
- [x] 1.4 Testes determinísticos com dado sintético (`work-log.test.ts`, 6 casos)

## 2. Interface

- [x] 2.1 Marca TON (anel dourado enquanto trabalha) e avatar de especialista no estilo Onyx; 4 ícones pequenos no Opal
- [x] 2.2 Painel de trabalho ao vivo, recolhido depois da resposta; "Ver o que foi lido"; copiar dados brutos só para administrador
- [x] 2.3 Barra de detalhes recolhida (Fontes, Especialistas, Resultados); cartões que pedem ação continuam visíveis
- [x] 2.4 Cartões com período/escopo, um por período; DRE sem bloqueio diz isso
- [x] 2.5 Seções da resposta como rótulos; aviso de parada traduzido
- [x] 2.6 Microinterações (entrada das etapas, check, progresso, chips) com `prefers-reduced-motion`

## 3. Validação

- [x] 3.1 tsc, oxlint sem erro novo, jest TON + chat (451/451)
- [x] 3.2 Chrome 1440 claro e escuro: conversa real antiga e pergunta nova ao vivo
- [x] 3.3 Chrome 390 px (o redimensionamento da janela não funcionou na sessão)
- [ ] 3.4 Reconstruir a imagem do web server para a porta 3000
- [x] 3.5 Atualizar `openspec/roadmap.md` e a decisão D-033

## 4. Próximos passos (fora deste escopo)

- [ ] 4.1 Saída do Python com acentos quebrados ("L�quida") no Code Interpreter
- [ ] 4.2 Citações no texto ligadas às fontes (exige mudança no prompt)
