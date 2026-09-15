# TON — índice do planejamento frontend

## Escopo

Esta pasta contém uma auditoria somente de planejamento para adaptar o frontend Onyx ao
contexto de produto TON/Vale Norte. Registra decisões de rota, UX, arquitetura, copy,
i18n, tema, mobile, fronteira backend e implementação.

Este trabalho não modifica código de aplicação, backend, contratos API, dependências,
componentes do design system, tokens de tema, auth, comportamento de agentes ou assets de
logo. Os documentos orientam uma mudança futura com escopo separado.

Os documentos com prefixo numérico são exceção: eles registram a execução de um item
do backlog, não o planejamento. Hoje existe um, `004-ton-navigation.md`. Os resultados
de TON-FE-000 a TON-FE-003 estão em `implementation-roadmap.md`.

## Baseline

The initial audit snapshot had no tracked changes. The 18 Markdown files in
this directory were pre-existing untracked planning artifacts. No existing
change was reverted.

TON-FE-000 used execution baseline
`6e4b2a066459e3bd7217341b6f2fa5af4eb4bc4f`. The ignored Jest cache contains
stale TON experiment output, but no matching product source exists. The cache
does not affect the source baseline.

The frontend instructions in `web/AGENTS.md` and the Engineering Best Practices section
of `CONTRIBUTING.md` were read before documentation. The docs follow the repository
boundary: prefer Opal/refresh components, keep user text in next-intl, preserve
semantic tokens/dark mode/accessibility, and route backend calls through the frontend.

## Decisões executivas

1. Keep the Onyx application shell, chat, navigation, responsive behavior, dark mode,
   accessibility, authentication, connector infrastructure, and operator controls.
2. Hide ordinary client access to cloud signup, plans, billing, Stripe checkout,
   subscription/upgrade prompts, SaaS marketing, and upstream Onyx/community links.
   Keep private operator/licensing infrastructure only where deployment needs it.
3. Treat `/app` as the TON Central host. Map Agent/Project surfaces to specialists and
   cases only after TON concepts and permissions are defined.
4. Preserve i18n internally (Recommendation A). Ship PT-BR first at the product-policy
   level; do not remove `next-intl`, catalogs, Opal strings, or backend locale coupling.
5. Reuse existing file, project, and knowledge surfaces. Add explicit “conversation
   only” versus “persistent knowledge” scope after the backend retention contract is
   defined. Do not confuse optimistic `temp_<uuid>` IDs with temporary retention.
6. Defer palette, shadow, logo, and broad design-system changes. Use the existing Opal
   token seams for a later, explicit brand implementation.

## Ordem de leitura recomendada

1. [Análise de lacunas TON](./ton-gap-analysis.md) — escopo, limites e gaps principais.
2. [Arquitetura atual](./current-architecture.md) — composição frontend e limites de runtime.
3. [Inventário de rotas e telas](./route-screen-inventory.md) — decisão por rota.
4. [Auditoria SaaS](./saas-surface-audit.md) — decisões de cloud, billing, upgrade e links upstream.
5. [Inventário do design system](./design-system-inventory.md) — componentes e tokens aprovados.
6. [Plano de branding e tema](./branding-theme-plan.md) e [plano dark](./dark-theme-plan.md) — pontos visuais e limites.
7. [Decisão de i18n](./i18n-decision.md) — estratégia PT-BR-first e profundidade da migração.
8. [Plano UX de arquivos e knowledge](./files-knowledge-ux-plan.md) — semântica de escopo e retenção.
9. [Plano UX de achados](./findings-ux-plan.md) e [plano UX de relatórios](./reports-ux-plan.md) — superfícies de trabalho TON.
10. [Plano UX de agentes](./agents-ux-plan.md) — decisões sobre o host de especialistas.
11. [Auditoria mobile](./mobile-audit.md) — responsividade e limites de plataforma.
12. [Dependências de backend](./backend-dependencies.md) — limites que impedem claims inseguros.
13. [Riscos](./risks.md) — riscos transversais e mitigações.
14. [Roadmap de implementação](./implementation-roadmap.md) — ordem e verificação.
15. [Arquitetura de informação TON](./ton-information-architecture.md) — navegação e domínio.
16. [Navegação TON — execução de FE-004](./004-ton-navigation.md) — registro da
    arquitetura de informação implementada na sidebar.

## Matriz de entregáveis

