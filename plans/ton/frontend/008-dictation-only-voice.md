# TON-VIS-008 — Voz Apenas por Ditado (Ditado Nativo no Navegador)

Documento de fechamento e especificação técnica da fatia **TON-VIS-008**.
Companheiro de [`000-de-onyx-visual-audit.md`](./000-de-onyx-visual-audit.md), [`visual-language.md`](./visual-language.md) e [`visual-implementation-roadmap.md`](./visual-implementation-roadmap.md).

**Estado: DONE (Atualizado com a correção de produto para ditado nativo sem provedor STT externo).**

---

## 1. Decisão de Produto e Correção de Arquitetura

### 1.1 Problema Original (Upstream)
Na arquitetura upstream da Onyx:
1. A voz operava em modo conversacional bidirecional contínuo com síntese de fala (TTS) assistiva.
2. `autoSend` submetia a mensagem automaticamente ao detectar silêncio.
3. A resposta do assistente tocava áudio via TTS em streaming (`autoPlayback`).
4. Ao término do áudio, `autoListen` religava o microfone automaticamente.
5. Uma animação circular de waveform cobria o campo de entrada (`speakingPlaceholder`).
6. Cada mensagem continha um botão `TTSButton`.
7. As configurações do usuário e administrativas continham blocos complexos de TTS e STT.

### 1.2 Correção de Produto TON (Ditado Nativo no Navegador)
A experiência desejada para o produto TON é **ditado puro e direto**:
```
microfone
  → reconhecimento de voz nativo do navegador (SpeechRecognition / webkitSpeechRecognition)
  → texto inserido no composer
  → revisão/edição pelo usuário
  → envio manual
```
- **Zero configuração externa para o usuário**: O cliente NÃO precisa configurar provedores como Whisper, Azure Speech ou ElevenLabs para utilizar o microfone no navegador.
- **Sem fala assistiva (TTS)**: O assistente responde apenas por texto.
- **Sem envio automático (`autoSend = false`)**: O texto reconhecido entra no editor e aguarda a submissão voluntária do usuário.
- **Sem reativação automática (`autoListen = false`)**: O microfone desliga ao parar e nunca religa sozinho.
- **Navegadores não suportados**: Comportamento gracioso de capacidade — o botão do microfone permanece desabilitado com tooltip claro e acessível indicando que o ditado não está disponível no navegador atual, sem exigir ação administrativa do usuário.
- **Superfície administrativa limpa**: A rota de configuração de voz é ocultada do menu lateral do painel de administração (`ADMIN_ROUTES.VOICE.visibleWhen = false`, `NAV_ITEM_IDS.VOICE = null`).
- **Infraestrutura de servidor preservada internamente**: O pipeline STT de servidor (`VoiceRecorderSession`, WebSocket `/api/voice/transcribe/stream`, modelos Whisper/Azure) permanece intacto para eventuais usos internos ou integrações futuras.

---

## 2. Acoplamentos Críticos e Invariantes Preservados

| Contrato | Arquivo / Ponto | Decisão Técnica |
|---|---|---|
| Reconhecimento de fala | `web/src/hooks/useBrowserDictation.ts` | Hook cliente implementando `window.SpeechRecognition \|\| window.webkitSpeechRecognition`. Suporta resultados contínuos e interinos, unmount cleanup e recuperação de erros. |
| Idioma da transcrição | `web/src/sections/input/MicrophoneButton.tsx` | Mapeia a localidade do `next-intl` (`pt` → `pt-BR`, etc.) para o parâmetro `lang` do `SpeechRecognition`. |
| Comportamento do composer | `web/src/sections/input/AppInputBar.tsx` | Sem portão de `sttEnabled` ou `isAdmin`. Microfone acessível diretamente; texto anexado a `currentMessage` sem apagar texto anterior; envio manual para a gravação. |
| Indicador de ditado | `web/src/components/voice/Waveform.tsx` | Quando `audioLevel <= 0` (ditado do navegador sem pipeline de microfone concorrente), renderiza indicador honesto de estado (ponto ativo de gravação + texto "Ditando..." + cronômetro decorrido), sem barras artificiais. |
| Navegadores sem suporte | `MicrophoneButton.tsx` + 9 catálogos i18n | Botão desabilitado com tooltip `Ditado não disponível neste navegador.` nos 9 idiomas suportados (`pt`, `en`, `es`, `fr`, `de`, `zh`, `ja`, `ko`, `ar`). |
| Ocultamento do admin | `admin-routes.ts`, `admin-sidebar-utils.ts` | Rota `/admin/voice` com `sidebarLabel: ""` e `visibleWhen: (_flags) => false`, `NAV_ITEM_IDS.VOICE = null`. Não aparece no menu do administrador. |
| Infraestrutura STT servidor | `VoiceRecorderSession.ts`, rotas FastAPI | Preservadas internamente sem remoções destrutivas. |

