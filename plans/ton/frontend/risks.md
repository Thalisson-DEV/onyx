# TON — riscos do plano frontend

Esta lista cobre riscos de adaptação, não mudanças a executar agora. O código
existente é a fonte de verdade. Cada mitigação deve ser localizada no backlog.

| ID | Risco e evidência | Impacto | Mitigação preservadora | Nível |
|---|---|---|---|---:|
| R-01 | A casca usa várias camadas. Evidência: `web/src/app/layout.tsx`, `web/src/app/app/layout.tsx`, `AppChrome.tsx` e `AppSidebar.tsx`. | Navegação duplicada, provider fora da ordem ou quebra de auth. | Manter os layouts e providers; tocar só composição e rótulos. | 3 |
| R-02 | Opal e legado coexistem. `web/AGENTS.md` exige `@opal/*` e `refresh-components`, mas `web/src/components/` ainda aparece em telas legadas. | Visual inconsistente, regressão de tokens e dívida involuntária. | Usar Opal em rotas TON novas; não migrar o legado inteiro. | 2 |
| R-03 | Há controles, ícones e cores fora do padrão em admin/legado, por exemplo `CCPairIndexingStatusTable.tsx`, `SettingsPage.tsx` e `web/src/components/*`. | Auditoria pode confundir dívida existente com escopo TON. | Registrar exceção; corrigir somente se a rota entrar no fluxo TON. | 1–2 |
| R-04 | `.dark` vem de tokens e `next-themes`, mas classes `dark:` são proibidas. | Contraste ruim ou tema incompleto. | Usar `semantic-light.json`, `semantic-dark.json` e tokens semânticos; testar ambos. | 2 |
| R-05 | Vale Norte não tem logo final. `useSettings` calcula `logoUrl` por enterprise settings. | Asset provisório pode virar contrato visual ou ficar cacheado. | Usar nome e tokens; manter fallback Onyx e deixar logo configurável. | 1 |
| R-06 | i18n tem infra completa e legado com strings diretas, incluindo `SettingsPage.tsx`. | Remover i18n gera churn; faltar chave quebra locale. | Aceitar português, adicionar chaves ao inglês e PT; manter bridge/locale. | 2 |
| R-07 | `AppSidebar` gerencia pins, DnD, agentes, projetos e chats. | Uma nova seção pode quebrar reorder, foco ou mobile. | Inserir destinos com o mesmo `SidebarLayouts`; não criar store paralelo. | 2–3 |
| R-08 | “Agent” frontend corresponde a “persona” backend. | Tentativa de criar sistema TON duplicado ou perda de permissões. | Mapear Central ao agente padrão e especialistas a personas; preservar APIs. | 2 |
| R-09 | `useActiveAgent` tem precedência de sessão/URL, default, pin e fallback. | URL TON pode selecionar agente inesperado ou perder contexto. | Testar cada precedência e fallback; não forçar id sem configuração. | 2 |
| R-10 | Compartilhamento de persona e arquivos tem ACL, grupos e proprietário. | Exposição de documento, prompt ou ferramenta. | Renderizar ações pelos campos de permissão; backend continua autoridade. | 3 |
| R-11 | Arquivo pode ser temporário, de projeto, recente ou ligado a agente. `ProjectFile` e `providers.tsx` têm estados distintos. | Retenção errada ou vazamento em recentes/citações. | Mostrar escopo e status; preservar `incognitoSessionId`; não inferir persistência. | 3 |
| R-12 | Não há modelo de ocorrência. Campos de knowledge graph em `backend/onyx/db/models.py` são contadores. | UI pode salvar negócio em dado técnico ou produzir falso histórico. | Bloquear tela real até schema, ACL, transições e API serem aprovados. | 3 |
| R-13 | Relatórios atuais são admin/EE. `UsageReports.tsx` e `QueryHistoryTable.tsx` têm gates e PII. | Usuário comum recebe 403, dado indevido ou falsa equivalência com TON. | Reusar somente padrão visual; criar contrato TON separado. | 3 |
| R-14 | `ADMIN_ROUTES` considera tier, assinatura, Craft, hooks, OpenSearch e query history. | Superfícies SaaS aparecem por URL direta ou configuração. | Matriz de visibilidade e gate server/client; não apenas ocultar sidebar. | 3 |
| R-15 | Auth e onboarding têm multi-tenant, SSO, senha e setup de LLM. | Redirecionamento quebrado ou primeiro usuário sem configuração. | Ajustar cópia e destino de forma incremental; manter fluxo auth. | 2 |
| R-16 | Tabelas e painéis têm comportamento diferente no mobile. | Ações inacessíveis ou overflow. | Reusar modal/drawer de `DocumentsSidebar` e toggles de `AppChrome`; testar 724/912px. | 2 |
| R-17 | Telegram está confirmado, mas o contrato backend do canal não existe. | Uma UI antecipada pode expor credenciais ou aplicar autorização somente no cliente. | Bloquear TON-FE-010 até o Backend 009 definir identidade, entrega, ACL e auditoria. | 3 |
| R-18 | APIs são consumidas pela mesma origem `/api`, com SWR e cache. | Fetch direto no backend, cache obsoleto ou estado duplicado. | Usar `SWR_KEYS`, fetcher existente, invalidação explícita e frontend como origem. | 2 |
| R-19 | Tipagem estrita e cobertura de tipos são requisitos de `web/AGENTS.md`. | Atalho com `any` esconde mudanças de contrato. | Tipar payloads, estados e handlers; rodar type coverage e testes afetados. | 2 |
| R-20 | Relatórios e ocorrências podem conter PII e conteúdo de fonte. | Exportação e histórico ampliam retenção e superfície de ataque. | Definir retenção, ACL, auditoria, URL temporária e redaction antes da UI. | 3 |

Os valores da coluna **Nível** estimam o impacto da mitigação futura e usam a
taxonomia canônica do `README.md`; eles não autorizam implementação. Um intervalo
indica que o nível depende da evidência e do contrato aprovado.

## Riscos de processo

- Descoberta pode ser confundida com implementação. Os documentos em
  `docs/ton/frontend/` são entregáveis; nenhum arquivo de `web/` ou `backend/`
  foi alterado.
- Um refactor de design system durante a adaptação elevaria o risco. A regra é
  corrigir apenas a rota tocada e manter o restante.
- Um contrato proposto neste plano não é um endpoint existente. Marcar sempre
  propostas como futuras e obter decisão antes de codificar.

O nível 4 de `R-17` descreve somente o risco de uma futura integração externa.
Não é uma autorização de implementação. Nenhuma atividade TON aceita nível 5.
