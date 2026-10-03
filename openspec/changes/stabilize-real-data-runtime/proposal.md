## Why

Desde 2026-10-02 o ambiente local roda com os dados reais da Vale Norte (jan–jun/2026), mas o
runtime acumulou dívidas que tornam o produto pouco confiável para uso fora de uma demonstração
roteirizada: alterações do backend aplicadas por `docker cp` (imagem `onyx-backend` não
reconstruída), imagem web não reconstruída, assistente levando 1,5–3 min por resposta e com
leitura incompleta do contexto financeiro (`financial_context` só olha os 10 cálculos mais
recentes por base), card do CFO dizendo "nenhuma DRE foi calculada" com DRE calculada, dotação
agrupada pelo nome do arquivo (o mesmo arquivo com "(1)" vira uma quarta dotação), e nenhuma
validação com um usuário cliente sem papel de admin. Nada novo deve ser construído sobre essa base
antes de ela ficar reprodutível.

## What Changes

- Reconstruir as imagens `onyx-backend` e `onyx-web-server` a partir do repositório, seguindo a
  subida sequencial (memória WSL), e eliminar a dependência de `docker cp`.
- Assistente: orçamento de latência explícito (meta proposta: p90 < 45 s e até 8 chamadas de
  ferramenta nas perguntas de referência — ajustável após a medição inicial), menos etapas por
  pergunta, contexto financeiro que enxerga todos os cálculos persistidos do escopo pedido, e testes
  de grounding sobre o banco real.
- Textos de especialistas e cards derivados do estado persistido (o CFO não pode negar uma DRE
  calculada).
- Identidade de dotação declarada (unidade + data-base da versão) e rejeição de conteúdo duplicado
  por hash, em vez de agrupamento por nome de arquivo.
- Validação ponta a ponta com um usuário do papel Controladoria sem admin.
- Limpeza do histórico de testes da preparação (conversas), sem apagar trilha de auditoria.

## Capabilities

### New Capabilities
<!-- nenhuma -->

### Modified Capabilities
- `ton-assistant`: requisitos de latência e de completude do contexto financeiro.
- `ton-product-experience`: cards de especialistas derivados de estado persistido; validação com papel cliente.
- `source-ingestion`: identidade de dotação declarada e deduplicação por hash.

## Impact

- `backend/onyx/db/ton/agent.py` (`financial_context`), `backend/onyx/prompts/ton/agent.py`,
  `backend/onyx/ton/agent/service.py`, `backend/onyx/db/ton/closing.py` (texto de especialistas).
- `backend/onyx/ton/client_import/service.py` e `operational_import` (identidade de dotação).
- Docker local (`deployment/docker_compose`), `plans/ton/local-runtime.md`.

## Dependências

- Nenhuma externa. Exige janela para rebuild com a stack parada.

## Estado de dado

Real (base local de 2026-10-02). Backup obrigatório antes de qualquer migração de dados.
