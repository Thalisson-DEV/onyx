"use client";

import { useCallback, useEffect, useRef, useState } from "react";

// Standard web SpeechRecognition type declarations for browsers and test mocks
export interface SpeechRecognitionResultItem {
  transcript: string;
  confidence?: number;
}

export interface SpeechRecognitionResultLike {
  isFinal: boolean;
  length: number;
  [index: number]: SpeechRecognitionResultItem;
}

export interface SpeechRecognitionEventLike {
  resultIndex: number;
  results: {
    length: number;
    [index: number]: SpeechRecognitionResultLike;
  };
}

export interface SpeechRecognitionErrorEventLike {
  error: string;
  message?: string;
}

export interface SpeechRecognitionInstance {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  maxAlternatives: number;
  start(): void;
  stop(): void;
  abort(): void;
  onstart: (() => void) | null;
  onend: (() => void) | null;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEventLike) => void) | null;
}

export type SpeechRecognitionConstructor = new () => SpeechRecognitionInstance;

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }
}

/**
 * Resolves the browser SpeechRecognition constructor (standard or webkit-prefixed).
 * Returns null in SSR environments or browsers without native speech recognition.
 */
export function getSpeechRecognitionConstructor(): SpeechRecognitionConstructor | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.SpeechRecognition ?? window.webkitSpeechRecognition ?? null;
}

/**
 * Checks whether native browser speech recognition is available.
 */
export function isSpeechRecognitionSupported(): boolean {
  return getSpeechRecognitionConstructor() !== null;
}

export interface BrowserDictationOptions {
  lang?: string;
  onInterimTranscript?: (text: string) => void;
  onFinalTranscript?: (text: string) => void;
  onError?: (error: string) => void;
}

export interface BrowserDictationReturn {
  isSupported: boolean;
  isRecording: boolean;
  isProcessing: boolean;
  isMuted: boolean;
  error: string | null;
  liveTranscript: string;
  startDictation: () => Promise<void>;
  stopDictation: () => Promise<string | null>;
  setMuted: (muted: boolean) => void;
  resetError: () => void;
}

/**
 * Hook for browser-native dictation using the Web Speech API (SpeechRecognition).
 *
 * Guarantees:
 * - Starts only upon explicit user interaction
 * - Streams interim results into composer
 * - Never auto-sends or auto-listens
 * - Allows full user editing before manual send
 * - Cleans up cleanly on stop, unmount, or navigation
 * - Recovers safely from permission and speech recognition errors
 * - Supports honest microphone muting (suspends capture while maintaining session)
 */