| Documento | Pergunta principal | Saída de planejamento |
|---|---|---|
| [ton-gap-analysis.md](./ton-gap-analysis.md) | What is missing or uncertain for TON? | Scope, constraints, and gaps. |
| [current-architecture.md](./current-architecture.md) | Where do routes, providers, shells, and boundaries live? | Frontend architecture map. |
| [route-screen-inventory.md](./route-screen-inventory.md) | Which screens stay, hide, adapt, or need investigation? | Significant route classification and rationale. |
| [saas-surface-audit.md](./saas-surface-audit.md) | Where are cloud/SaaS/Onyx surfaces? | Hide/keep/review matrix with real paths. |
| [design-system-inventory.md](./design-system-inventory.md) | Which components and tokens are approved? | Opal, refresh, layout, and token guidance. |
| [branding-theme-plan.md](./branding-theme-plan.md) | Where can Vale Norte/TON branding enter later? | Brand seams and out-of-scope visual changes. |
| [dark-theme-plan.md](./dark-theme-plan.md) | How is dark mode preserved? | Existing class/token/runtime constraints. |
| [i18n-decision.md](./i18n-decision.md) | Should i18n remain? | Recommendation A, framework depth, and PT-BR policy. |
| [files-knowledge-ux-plan.md](./files-knowledge-ux-plan.md) | How should temporary and persistent files differ? | Reuse plan, scope labels, and backend questions. |
| [findings-ux-plan.md](./findings-ux-plan.md) | How can findings/occurrences fit the UI? | Existing-host and future-extension guidance. |
| [reports-ux-plan.md](./reports-ux-plan.md) | How can reports fit the UI? | Report workflow and route-host guidance. |
| [agents-ux-plan.md](./agents-ux-plan.md) | How do specialists map to Agents? | Agent/persona terminology and governance questions. |
| [mobile-audit.md](./mobile-audit.md) | What must remain aligned on mobile? | Web responsivo e restrições de plataforma. |
| [backend-dependencies.md](./backend-dependencies.md) | Which UX claims require backend work? | API, permission, persistence, and rollout boundaries. |
| [risks.md](./risks.md) | What can regress? | Risk register and mitigations. |
| [implementation-roadmap.md](./implementation-roadmap.md) | In what order should later work happen? | Phases, gates, and verification plan. |
| [ton-information-architecture.md](./ton-information-architecture.md) | What is the TON navigation/domain model? | Central, specialist, source, finding, and report IA. |
| [004-ton-navigation.md](./004-ton-navigation.md) | Which navigation did TON-FE-004 actually ship? | Executed IA, route map, decisions, checks, and the VIS-000 handoff. |

## Application-change confirmation

No application file was changed as part of this documentation handoff. The expected
implementation boundary remains the existing `web/` frontend, with no backend or API
implementation in this planning pass. Before implementation, reconcile open questions
in the route, SaaS, i18n, files, backend, and risk documents with product and backend
owners.

## Taxonomia canônica de mudança

Todos os documentos usam esta taxonomia. O nível descreve o impacto da mudança
frontend proposta, e não o esforço da descoberta ou do teste:

| Nível | Definição | Exemplo TON |
|---:|---|---|
| 0 | Somente texto, copy ou configuração | Rótulo, metadata ou link aprovado. |
| 1 | Ajuste de tema ou token | Mapeamento Vale Norte em light/dark. |
| 2 | Pequena composição de componentes ou variante | Item de navegação, modal ou variante Opal. |
| 3 | Nova página TON usando o design system existente | Lista/detalhe futuro de ocorrências ou relatórios. |
| 4 | Mudança estrutural de frontend | Nova casca, store ou fluxo que cruza áreas existentes. |
| 5 | Reescrita do design system ou da arquitetura | Substituição da arquitetura visual ou de frontend. |

TON deve preferir níveis 0–3. Qualquer nível 4 precisa de justificativa e
aprovação. Nível 5 é incompatível com esta adaptação.

## Matriz de cobertura dos 30 itens de descoberta