---

## 3. Resumo das Alterações por Superfície

### 3.1 `useBrowserDictation.ts` (Novo Hook)
- Adapter para Web Speech API (`SpeechRecognition` e `webkitSpeechRecognition`);
- Controle do ciclo de vida: `startDictation`, `stopDictation`, `resetError`;
- Suporte a resultados interinos (`onInterimTranscript`) e finais (`onFinalTranscript`);
- Limpeza segura ao desmontar ou navegar;
- Tratamento gracioso de erros de permissão (`not-allowed`) e dispositivos ausentes.

### 3.2 `MicrophoneButton.tsx`
- Migrado para `useBrowserDictation`;
- Suporte a fallback gracioso quando o navegador não suporta `SpeechRecognition` (renderiza botão desabilitado com tooltip traduzido);
- Elimina dependências de estados obsoletos de TTS;
- Mapeia a localidade ativa para idiomas de reconhecimento (padrão `pt-BR`).

### 3.3 `AppInputBar.tsx`
- Removido portão de `sttEnabled` e verificação `isAdmin` para exibição do microfone;
- Renderiza `<MicrophoneButton>` diretamente na barra de ações;
- Mantém o cancelamento da gravação (`stopRecordingRef.current?.()`) ao acionar o envio manual;
- Preserva todas as funcionalidades existentes do composer (anexos, modelos, Deep Research, parada, rascunhos).

### 3.4 `Waveform.tsx`
- Exibe indicador honesto de gravação (`Ditando...` com ponto pulsante e cronômetro) durante o ditado no navegador;
- Evita inicialização paralela de `getUserMedia` que causaria concorrência e bloqueios de áudio no Windows/Chrome.

### 3.5 Navegação Administrativa (`admin-routes.ts`, `admin-sidebar-utils.ts`)
- `ADMIN_ROUTES.VOICE.visibleWhen = (_flags) => false`;
- `ADMIN_ROUTES.VOICE.sidebarLabel = ""`;
- `NAV_ITEM_IDS.VOICE = null`;
- Voz completamente removida da barra lateral de administração normal.

### 3.6 Catálogos de Internacionalização (9 Idiomas)
- Adicionadas chaves `chat.input.waveform.dictating`;
- Adicionadas chaves `chat.input.microphoneButton.unsupported.ariaLabel` e `chat.input.microphoneButton.unsupported.tooltip`;
- Atualizada a cópia de `appInputBar.voiceSetupButton.tooltip` em todos os 9 idiomas (`pt`, `en`, `es`, `fr`, `de`, `ja`, `zh`, `ko`, `ar`).

---

## 4. Testes e Verificação

A suíte `web/src/sections/input/__tests__/ton-vis-008-voice-dictation.test.tsx` cobre 22 contratos essenciais:

1. Navegador suportado possui microfone disponível sem provedor STT configurado;
2. Ausência de requisito `stt_enabled` no fluxo nativo do `AppInputBar`;
3. Ausência de tooltip de configuração de provedor em navegador suportado;
4. Reconhecimento inicia sob clique explícito no botão do microfone;
5. Resultados interinos atualizam a transcrição sem submissão automática;
6. Transcrição entra no composer via `onTranscription`;
7. Texto permanece editável no composer antes do envio;
8. Transcrição nunca envia automaticamente;
9. Envio manual funciona e encerra a gravação de forma limpa;
10. Clique no microfone durante a gravação encerra o reconhecimento;
11. Desmontagem encerra o reconhecimento com segurança;
12. Erro de permissão recupera de forma limpa sem crash;
13. Navegador sem suporte renderiza botão desabilitado com tooltip claro;
14. Tooltip de navegador sem suporte não menciona Whisper, Azure nem configuração de admin;
15. Botão de TTS e reprodução permanecem ausentes;
16. `autoSend` permanece estritamente `false`;
17. `autoListen` permanece estritamente `false`;
18. `MessageToolbar` permanece sem TTS;
19. Contratos de estilo de Waveform e globals CSS permanecem íntegros;
20. Página de voz do admin está oculta da barra lateral voltada ao usuário comum;
21. Infraestrutura STT de servidor retida permanece intacta internamente;
22. Paridade completa mantida entre os 9 catálogos de internacionalização.

### Resultados dos Portões de Qualidade
- `bun run test ton-vis-008-voice-dictation`: **22/22 PASS**
- `bun run test catalog composerVisualContract messageVisualContract`: **56/56 PASS**
- `oxlint` nos arquivos modificados e criados: **0 erros, 0 avisos**
- `git diff --check`: **0 erros de formatação**