export function useBrowserDictation({
  lang = "pt-BR",
  onInterimTranscript,
  onFinalTranscript,
  onError,
}: BrowserDictationOptions = {}): BrowserDictationReturn {
  const [isSupported, setIsSupported] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [liveTranscript, setLiveTranscript] = useState("");

  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const finalTranscriptRef = useRef("");
  const liveTranscriptRef = useRef("");
  const isStartingRef = useRef(false);
  const isMutedRef = useRef(false);
  const isRecordingRef = useRef(false);
  const accumulatedBeforeMuteRef = useRef("");

  // Feature detection on mount
  useEffect(() => {
    setIsSupported(isSpeechRecognitionSupported());
  }, []);

  const resetError = useCallback(() => {
    setError(null);
  }, []);

  const startRecognitionSession = useCallback(() => {
    const RecognitionClass = getSpeechRecognitionConstructor();
    if (!RecognitionClass) {
      setError("unsupported");
      onError?.("unsupported");
      return;
    }

    try {
      const recognition = new RecognitionClass();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = lang;
      recognition.maxAlternatives = 1;

      recognition.onstart = () => {
        isStartingRef.current = false;
        isRecordingRef.current = true;
        setIsRecording(true);
        setIsProcessing(false);
      };

      recognition.onresult = (event: SpeechRecognitionEventLike) => {
        if (isMutedRef.current) {
          return;
        }

        let finalAccumulated = "";
        let interimAccumulated = "";

        for (let i = 0; i < event.results.length; i++) {
          const res = event.results[i];
          if (!res) continue;
          const transcriptChunk = res[0]?.transcript || "";
          if (res.isFinal) {
            finalAccumulated += (finalAccumulated ? " " : "") + transcriptChunk.trim();
          } else {
            interimAccumulated += (interimAccumulated ? " " : "") + transcriptChunk.trim();
          }
        }

        const base = accumulatedBeforeMuteRef.current;
        const newPart = [finalAccumulated, interimAccumulated]
          .filter(Boolean)
          .join(" ");

        const combined = [base, newPart].filter(Boolean).join(" ");
        const finalCombined = [base, finalAccumulated].filter(Boolean).join(" ");

        liveTranscriptRef.current = combined;
        finalTranscriptRef.current = finalCombined || combined;
        setLiveTranscript(combined);
        onInterimTranscript?.(combined);
      };

      recognition.onerror = (event: SpeechRecognitionErrorEventLike) => {
        isStartingRef.current = false;
        const errorCode = event.error;

        // Aborted or no-speech during intentional mute or transition is harmless
        if (errorCode === "no-speech" || (errorCode === "aborted" && isMutedRef.current)) {
          return;
        }

        if (errorCode === "aborted") {
          return;
        }

        isRecordingRef.current = false;
        setIsProcessing(false);
        setIsRecording(false);
        setIsMuted(false);
        isMutedRef.current = false;

        const normalizedError =
          errorCode === "not-allowed" || errorCode === "service-not-allowed"
            ? "permission-denied"
            : errorCode || "recognition-error";

        setError(normalizedError);
        onError?.(normalizedError);
      };

      recognition.onend = () => {
        isStartingRef.current = false;
        recognitionRef.current = null;

        // If muted, recognition was intentionally aborted while maintaining session
        if (isMutedRef.current) {
          return;
        }

        isRecordingRef.current = false;
        setIsRecording(false);
        setIsProcessing(false);
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err) {
      isStartingRef.current = false;
      isRecordingRef.current = false;
      setIsProcessing(false);
      setIsRecording(false);
      setIsMuted(false);
      isMutedRef.current = false;
      recognitionRef.current = null;
      const errorMsg = err instanceof Error ? err.message : "recognition-start-error";
      setError(errorMsg);
      onError?.(errorMsg);
    }
  }, [lang, onError, onInterimTranscript]);

  const startDictation = useCallback(async () => {
    // Guard against re-entrant start
    if (recognitionRef.current || isStartingRef.current) {
      return;
    }

    isStartingRef.current = true;
    setIsProcessing(true);
    setError(null);
    setIsMuted(false);
    isMutedRef.current = false;
    accumulatedBeforeMuteRef.current = "";
    finalTranscriptRef.current = "";
    liveTranscriptRef.current = "";
    setLiveTranscript("");

    startRecognitionSession();
  }, [startRecognitionSession]);

  const setMuted = useCallback(
    (muted: boolean) => {
      if (isMutedRef.current === muted) return;
      isMutedRef.current = muted;
      setIsMuted(muted);

      if (muted) {
        // Freeze transcript accumulated prior to muting
        accumulatedBeforeMuteRef.current =
          finalTranscriptRef.current ||
          liveTranscriptRef.current ||
          accumulatedBeforeMuteRef.current;

        // Abort active recognition to truly release/silence audio capture
        const rec = recognitionRef.current;
        if (rec) {
          try {
            rec.abort();
          } catch {
            // Ignore abort errors
          }
          recognitionRef.current = null;
        }
      } else {
        // Unmuting: if recording session is active, resume recognition
        if (isRecordingRef.current && !recognitionRef.current) {
          startRecognitionSession();
        }
      }
    },
    [startRecognitionSession]
  );

  const stopDictation = useCallback(async (): Promise<string | null> => {
    isStartingRef.current = false;
    const rec = recognitionRef.current;
    if (rec) {
      try {
        rec.stop();
      } catch {
        // Recognition might already be stopped
      }
      recognitionRef.current = null;
    }

    isRecordingRef.current = false;
    setIsRecording(false);
    setIsProcessing(false);
    setIsMuted(false);
    isMutedRef.current = false;

    const result =
      finalTranscriptRef.current ||
      liveTranscriptRef.current ||
      accumulatedBeforeMuteRef.current ||
      null;

    accumulatedBeforeMuteRef.current = "";

    if (result) {
      onFinalTranscript?.(result);
    }
    return result;
  }, [onFinalTranscript]);

  // Clean up on unmount or navigation
  useEffect(() => {
    return () => {
      isStartingRef.current = false;
      isRecordingRef.current = false;
      isMutedRef.current = false;
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {
          // Ignore cleanup errors
        }
        recognitionRef.current = null;
      }
    };
  }, []);

  return {
    isSupported,
    isRecording,
    isProcessing,
    isMuted,
    error,
    liveTranscript,
    startDictation,
    stopDictation,
    setMuted,
    resetError,
  };
}
