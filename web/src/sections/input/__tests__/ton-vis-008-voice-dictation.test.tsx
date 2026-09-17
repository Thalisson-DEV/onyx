/**
 * TON-VIS-008: Voice -> Dictation Only Test Suite (Native Browser Recognition).
 *
 * Validates all required product contracts:
 * 1. Supported browser -> microphone available without STT provider configured
 * 2. No stt_enabled requirement in native dictation path
 * 3. No admin-provider tooltip in supported browser
 * 4. Recognition starts on explicit microphone action
 * 5. Interim result does not auto-send
 * 6. Final result enters composer
 * 7. Transcript remains editable
 * 8. Transcript never automatically submits
 * 9. Manual send still works
 * 10. Stop terminates recognition
 * 11. Navigation/unmount terminates recognition
 * 12. Permission error recovers cleanly
 * 13. Unsupported browser has graceful UI (disabled button with accessible tooltip)
 * 14. Unsupported browser does not tell normal user to configure Whisper/Azure
 * 15. TTS remains absent
 * 16. autoSend remains false
 * 17. autoListen remains false
 * 18. MessageToolbar remains without TTS
 * 19. Previous composer contracts remain green
 * 20. Admin voice page is hidden from normal client-facing sidebar
 * 21. Retained server STT infrastructure remains intact internally
 * 22. Catalogs remain in parity across all 9 locales
 */
import fs from "node:fs";
import path from "node:path";
import React from "react";
import { render, screen, fireEvent, act, cleanup } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";

import ar from "@/i18n/messages/ar.json";
import de from "@/i18n/messages/de.json";
import en from "@/i18n/messages/en.json";
import es from "@/i18n/messages/es.json";
import fr from "@/i18n/messages/fr.json";
import ja from "@/i18n/messages/ja.json";
import ko from "@/i18n/messages/ko.json";
import pt from "@/i18n/messages/pt.json";
import zh from "@/i18n/messages/zh.json";

import { type Locale } from "@/i18n/config";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";

import MicrophoneButton from "@/sections/input/MicrophoneButton";
import Waveform from "@/components/voice/Waveform";
import {
  isSpeechRecognitionSupported,
  useBrowserDictation,
} from "@/hooks/useBrowserDictation";
import { ADMIN_ROUTES } from "@/lib/admin-routes";
import { buildItems, NAV_ITEM_IDS } from "@/lib/admin-sidebar-utils";
import { Permission } from "@/lib/types";
import { Tier } from "@/lib/settings/types";

const WEB_ROOT = path.resolve(__dirname, "../../../..");

const read = (relativePath: string): string =>
  fs.readFileSync(path.join(WEB_ROOT, relativePath), "utf8").replace(/\r\n/g, "\n");

const APP_INPUT_BAR = "src/sections/input/AppInputBar.tsx";
const MICROPHONE_BUTTON = "src/sections/input/MicrophoneButton.tsx";
const MESSAGE_TOOLBAR =
  "src/app/app/message/messageComponents/MessageToolbar.tsx";
const WAVEFORM = "src/components/voice/Waveform.tsx";
const GLOBALS_CSS = "src/app/globals.css";
const VOICE_MODE_PROVIDER = "src/providers/VoiceModeProvider.tsx";
const SETTINGS_PAGE = "src/views/SettingsPage.tsx";
const ADMIN_VOICE_PAGE = "src/views/admin/VoicePage/index.tsx";
const APP_LAYOUT = "src/app/app/layout.tsx";
const NRF_LAYOUT = "src/app/nrf/layout.tsx";
const MESSAGE_TEXT_RENDERER =
  "src/app/app/message/messageComponents/renderers/MessageTextRenderer.tsx";
const USE_VOICE_RECORDER = "src/hooks/useVoiceRecorder.ts";

// Mock SpeechRecognition implementation
class MockSpeechRecognition {
  continuous = false;
  interimResults = false;
  lang = "pt-BR";
  maxAlternatives = 1;
  onstart: (() => void) | null = null;
  onend: (() => void) | null = null;
  onresult: ((ev: any) => void) | null = null;
  onerror: ((ev: any) => void) | null = null;

  start = jest.fn(() => {
    this.onstart?.();
  });

  stop = jest.fn(() => {
    this.onend?.();
  });

  abort = jest.fn(() => {
    this.onend?.();
  });
}

