"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import useSWR from "swr";
import { errorHandlingFetcher } from "@/lib/fetcher";
import type {
  ClosingOutput,
  Publication,
} from "@/views/ton/ControladoriaPage/types";

interface ClosingSubmission {
  request_id: string;
  normalization_run_id: string | null;
  structure_version_id: string | null;
  period: string;
  unit_id: string | null;
}

function isSubmission(value: unknown): value is ClosingSubmission {
  return (
    typeof value === "object" &&
    value !== null &&
    "request_id" in value &&
    typeof value.request_id === "string" &&
    "period" in value &&
    typeof value.period === "string" &&
    "normalization_run_id" in value &&
    (value.normalization_run_id === null ||
      typeof value.normalization_run_id === "string") &&
    "structure_version_id" in value &&
    (value.structure_version_id === null ||
      typeof value.structure_version_id === "string") &&
    "unit_id" in value &&
    (value.unit_id === null || typeof value.unit_id === "string")
  );
}

// Only the retry token and exact request survive reload. Results come from the API.
export function useR3Execution(
  output: ClosingOutput | undefined,
  enabled: boolean,
  userId: string | undefined,
  canReadResults = enabled
) {
  const publications = useSWR<Publication | null>(
    canReadResults && output
      ? `/api/ton/agent/routines/R3/latest?period=${output.period}${output.unit_id ? `&unit_id=${encodeURIComponent(output.unit_id)}` : ""}`
      : null,
    errorHandlingFetcher
  );
  const [running, setRunning] = useState(false);
  const [failed, setFailed] = useState(false);
  const [startedAt, setStartedAt] = useState<string | null>(null);
  const [result, setResult] = useState<Publication | null>(null);
  const pending = useRef<ClosingSubmission | null>(null);
  const inFlight = useRef(false);
  const resumed = useRef(false);
  const storageKey = userId ? `ton:R3:submission:${userId}` : null;

  const submit = useCallback(
    async (request: ClosingSubmission) => {
      if (!enabled || inFlight.current || !storageKey) return;
      inFlight.current = true;
      pending.current = request;
      setRunning(true);
      setFailed(false);
      setStartedAt(new Date().toISOString());
      try {
        sessionStorage.setItem(storageKey, JSON.stringify(request));
        const response = await fetch("/api/ton/agent/routines/R3/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(request),
        });
        if (!response.ok) throw new Error("R3 request failed");
        const publication: Publication = await response.json();
        setResult(publication);
        pending.current = null;
        sessionStorage.removeItem(storageKey);
        await publications.mutate();
      } catch {
        setFailed(true);
      } finally {
        inFlight.current = false;
        setRunning(false);
      }
    },
    [enabled, storageKey, publications.mutate]
  );

  useEffect(() => {
    if (!enabled || !storageKey || resumed.current) return;
    resumed.current = true;
    const saved = sessionStorage.getItem(storageKey);
    if (saved) {
      try {
        const value: unknown = JSON.parse(saved);
        if (isSubmission(value)) void submit(value);
        else sessionStorage.removeItem(storageKey);
      } catch {
        sessionStorage.removeItem(storageKey);
      }
    }
  }, [enabled, storageKey, submit]);

  function run() {
    if (!output || !enabled) return;
    void submit(
      pending.current ?? {
        request_id: crypto.randomUUID(),
        normalization_run_id: output.normalization_run_id,
        structure_version_id: output.structure_version_id,
        period: output.period,
        unit_id: output.unit_id,
      }
    );
  }

  const latest =
    result?.output.unit_id === output?.unit_id &&
    result?.output.period === output?.period
      ? result
      : publications.data;
  return {
    run,
    running,
    failed,
    startedAt,
    latest,
    isLoading: publications.isLoading,
    error: publications.error,
  };
}
