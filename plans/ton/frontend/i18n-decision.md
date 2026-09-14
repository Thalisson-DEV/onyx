# TON — decisão de internacionalização

## Recomendação: A — preservar i18n internamente e publicar PT-BR primeiro

Use a arquitetura `next-intl` existente e mantenha o contrato de locale. TON pode
publicar uma experiência PT-BR por padrão e limitar a escolha visível de idioma, mas não
deve remover framework, catálogos ou chamadas de tradução nesta adaptação.

Este é o caminho de menor risco. Ele troca a copy de produto sem mudar rotas, renderização
server, integração Opal, preferência de idioma no backend ou pipeline de build.

A recomendação B (remover a infraestrutura i18n) não cabe no escopo atual. Ela transforma
uma migração de copy em migração ampla de runtime e tipos, sem benefício que compense o risco.

## Framework atual e contrato de dependências

| Tema | Evidência | Implicação |
|---|---|---|
| Dependência | `web/package.json` inclui `next-intl: ^4.13.7`. | O app atual já usa next-intl; não adicionar um segundo sistema de tradução. |
| Integração Next | `web/next.config.js` envolve o app com `createNextIntlPlugin` usando `./src/i18n/request.ts`. | Remover i18n mudaria a configuração de build do Next e o ciclo de requisição server. |
| Origem do locale | `web/src/i18n/config.ts` define `SUPPORTED_LOCALES` (`en`, `es`, `pt`, `fr`, `de`, `ja`, `zh`, `ko`, `ar`) e `DEFAULT_LOCALE = "en"`. | Não há segmento de URL `[locale]`. Locale é preferência em cookie/backend, portanto PT-BR-first não exige redesenho de rota. |
| Resolução de requisição | `web/src/i18n/request.ts` lê `NEXT_LOCALE`, importa `src/i18n/messages/${locale}.json` e sobrepõe o catálogo selecionado ao fallback inglês. | Manter fallback enquanto a cobertura PT-BR é completada. |
| Renderização raiz | `web/src/app/layout.tsx` chama `getLocale`/`getMessages`, define `<html lang dir>` e monta `NextIntlClientProvider`, `OpalStringsBridge` e `DirectionProvider`. | Locale afeta saída server/client, direção e labels Opal. Não pode ser substituído com segurança por poucos literais. |
| Preferência no backend | `web/src/i18n/config.ts` documenta `NEXT_LOCALE` como do backend; usa `PATCH /user/language` e `/me`. | Remover locale exige coordenar enum e idioma persistido no backend. Esta tarefa não altera backend. |
| Bridge Opal | `web/src/i18n/OpalStringsBridge.tsx` mapeia o namespace `opal` e números sensíveis a locale para o Opal. | Preservar o bridge. Quebrar strings Opal ao trocar traduções criaria controles em idiomas mistos. |
| Catálogos | `web/src/i18n/messages/{ar,de,en,es,fr,ja,ko,pt,zh}.json`; inglês é a fonte. `catalog.test.ts` importa os nove e valida ICU/placeholders; `keyParity.ts` valida paridade. | Manter todos os catálogos até projeto separado de retirada de locale, com métricas. |
| Build e tipagem | `web/package.json` executa `next build`, `next typegen` e o type-check próprio. `next.config.js` também usa `typedRoutes: true`. | Recomendação A não exige rota ou build novos. Rodar checks existentes após mudanças de copy. |

## Profundidade do uso atual

O comando de auditoria
`rg -l '(useTranslations|getTranslations|useFormatter|useLocale|NextIntl)' web/src
--glob '*.tsx' --glob '*.ts'` encontrou 516 arquivos. A contagem complementar de
`useTranslations(` e `getTranslations(` encontrou 738 usos. São contagens de snapshot,
não métricas de produto, mas mostram que i18n é uma dependência transversal.

As chamadas de tradução aparecem em auth, shell, settings, agentes, knowledge, UI de
anexos, admin, Craft, renderização de mensagens e componentes próximos ao Opal.
Datas/números sensíveis a locale também usam `useLocale`, `useFormatter` e `Intl`,
incluindo `web/src/i18n/numbers.ts` e testes. Não ter segmento de locale na URL não
significa que a localização seja superficial.

## Política de produto para TON PT-BR-first

1. Manter `pt.json` como catálogo PT-BR e continuar usando chaves em toda UI nova ou
   alterada. Não trocar chaves por literais em português.
2. Definir PT-BR como locale visível/padrão do deployment TON somente por decisão de
   configuração aprovada. Se houver seletor, ocultar opções não suportadas em vez de
   apagar catálogos.
3. Manter fallback inglês para chaves ausentes durante a auditoria PT-BR. Fallback é
   mais seguro que controle vazio ou mudança no markup server/client.
4. Preservar direção árabe e contrato raiz `lang`/`dir`, mesmo se o primeiro release
   TON expuser somente PT-BR. Isso evita regressão futura no Opal e no layout.
5. Revisar famílias de chaves SaaS em `en.json` e `pt.json` ao ocultar billing/cloud.
   Remover chaves é decisão separada, após conhecer o uso das rotas.

## Por que não B — remover i18n agora

Remover next-intl exigiria mudança coordenada na dependência, plugin Next, configuração
de request, provider raiz, chamadas de tradução server/client, strings Opal, formatação
sensível a locale, testes e preferência de idioma no backend. Também aumentaria o risco
de controles auth/admin sem tradução ou inconsistentes. Isso excede a adaptação de baixa
ou moderada diferença e não é necessário para criar uma nova rota.

## Gates de aceite para implementação posterior

* Nenhuma string nova visível sem chave nas superfícies TON alteradas.
* `catalog.test.ts`, paridade de chaves, validação ICU e checks TypeScript passam.
* Auth, shell, settings, picker, knowledge, gates admin e labels Opal renderizam PT-BR
  sem mudar formato de URL ou comportamento de auth server.
* Teste com `NEXT_LOCALE` e preferência persistida no backend confirma PT-BR e fallback
  inglês.
* Proposta separada antes de apagar catálogos ou mudar enum de idioma no backend. Esta
  auditoria não faz essa alteração.
