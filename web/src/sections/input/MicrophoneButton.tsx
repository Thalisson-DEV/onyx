"use client";

import { useCallback, useEffect, useRef } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Button } from "@opal/components";
import { SvgMicrophone, SvgSimpleLoader } from "@opal/icons";
import { toast } from "@opal/layouts";
import { ChatState } from "@/app/app/interfaces";
import {
  useBrowserDictation,
  isSpeechRecognitionSupported,
} from "@/hooks/useBrowserDictation";

const LOCALE_TO_SPEECH_LANG = {
  pt: "pt-BR",
  en: "en-US",
  es: "es-ES",
  fr: "fr-FR",
  de: "de-DE",
  zh: "zh-CN",
  ja: "ja-JP",
  ko: "ko-KR",
  ar: "ar-SA",
} satisfies Record<string, string>;

interface MicrophoneButtonProps {
  onTranscription: (text: string) => void;
  disabled?: boolean;
  autoSend?: boolean;
  /** Called with transcribed text when autoSend is enabled (disabled in TON dictation) */
  onAutoSend?: (text: string) => void;
  /** Auto-listen disabled in TON dictation */
  autoListen?: boolean;
  /** Current chat state */
  chatState?: ChatState;
  /** Called when recording state changes */
  onRecordingChange?: (isRecording: boolean) => void;
  /** Ref to expose stop recording function to parent */
  stopRecordingRef?: React.MutableRefObject<
    (() => Promise<string | null>) | null
  >;
  /** Called when recording starts */
  onRecordingStart?: () => void;
  /** Existing message text to prepend to transcription (append mode) */
  currentMessage?: string;
  /** Called when mute state changes */
  onMuteChange?: (isMuted: boolean) => void;
  /** Ref to expose setMuted function to parent */
  setMutedRef?: React.MutableRefObject<((muted: boolean) => void) | null>;
  /** Called with current microphone audio level (0-1) for waveform visualization */
  onAudioLevel?: (level: number) => void;
  /** Whether current chat is a new session */
  isNewSession?: boolean;
  /** Explicit capability override for tests or controlled environments */
  isSupported?: boolean;
}

function MicrophoneButton({
  onTranscription,
  disabled = false,
  autoSend = false,
  onAutoSend,
  autoListen = false,
  chatState,
  onRecordingChange,
  stopRecordingRef,
  onRecordingStart,
  currentMessage = "",
  onMuteChange,
  setMutedRef,
  onAudioLevel,
  isNewSession = false,
  isSupported: isSupportedProp,
}: MicrophoneButtonProps) {
  const t = useTranslations("chat.input");
  const locale = useLocale();
  const lang = LOCALE_TO_SPEECH_LANG[locale] ?? "pt-BR";

  // Snapshot of existing message text when recording starts (for append mode)
  const messagePrefixRef = useRef("");
  const currentMessageRef = useRef(currentMessage);
  const suppressTranscriptUpdatesRef = useRef(false);
  const manualStopRequestedRef = useRef(false);

  useEffect(() => {
    currentMessageRef.current = currentMessage;
  }, [currentMessage]);

  // Helper to combine prefix with new transcript
  const withPrefix = useCallback((text: string) => {
    const prefix = messagePrefixRef.current;
    if (!prefix) return text;
    return prefix + (prefix.endsWith(" ") ? "" : " ") + text;
  }, []);

  const {
    isSupported: isNativeSupported,
    isRecording,
    isProcessing,
    isMuted,
    error,
    startDictation,
    stopDictation,
    setMuted,
  } = useBrowserDictation({
    lang,
    onInterimTranscript: (interim) => {
      if (!suppressTranscriptUpdatesRef.current && interim) {
        onTranscription(withPrefix(interim));
      }
    },
    onFinalTranscript: (final) => {
      if (!suppressTranscriptUpdatesRef.current && final) {
        onTranscription(withPrefix(final));
      }
    },
  });

  const effectiveIsSupported =
    isSupportedProp !== undefined
      ? isSupportedProp
      : (isNativeSupported || isSpeechRecognitionSupported());

  // Expose stopRecording to parent (e.g. submitMessage stopping recording cleanly)
  useEffect(() => {
    if (stopRecordingRef) {
      stopRecordingRef.current = stopDictation;
    }
  }, [stopDictation, stopRecordingRef]);

  // Expose setMuted to parent (e.g. Waveform mute toggle)
  useEffect(() => {
    if (setMutedRef) {
      setMutedRef.current = setMuted;
    }
  }, [setMuted, setMutedRef]);

  // Notify parent when mute state changes
  useEffect(() => {
    onMuteChange?.(isMuted);
  }, [isMuted, onMuteChange]);

  // Notify parent when recording state changes
  useEffect(() => {
    onRecordingChange?.(isRecording);
  }, [isRecording, onRecordingChange]);

  // New sessions reset any active prefix
  useEffect(() => {
    if (isNewSession) {
      suppressTranscriptUpdatesRef.current = false;
      messagePrefixRef.current = "";
    }
  }, [isNewSession]);

  useEffect(() => {
    if (!isRecording) {
      suppressTranscriptUpdatesRef.current = false;
    }
  }, [isRecording]);

  // Error notifications
  useEffect(() => {
    if (error === "permission-denied") {
      toast.error(t("microphoneButton.accessError.toast"));
    } else if (error && error !== "unsupported") {
      toast.error(error);
    }
  }, [error, t]);

  const handleClick = useCallback(async () => {
    if (isRecording) {
      manualStopRequestedRef.current = true;
      try {
        const finalTranscript = await stopDictation();
        if (finalTranscript) {
          onTranscription(withPrefix(finalTranscript));
        }
        messagePrefixRef.current = "";
      } finally {
        manualStopRequestedRef.current = false;
      }
    } else {
      try {
        suppressTranscriptUpdatesRef.current = false;
        messagePrefixRef.current = currentMessage;
        onRecordingStart?.();
        await startDictation();
      } catch (err) {
        console.error("Dictation start failed:", err);
        toast.error(t("microphoneButton.accessError.toast"));
      }
    }
  }, [
    isRecording,
    currentMessage,
    onRecordingStart,
    startDictation,
    stopDictation,
    onTranscription,
    withPrefix,
    t,
  ]);

  // If speech recognition is not supported in the browser, render gracefully disabled
  if (!effectiveIsSupported) {
    return (
      <Button
        disabled
        icon={SvgMicrophone}
        aria-label={t("microphoneButton.unsupported.ariaLabel")}
        prominence="tertiary"
        tooltip={t("microphoneButton.unsupported.tooltip")}
      />
    );
  }

  // Icon: show loader when processing, otherwise mic
  const icon = isProcessing ? SvgSimpleLoader : SvgMicrophone;

  // In dictation-only mode, microphone is disabled when explicitly disabled or processing.
  const isDisabled = disabled || isProcessing;

  // Recording = active (primary), idle = tertiary
  const prominence = isRecording ? "primary" : "tertiary";

  return (
    <Button
      disabled={isDisabled}
      icon={icon}
      onClick={handleClick}
      aria-label={
        isRecording
          ? t("microphoneButton.stopRecording.ariaLabel")
          : t("microphoneButton.startRecording.ariaLabel")
      }
      prominence={prominence}
    />
  );
}

export default MicrophoneButton;