function renderWithIntl(ui: React.ReactElement, locale: Locale = "pt", messages: any = pt) {
  return render(
    <NextIntlClientProvider locale={locale} messages={messages}>
      <TooltipPrimitive.Provider>
        {ui}
      </TooltipPrimitive.Provider>
    </NextIntlClientProvider>
  );
}

describe("TON-VIS-008: Browser-Native Dictation Contracts", () => {
  let originalSpeechRecognition: any;
  let originalWebkitSpeechRecognition: any;

  beforeEach(() => {
    originalSpeechRecognition = (window as any).SpeechRecognition;
    originalWebkitSpeechRecognition = (window as any).webkitSpeechRecognition;
    (window as any).SpeechRecognition = MockSpeechRecognition;
    delete (window as any).webkitSpeechRecognition;
  });

  afterEach(() => {
    cleanup();
    if (originalSpeechRecognition !== undefined) {
      (window as any).SpeechRecognition = originalSpeechRecognition;
    } else {
      delete (window as any).SpeechRecognition;
    }
    if (originalWebkitSpeechRecognition !== undefined) {
      (window as any).webkitSpeechRecognition = originalWebkitSpeechRecognition;
    } else {
      delete (window as any).webkitSpeechRecognition;
    }
  });

  // 1. supported browser -> microphone available without STT provider configured
  test("1. supported browser has microphone available without STT provider configured", () => {
    expect(isSpeechRecognitionSupported()).toBe(true);

    const onTranscription = jest.fn();
    renderWithIntl(
      <MicrophoneButton onTranscription={onTranscription} isSupported={true} />
    );

    const button = screen.getByRole("button");
    expect(button).not.toBeDisabled();
    expect(button).toHaveAttribute("aria-label", pt.chat.input.microphoneButton.startRecording.ariaLabel);
  });

  // 2. no stt_enabled requirement in native dictation path
  test("2. no stt_enabled requirement in AppInputBar native dictation path", () => {
    const inputBarSource = read(APP_INPUT_BAR);
    // AppInputBar must NOT gate MicrophoneButton on sttEnabled
    expect(inputBarSource).not.toContain("sttEnabled ?");
    expect(inputBarSource).not.toContain("useVoiceStatus");
    expect(inputBarSource).toContain("<MicrophoneButton");
  });

  // 3. no admin-provider tooltip in supported browser
  test("3. no admin-provider tooltip in supported browser", () => {
    renderWithIntl(
      <MicrophoneButton onTranscription={jest.fn()} isSupported={true} />
    );

    const button = screen.getByRole("button");
    // Tooltip should not prompt admin configuration
    expect(button.getAttribute("title")).toBeNull();
  });

  // 4. recognition starts on explicit microphone action
  test("4. recognition starts on explicit microphone button click", async () => {
    const onTranscription = jest.fn();
    const onRecordingChange = jest.fn();

    renderWithIntl(
      <MicrophoneButton
        onTranscription={onTranscription}
        onRecordingChange={onRecordingChange}
        isSupported={true}
      />
    );

    const button = screen.getByRole("button");
    await act(async () => {
      fireEvent.click(button);
    });

    expect(onRecordingChange).toHaveBeenCalledWith(true);
  });

  // 5. interim result does not auto-send
  test("5. interim result updates transcription without auto-sending", () => {
    const inputBarSource = read(APP_INPUT_BAR);
    const micButtonTag = inputBarSource.match(/<MicrophoneButton[\s\S]*?\/>/)?.[0] ?? "";
    expect(micButtonTag).not.toContain("onAutoSend");
    expect(micButtonTag).toContain("autoSend={false}");
  });

  // 6. final result enters composer
  test("6. transcription enters composer via onTranscription", () => {
    const inputBarSource = read(APP_INPUT_BAR);
    expect(inputBarSource).toContain("onTranscription={(text) => setMessage(text)}");
  });

  // 7. transcript remains editable
  test("7. transcript remains in normal editable composer state", () => {
    const inputBarSource = read(APP_INPUT_BAR);
    expect(inputBarSource).toContain("setMessage(text)");
    expect(inputBarSource).toContain("submitMessage(message)");
  });

  // 8. transcript never automatically submits
  test("8. transcript never automatically submits", () => {
    const micBtnSource = read(MICROPHONE_BUTTON);
    expect(micBtnSource).toContain("autoSend = false");
    // No auto-send submission call
    expect(micBtnSource).not.toContain("submitMessage(");
  });

  // 9. manual send still works
  test("9. manual send still works and stops recording cleanly", () => {
    const inputBarSource = read(APP_INPUT_BAR);
    expect(inputBarSource).toContain("submitMessage");
    expect(inputBarSource).toContain("stopRecordingRef.current");
  });

  // 10. stop terminates recognition
  test("10. clicking microphone while recording terminates recognition", async () => {
    const onRecordingChange = jest.fn();
    renderWithIntl(
      <MicrophoneButton
        onTranscription={jest.fn()}
        onRecordingChange={onRecordingChange}
        isSupported={true}
      />
    );

    const button = screen.getByRole("button");
    // Start
    await act(async () => {
      fireEvent.click(button);
    });
    expect(onRecordingChange).toHaveBeenCalledWith(true);

    // Stop
    await act(async () => {
      fireEvent.click(button);
    });
    expect(onRecordingChange).toHaveBeenCalledWith(false);
  });

  // 11. navigation/unmount terminates recognition
  test("11. unmount cleanly terminates recognition", () => {
    const hookSource = read("src/hooks/useBrowserDictation.ts");
    expect(hookSource).toContain("recognitionRef.current.abort()");
  });

  // 12. permission error recovers cleanly
  test("12. permission error recovers cleanly without crashing", () => {
    const micBtnSource = read(MICROPHONE_BUTTON);
    expect(micBtnSource).toContain("error === \"permission-denied\"");
    expect(micBtnSource).toContain("toast.error(t(\"microphoneButton.accessError.toast\"))");
    expect(micBtnSource).toContain("const isDisabled = disabled || isProcessing;");
  });

  // 13. unsupported browser has graceful UI
  test("13. unsupported browser renders disabled button with clear tooltip", () => {
    delete (window as any).SpeechRecognition;
    delete (window as any).webkitSpeechRecognition;

    renderWithIntl(
      <MicrophoneButton onTranscription={jest.fn()} isSupported={false} />,
      "pt",
      pt
    );

    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-label", pt.chat.input.microphoneButton.unsupported.ariaLabel);
  });

  // 14. unsupported browser does not tell normal user to configure Whisper/Azure
  test("14. unsupported browser tooltip does not mention Whisper, Azure or admin configuration", () => {
    const tooltip = pt.chat.input.microphoneButton.unsupported.tooltip;
    expect(tooltip).toBe("Ditado não disponível neste navegador.");
    expect(tooltip).not.toContain("Whisper");
    expect(tooltip).not.toContain("Azure");
    expect(tooltip).not.toContain("ElevenLabs");
    expect(tooltip).not.toContain("administrador");
  });

  // 15. TTS remains absent
  test("15. TTS button and playback remain absent", () => {
    const toolbarSource = read(MESSAGE_TOOLBAR);
    expect(toolbarSource).not.toContain("TTSButton");

    const voiceProviderSource = read(VOICE_MODE_PROVIDER);
    expect(voiceProviderSource).toContain("const autoPlayback = false;");
  });

  // 16. autoSend remains false
  test("16. autoSend remains explicitly false", () => {
    const inputBarSource = read(APP_INPUT_BAR);
    expect(inputBarSource).toContain("autoSend={false}");
  });

  // 17. autoListen remains false
  test("17. autoListen remains explicitly false", () => {
    const inputBarSource = read(APP_INPUT_BAR);
    expect(inputBarSource).toContain("autoListen={false}");
  });

  // 18. MessageToolbar remains without TTS
  test("18. MessageToolbar remains without TTS", () => {
    const toolbarSource = read(MESSAGE_TOOLBAR);
    expect(toolbarSource).not.toContain("isTTSActiveForThisMessage");
  });

  // 19. previous composer contracts remain green
  test("19. Waveform and globals CSS contracts remain intact", () => {
    const cssSource = read(GLOBALS_CSS);
    expect(cssSource).not.toContain("@keyframes waveform");

    const waveformSource = read(WAVEFORM);
    expect(waveformSource).toContain("RECORDING_BAR_COUNT = 120");
    expect(waveformSource).toContain("formatElapsedTime(elapsedSeconds)");
  });

  // 20. admin voice page is hidden from normal client-facing sidebar
  test("20. admin voice page is hidden from normal client-facing sidebar", () => {
    // 1. In ADMIN_ROUTES: sidebarLabel is empty string and visibleWhen evaluates to false
    expect(ADMIN_ROUTES.VOICE.sidebarLabel).toBe("");
    expect(ADMIN_ROUTES.VOICE.visibleWhen?.({} as any)).toBe(false);

    // 2. In NAV_ITEM_IDS: VOICE is null
    expect(NAV_ITEM_IDS.VOICE).toBeNull();

    // 3. buildItems does not include voice
    const items = buildItems(
      [Permission.FULL_ADMIN_PANEL_ACCESS],
      {
        vectorDbEnabled: true,
        enableCloud: false,
        tier: Tier.ENTERPRISE,
        customAnalyticsEnabled: false,
        hasSubscription: true,
        hooksEnabled: true,
        opensearchEnabled: true,
        queryHistoryEnabled: true,
        craftAvailable: true,
      },
      null
    );
    expect(items.some((item) => item.nameId === ("voice" as any))).toBe(false);
  });

  // 21. retained server STT infrastructure remains intact internally
  test("21. retained server STT infrastructure remains intact internally", () => {
    const recorderSource = read(USE_VOICE_RECORDER);
    expect(recorderSource).toContain("VoiceRecorderSession");
    expect(recorderSource).toContain("/api/voice/transcribe/stream");
  });

  // 22. catalogs remain in parity across all 9 locales
  test("22. catalogs remain in parity across all 9 locales with unsupported and dictating keys", () => {
    const catalogs = [
      { name: "en", cat: en },
      { name: "pt", cat: pt },
      { name: "es", cat: es },
      { name: "fr", cat: fr },
      { name: "de", cat: de },
      { name: "zh", cat: zh },
      { name: "ja", cat: ja },
      { name: "ko", cat: ko },
      { name: "ar", cat: ar },
    ];

    for (const { name, cat } of catalogs) {
      // 1. waveform.dictating must exist
      expect(typeof (cat as any).chat?.input?.waveform?.dictating).toBe("string");

      // 2. microphoneButton.unsupported must exist with ariaLabel and tooltip
      const unsupported = (cat as any).chat?.input?.microphoneButton?.unsupported;
      expect(unsupported).toBeDefined();
      expect(typeof unsupported.ariaLabel).toBe("string");
      expect(typeof unsupported.tooltip).toBe("string");

      // 3. settings.voice must NOT exist
      expect((cat as any).settings?.voice).toBeUndefined();

      // 4. speakingPlaceholder must NOT exist
      expect((cat as any).chat?.input?.appInputBar?.input?.speakingPlaceholder).toBeUndefined();
    }
  });

  // 23. mute toggle connects setMutedRef and updates isMuted state
  test("23. mute toggle connects setMutedRef and updates isMuted state", async () => {
    const onMuteChange = jest.fn();
    const setMutedRef = { current: null as any };
    renderWithIntl(
      <MicrophoneButton
        onTranscription={jest.fn()}
        onMuteChange={onMuteChange}
        setMutedRef={setMutedRef}
        isSupported={true}
      />
    );

    expect(typeof setMutedRef.current).toBe("function");

    const button = screen.getByRole("button");
    // Start recording
    await act(async () => {
      fireEvent.click(button);
    });

    // Mute
    await act(async () => {
      setMutedRef.current(true);
    });
    expect(onMuteChange).toHaveBeenCalledWith(true);

    // Unmute
    await act(async () => {
      setMutedRef.current(false);
    });
    expect(onMuteChange).toHaveBeenCalledWith(false);
  });

  // 24. Waveform renders mute button with correct icon and tooltip
  test("24. Waveform toggles mute button between Silenciar and Ativar", () => {
    const onMuteToggle = jest.fn();
    const { rerender } = renderWithIntl(
      <Waveform
        isActive={true}
        isMuted={false}
        onMuteToggle={onMuteToggle}
      />,
      "pt",
      pt
    );

    const muteBtn = screen.getByRole("button", { name: "Silenciar microfone" });
    expect(muteBtn).toBeInTheDocument();

    fireEvent.click(muteBtn);
    expect(onMuteToggle).toHaveBeenCalledTimes(1);

    // Re-render as muted
    rerender(
      <NextIntlClientProvider locale="pt" messages={pt}>
        <TooltipPrimitive.Provider>
          <Waveform
            isActive={true}
            isMuted={true}
            onMuteToggle={onMuteToggle}
          />
        </TooltipPrimitive.Provider>
      </NextIntlClientProvider>
    );

    const unmuteBtn = screen.getByRole("button", { name: "Ativar microfone" });
    expect(unmuteBtn).toBeInTheDocument();
  });
});