| # | Item exigido | Evidência principal |
|---:|---|---|
| 1 | Estrutura do app e router | `current-architecture.md`: mapa App Router e famílias de rota. |
| 2 | Layouts principais | `current-architecture.md`: mapa de runtime e shell. |
| 3 | Navegação | `current-architecture.md`: shell/nav/sidebar. |
| 4 | Sidebar | `current-architecture.md`: `AppSidebar` e `AdminSidebar`. |
| 5 | Páginas de chat | `current-architecture.md`: AppPage, ChatUI e sessões. |
| 6 | Composer | `current-architecture.md`: `AppInputBar` e `BaseInputBar`. |
| 7 | Histórico | `current-architecture.md`: recents, busca e sessões de projeto. |
| 8 | Agentes/personas | `agents-ux-plan.md` e inventário de rotas. |
| 9 | Projetos | `current-architecture.md` e `files-knowledge-ux-plan.md`. |
| 10 | Arquivos | `files-knowledge-ux-plan.md` e `mobile-audit.md`. |
| 11 | Documentos/conhecimento | `current-architecture.md` e inventário do design system. |
| 12 | Conectores/fontes | `backend-dependencies.md` e `saas-surface-audit.md`. |
| 13 | Administração | `route-screen-inventory.md` e `current-architecture.md`. |
| 14 | Configurações | `route-screen-inventory.md` e `current-architecture.md`. |
| 15 | Autenticação | `route-screen-inventory.md` e `current-architecture.md`. |
| 16 | Onboarding | `route-screen-inventory.md` e `current-architecture.md`. |
| 17 | SaaS/cloud/planos | `saas-surface-audit.md` e `route-screen-inventory.md`. |
| 18 | Arquitetura de tema | `design-system-inventory.md` e `branding-theme-plan.md`. |
| 19 | Tema escuro | `dark-theme-plan.md`. |
| 20 | Tipografia | `design-system-inventory.md`. |
| 21 | Espaçamento | `design-system-inventory.md`. |
| 22 | Radius | `design-system-inventory.md`. |
| 23 | Sombras/elevation | `design-system-inventory.md` e `dark-theme-plan.md`. |
| 24 | Componentes reutilizáveis | `design-system-inventory.md`. |
| 25 | Estratégia mobile/responsiva | `mobile-audit.md`. |
| 26 | i18n | `i18n-decision.md`. |
| 27 | Feature flags | `current-architecture.md` e `backend-dependencies.md`. |
| 28 | Fronteiras frontend EE | `current-architecture.md` e inventário de rotas. |
| 29 | Testes existentes | `mobile-audit.md` e `current-architecture.md`. |
| 30 | Ferramentas visual/e2e | `design-system-inventory.md` e `current-architecture.md`. |

## Relatório final do discovery

1. **Inspeção:** código frontend em `web/src`, Opal/refresh, tokens, rotas,
   testes, i18n, flags e contratos backend usados pelo frontend.
2. **Arquitetura:** Next.js App Router com layouts raiz, autenticação, app,
   administração e EE; `/app` hospeda o chat e o shell autenticado.
3. **Design system:** Opal é a autoridade; refresh compõe peças ainda não
   migradas; `src/components` é legado e não recebe novas dependências.
4. **Intocado:** chat, composer, sidebar, providers, auth, RBAC, APIs,
   conectores, filas, storage, migrações, dark mode e infraestrutura operacional.
5. **Mudança futura:** copy, tokens Vale Norte, navegação e pequenas extensões
   de UX, sempre no menor nível compatível.
6. **Saída do cliente:** cloud signup, planos, billing, Stripe, upgrade,
   upsell e links Onyx/comunidade sem destino TON aprovado.
7. **Gaps TON:** sem entidades/rotas dedicadas para ocorrências e relatórios;
   fontes agregadas e semântica de retenção de arquivos também exigem decisão.
8. **Backend:** contratos de ocorrência, evidência, relatório, retenção,
   ACL, histórico e exportação são dependências futuras. Telegram é o primeiro
   canal externo e espera o contrato do Backend 009.
9. **Riscos:** permissões, PII, CE/EE, SaaS por URL direta, i18n, dark,
   mobile, cache SWR e mistura de temporário com persistente.
10. **Ordem:** baseline, decisões de produto, copy, tokens, shell, chat,
    agentes/arquivos, admin, mobile, QA e rollout; contratos precedem novas telas.
11. **Documentação:** os 18 documentos desta pasta cobrem arquitetura, rotas,
    design system, marca, i18n, SaaS, UX, mobile, backend, riscos e roadmap.
12. **Confirmação:** a auditoria não alterou arquivos de aplicação, backend,
    APIs, dependências, tokens ou assets; somente documentos Markdown desta pasta
    são permitidos neste trabalho.
