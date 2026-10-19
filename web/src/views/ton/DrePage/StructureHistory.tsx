"use client";

import { useState } from "react";
import useSWR from "swr";
import { Button, InputTypeIn, Text } from "@opal/components";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { COPY, formatDateTime } from "@/lib/ton/copy";
import { TonApiError, postTonJson } from "@/lib/ton/decisions";
import { getBusinessLabel } from "@/lib/ton/labels";
import { StatusPill } from "@/views/ton/components/ui";

const T = COPY.dre.editor.history;

interface DreChange {
  kind: string;
  line: string;
  before: string | null;
  after: string | null;
}

interface HistoryItem {
  id: string;
  number: number;
  created_at: string;
  author: string | null;
  reason: string | null;
  changes: DreChange[];
}

interface RestoreView {
  target_number: number;
  changes: DreChange[];
  left_out_natures: string[];
  version: { number: number } | null;
}

function describe(change: DreChange): string {
  const text = T.changes[change.kind];
  return text
    ? text(change.line, change.before, change.after)
    : `${change.kind}: ${change.line}`;
}

function Changes({ changes }: { changes: DreChange[] }) {
  return (
    <ul className="flex flex-col gap-0.5 ps-4 list-disc">
      {changes.map((change, index) => (
        <li key={`${change.kind}-${change.line}-${index}`}>
          <Text font="secondary-body" color="text-04">
            {describe(change)}
          </Text>
        </li>
      ))}
    </ul>
  );
}

/** Every version of the structure: who, when, why and what changed. */
export default function StructureHistory({
  structureId,
  currentNumber,
  onRestored,
}: {
  structureId: string;
  currentNumber: number;
  onRestored: (number: number) => Promise<void>;
}) {
  const { data, error, isLoading } = useSWR<HistoryItem[]>(
    `/api/ton/dre/structures/${structureId}/versions`,
    errorHandlingFetcher
  );
  const [target, setTarget] = useState<number | null>(null);
  const [preview, setPreview] = useState<RestoreView | null>(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  function fail(caught: unknown) {
    setFailure(
      caught instanceof TonApiError && caught.detail
        ? `${T.restoreFailed} ${getBusinessLabel(caught.detail)}`
        : T.restoreFailed
    );
  }

  async function open(number: number) {
    setTarget(number);
    setPreview(null);
    setReason("");
    setFailure(null);
    setBusy(true);
    try {
      setPreview(
        await postTonJson<RestoreView>(
          `/api/ton/dre/structures/${structureId}/versions/${number}/restore`,
          { dry_run: true }
        )
      );
    } catch (caught) {
      fail(caught);
    } finally {
      setBusy(false);
    }
  }

  async function confirm(number: number) {
    setBusy(true);
    setFailure(null);
    try {
      const restored = await postTonJson<RestoreView>(
        `/api/ton/dre/structures/${structureId}/versions/${number}/restore`,
        { dry_run: false, reason: reason.trim() || null }
      );
      if (restored.version) await onRestored(restored.version.number);
    } catch (caught) {
      fail(caught);
    } finally {
      setBusy(false);
    }
  }

  if (isLoading)
    return (
      <Text font="secondary-body" color="text-03">
        {T.loading}
      </Text>
    );
  if (error || !data)
    return (
      <Text font="secondary-body" color="status-error-05">
        {T.failed}
      </Text>
    );
  if (data.length <= 1)
    return (
      <Text font="secondary-body" color="text-03">
        {T.empty}
      </Text>
    );

  return (
    <ol className="flex flex-col">
      {data.map((item) => {
        const current = item.number === currentNumber;
        const opened = target === item.number;
        return (
          <li
            key={item.id}
            className="flex flex-col gap-2 py-3 border-b border-01 last:border-b-0"
          >
            <div className="flex flex-wrap items-center gap-2">
              <Text font="main-ui-action" color="text-05">
                {T.version(item.number)}
              </Text>
              {current && <StatusPill tone="brand">{T.current}</StatusPill>}
              <Text font="secondary-body" color="text-03">
                {T.by(item.author, formatDateTime(item.created_at))}
              </Text>
              <span className="flex-1" />
              {!current && !opened && (
                <Button
                  prominence="secondary"
                  disabled={busy}
                  onClick={() => void open(item.number)}
                >
                  {T.restore}
                </Button>
              )}
            </div>
            <Text font="secondary-body" color={item.reason ? "text-05" : "text-03"}>
              {item.reason || T.noReason}
            </Text>
            {item.changes.length > 0 ? (
              <Changes changes={item.changes} />
            ) : (
              <Text font="secondary-body" color="text-03">
                {T.noChanges}
              </Text>
            )}
            {opened && (
              <div className="flex flex-col gap-2 rounded-08 border border-01 p-3 bg-background-tint-01">
                <Text font="main-ui-action" color="text-05">
                  {T.preview(item.number)}
                </Text>
                {busy && !preview && (
                  <Text font="secondary-body" color="text-03">
                    {T.loading}
                  </Text>
                )}
                {preview &&
                  (preview.changes.length > 0 ? (
                    <>
                      <Text font="secondary-body" color="text-04">
                        {T.previewIntro}
                      </Text>
                      <Changes changes={preview.changes} />
                    </>
                  ) : (
                    <Text font="secondary-body" color="text-03">
                      {T.previewNone}
                    </Text>
                  ))}
                {preview && preview.left_out_natures.length > 0 && (
                  <span className="text-status-warning-05">
                    <Text font="secondary-body" color="inherit">
                      {T.leftOut(preview.left_out_natures.join(", "))}
                    </Text>
                  </span>
                )}
                {failure && (
                  <Text font="secondary-body" color="status-error-05">
                    {failure}
                  </Text>
                )}
                <div className="flex flex-wrap items-end gap-3">
                  <label className="flex flex-col gap-1 flex-1 min-w-[14rem]">
                    <Text font="secondary-action" color="text-04">
                      {T.reason}
                    </Text>
                    <InputTypeIn
                      value={reason}
                      aria-label={T.reason}
                      onChange={(event) => setReason(event.target.value)}
                    />
                  </label>
                  <Button
                    prominence="tertiary"
                    disabled={busy}
                    onClick={() => {
                      setTarget(null);
                      setPreview(null);
                    }}
                  >
                    {T.cancel}
                  </Button>
                  <Button
                    disabled={busy || !preview || preview.changes.length === 0}
                    onClick={() => void confirm(item.number)}
                  >
                    {busy && preview ? T.confirming : T.confirm}
                  </Button>
                </div>
              </div>
            )}
          </li>
        );
      })}
    </ol>
  );
}
