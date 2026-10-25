"use client";

import { SideModal } from "@/views/ton/components/kit";
import { useState } from "react";
import { useFormatter, useTranslations } from "next-intl";
import useSWR from "swr";
import { useDropzone } from "react-dropzone";
import { BasicModalFooter, Button, Text } from "@opal/components";
import { SvgFiles, SvgSimpleLoader, SvgUploadCloud } from "@opal/icons";
import { SettingsLayouts } from "@opal/layouts";
import { cn } from "@opal/utils";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { hasPermission } from "@/lib/permissions";
import { Permission } from "@/lib/types";
import { COPY, formatNumber, formatRelativeDateTime } from "@/lib/ton/copy";
import { pendingQueueHref } from "@/lib/ton/decisions";
import { SHOW_UPSTREAM_SCREENS } from "@/lib/ton/product-surface";
import {
  IMPORT_DIAGNOSTIC_KEYS,
  isInformationalDiagnostic,
} from "@/lib/ton/import-diagnostics";
import { useUser } from "@/providers/UserProvider";
import { TonStatusTag } from "@/views/ton/components/TonStatusTag";
import ProblemRows from "@/views/ton/DataSourcesPage/ProblemRows";

interface Diagnostic {
  code: string;
  count: number;
}

interface ClientImport {
  id: string;
  source_id: string;
  status: string;
  filename: string;
  format: string;
  size_bytes: number;
  started_at: string;
  finished_at: string | null;
  imported: number;
  rejected: number;
  warnings: number;
  errors: number;
  needs_review: number | null;
  available_for_analysis: number | null;
  diagnostics: Diagnostic[];
  downstream: string[];
  readiness_status: string;
  readiness_run_id: string | null;
  failure_reason: string | null;
}

interface ClientSource {
  key: string;
  name: string;
  description: string;
  format: string;
  source_id: string | null;
  can_import: boolean;
  status: "CURRENT" | "PROCESSING" | "ATTENTION" | "FAILED" | "UNCONFIGURED";
  last_success_at: string | null;
  last_attempt_at: string | null;
  latest: ClientImport | null;
  history: ClientImport[];
}

const MAX_FILE_BYTES = 50 * 1024 * 1024;
/** NG gets the decision preview; billing only reports what was read. */
const PREVIEWED_SOURCES = new Set([
  "financial_launches",
  "billing_invoices",
  "installments",
]);

interface ReimportPreview {
  imported: number;
  rejected: number;
  has_previous_review: boolean;
  carried_over: number;
  evidence_changed: number;
  still_open: number;
  reopened: number;
  new: number;
  not_detected: number;
  changes_actuals: boolean;
}

function isReimportPreview(value: unknown): value is ReimportPreview {
  if (typeof value !== "object" || value === null) return false;
  return (
    "carried_over" in value &&
    typeof value.carried_over === "number" &&
    "new" in value &&
    typeof value.new === "number" &&
    "not_detected" in value &&
    typeof value.not_detected === "number"
  );
}

function PreviewSummary({
  preview,
  previous,
}: {
  preview: ReimportPreview;
  previous: ClientImport | null;
}) {
  const copy = COPY.sources.preview;
  if (!preview.changes_actuals)
    return (
      <section aria-label={copy.title} className="flex flex-col gap-2">
        <Text as="h3" font="main-ui-action" color="text-05">
          {copy.title}
        </Text>
        <Text as="p" font="main-ui-body" color="text-04">
          {copy.billingRecords(preview.imported, preview.rejected)}
        </Text>
        {previous && (
          <Text as="p" font="secondary-body" color="text-03">
            {copy.previousImport(previous.imported)}
          </Text>
        )}
        <Text as="p" font="secondary-body" color="text-03">
          {copy.billingOnly}
        </Text>
      </section>
    );
  const toDecide = preview.new + preview.evidence_changed + preview.reopened;
  const rows: [string, number][] = [
    [copy.carriedOver, preview.carried_over],
    [copy.evidenceChanged, preview.evidence_changed],
    [copy.reopened, preview.reopened],
    [copy.newFindings, preview.new],
    [copy.stillOpen, preview.still_open],
    [copy.notDetected, preview.not_detected],
  ];
  return (
    <section aria-label={copy.title} className="flex flex-col gap-3">
      <Text as="h3" font="main-ui-action" color="text-05">
        {copy.title}
      </Text>
      <Text as="p" font="secondary-body" color="text-03">
        {copy.records(preview.imported, preview.rejected)}
      </Text>
      {preview.has_previous_review ? (
        <dl className="grid grid-cols-1 gap-x-6 gap-y-2 sm:grid-cols-2">
          {rows.map(([label, count]) => (
            <div
              key={label}
              className="flex items-baseline justify-between gap-3"
            >
              <dt>
                <Text font="secondary-body" color="text-04">
                  {label}
                </Text>
              </dt>
              <dd>
                <Text font="main-ui-action" color="text-05">
                  {formatNumber(count)}
                </Text>
              </dd>
            </div>
          ))}
        </dl>
      ) : (
        <Text as="p" font="secondary-body" color="text-04">
          {copy.firstImport(preview.new)}
        </Text>
      )}
      <Text as="p" font="secondary-body" color="text-03">
        {toDecide > 0 ? copy.toDecide(toDecide) : copy.nothingToDecide}
      </Text>
    </section>
  );
}

function isClientImport(value: unknown): value is ClientImport {
  if (typeof value !== "object" || value === null) return false;
  return (
    "id" in value &&
    typeof value.id === "string" &&
    "status" in value &&
    typeof value.status === "string" &&
    "imported" in value &&
    typeof value.imported === "number" &&
    "diagnostics" in value &&
    Array.isArray(value.diagnostics) &&
    "downstream" in value &&
    Array.isArray(value.downstream)
  );
}

export function SourceUpload({
  source,
  onClose,
  onComplete,
  guidance,
}: {
  source: ClientSource;
  onClose: () => void;
  onComplete: (result: ClientImport) => void;
  /** What the file must contain for the workflow that opened the upload. */
  guidance?: string;
}) {
  const t = useTranslations("dataSources");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState<ReimportPreview | null>(null);
  const extension = source.format.toLowerCase();
  const needsPreview = PREVIEWED_SOURCES.has(source.key);
  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    multiple: false,
    noClick: true,
    noKeyboard: true,
    disabled: busy,
    onDropAccepted: (files) => {
      const chosen = files[0];
      if (!chosen) return;
      if (chosen.size > MAX_FILE_BYTES) {
        setFile(null);
        setError(t("fileTooLarge"));
        return;
      }
      if (!chosen.name.toLowerCase().endsWith(`.${extension}`)) {
        setFile(null);
        setError(t("invalidFile"));
        return;
      }
      setFile(chosen);
      setPreview(null);
      setError("");
    },
    onDropRejected: () => setError(t("invalidFile")),
  });

  async function submit() {
    if (!file) return;
    if (file.size > MAX_FILE_BYTES) {
      setError(t("fileTooLarge"));
      return;
    }
    if (!file.name.toLowerCase().endsWith(`.${extension}`)) {
      setError(t("invalidFile"));
      return;
    }
    setBusy(true);
    setError("");
    try {
      const body = new FormData();
      const mediaType =
        source.format === "XLS"
          ? "application/vnd.ms-excel"
          : "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
      body.append("file", new File([file], file.name, { type: mediaType }));
      if (needsPreview && !preview) {
        // Nothing is stored yet: the server parses and compares in memory.
        const response = await fetch(
          `/api/ton/data-sources/${source.key}/imports/preview`,
          { method: "POST", body }
        );
        if (!response.ok) {
          setError(
            response.status === 400 ? t("unrecognized") : t("uploadError")
          );
          return;
        }
        const result: unknown = await response.json();
        if (!isReimportPreview(result)) throw new Error("Invalid preview");
        setPreview(result);
        return;
      }
      const response = await fetch(
        `/api/ton/data-sources/${source.key}/imports`,
        { method: "POST", body }
      );
      if (!response.ok) {
        setError(
          response.status === 400 ? t("unrecognized") : t("uploadError")
        );
        return;
      }
      const result: unknown = await response.json();
      if (!isClientImport(result)) throw new Error("Invalid import response");
      onComplete(result);
    } catch {
      setError(t("uploadError"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <SideModal open onOpenChange={(open) => !open && !busy && onClose()}>
      <SideModal.Content width="md">
        <SideModal.Header
          icon={SvgUploadCloud}
          title={t("uploadTitle", { source: source.name })}
          description={t("uploadDescription", { format: source.format })}
          onClose={() => !busy && onClose()}
        />
        <SideModal.Body>
          <div className="flex w-full flex-col gap-4">
            {guidance && (
              <Text as="p" font="main-ui-body" color="text-04">
                {guidance}
              </Text>
            )}
            <div
              {...getRootProps()}
              className={cn(
                "flex min-h-36 w-full flex-col items-center justify-center gap-3 rounded-lg border border-dashed p-5 text-center",
                isDragActive
                  ? "border-action-selection-05 bg-background-tint-01"
                  : "border-border-02"
              )}
            >
              <input
                {...getInputProps({
                  accept: `.${extension}`,
                  "aria-label": t("chooseFile"),
                })}
              />
              <Button prominence="secondary" onClick={open} disabled={busy}>
                {t("chooseFile")}
              </Button>
              <Text font="secondary-body" color={file ? "text-05" : "text-03"}>
                {file ? file.name : t("dropFile")}
              </Text>
            </div>
            {preview && (
              <PreviewSummary preview={preview} previous={source.latest} />
            )}
            {busy && (
              <div role="status" className="flex items-center gap-2">
                <SvgSimpleLoader />
                <Text font="main-ui-body" color="text-03">
                  {t("processing")}
                </Text>
              </div>
            )}
            {error && (
              <div role="alert">
                <Text font="main-ui-body" color="status-error-05">
                  {error}
                </Text>
              </div>
            )}
          </div>
        </SideModal.Body>
        <SideModal.Footer>
          <BasicModalFooter
            cancel={
              <Button prominence="secondary" onClick={onClose} disabled={busy}>
                {t("cancel")}
              </Button>
            }
            submit={
              <Button onClick={submit} disabled={!file || busy}>
                {busy
                  ? t("processing")
                  : needsPreview && !preview
                    ? COPY.sources.preview.check
                    : needsPreview
                      ? COPY.sources.preview.confirm
                      : t("startImport")}
              </Button>
            }
          />
        </SideModal.Footer>
      </SideModal.Content>
    </SideModal>
  );
}

export function ImportDetail({
  result,
  sourceKey,
}: {
  result: ClientImport;
  /** Lets each problem open its rows; without it only the counts show. */
  sourceKey?: string;
}) {
  const [openCode, setOpenCode] = useState<string | null>(null);
  const t = useTranslations("dataSources");
  const format = useFormatter();
  const copy = COPY.sources.detail;
  const isNg = result.downstream.includes("financial_review");
  const fileSize =
    result.size_bytes >= 1024 * 1024
      ? `${format.number(result.size_bytes / (1024 * 1024), {
          maximumFractionDigits: 1,
        })} MB`
      : result.size_bytes >= 1024
        ? `${format.number(result.size_bytes / 1024, {
            maximumFractionDigits: 1,
          })} KB`
        : `${format.number(result.size_bytes)} B`;
  const metadata = [
    result.filename || t("unprocessedFile"),
    // Browser time zone, like every other date on the screen.
    formatRelativeDateTime(result.finished_at ?? result.started_at),
    result.size_bytes > 0 ? fileSize : "",
  ]
    .filter(Boolean)
    .join(" · ");
  const status =
    result.status === "SUCCEEDED" && result.rejected === 0
      ? t("completed")
      : result.status === "RUNNING"
        ? t("processingStatus")
        : result.status === "FAILED"
          ? t("failed")
          : t("attention");
  const labelled = result.diagnostics.map((item) => {
    const key = Object.entries(IMPORT_DIAGNOSTIC_KEYS).find(
      ([code]) => code === item.code
    )?.[1];
    return {
      ...item,
      label: key ? t(`diagnostics.${key}`) : t("diagnostics.other"),
    };
  });
  // What the reader skipped on purpose is not a pending item.
  const actionable = labelled.filter(
    (item) => !isInformationalDiagnostic(item.code)
  );
  const informational = labelled.filter((item) =>
    isInformationalDiagnostic(item.code)
  );
  const toDecide = result.needs_review;
  const metrics: [string, number | null][] = [
    [copy.imported, result.imported],
    [copy.rejected, result.rejected],
    // Only the upload response knows the count; history rows do not.
    ...(isNg && toDecide !== null
      ? ([[copy.toDecide, toDecide]] as [string, number | null][])
      : []),
  ];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <Text as="h2" font="heading-h3" color="text-05">
          {status}
        </Text>
        <Text font="secondary-body" color="text-03">
          {metadata}
        </Text>
      </div>
      {result.status === "FAILED" && (
        <Text font="main-ui-body" color="status-error-05">
          {result.failure_reason === "INVALID_FILE"
            ? t("invalidFileFailure")
            : t("processingFailure")}
        </Text>
      )}
      <dl className="flex flex-wrap gap-x-8 gap-y-3">
        {metrics.map(([label, count]) => (
          <div key={label} className="flex flex-col">
            <dt className="ton-eyebrow">{label}</dt>
            <dd>
              <Text font="heading-h3" color="text-05">
                {count === null ? "—" : format.number(count)}
              </Text>
            </dd>
          </div>
        ))}
      </dl>
      {actionable.length > 0 && (
        <section className="flex flex-col gap-1.5">
          <Text as="h3" font="main-ui-action" color="text-05">
            {copy.actionableTitle}
          </Text>
          <ul className="flex flex-col divide-y divide-border-01 rounded-12 border border-01">
            {actionable.map((item) => {
              const open = openCode === item.code;
              const label = (
                <>
                  <span className="flex-1 min-w-0">
                    <Text font="main-ui-body" color="text-05">
                      {item.label}
                    </Text>
                  </span>
                  <Text font="main-ui-action" color="text-04">
                    {format.number(item.count)}
                  </Text>
                  {sourceKey && (
                    <Text font="secondary-action" color="text-03">
                      {open ? copy.problems.hide : copy.problems.show}
                    </Text>
                  )}
                </>
              );
              return (
                <li key={item.code} className="flex flex-col">
                  {sourceKey ? (
                    <button
                      type="button"
                      aria-expanded={open}
                      className="ton-row-link ton-focusable flex w-full items-center gap-4 px-3 py-2 text-start"
                      onClick={() => setOpenCode(open ? null : item.code)}
                    >
                      {label}
                    </button>
                  ) : (
                    <div className="flex items-center gap-4 px-3 py-2">
                      {label}
                    </div>
                  )}
                  {open && sourceKey && (
                    <div className="px-3 pb-3">
                      <ProblemRows
                        sourceKey={sourceKey}
                        importId={result.id}
                        code={item.code}
                      />
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        </section>
      )}
      {informational.length > 0 && (
        <details className="ton-import-notes">
          <summary className="ton-focusable">
            <Text font="secondary-action" color="text-03">
              {copy.informational(
                informational.reduce((sum, item) => sum + item.count, 0)
              )}
            </Text>
          </summary>
          <ul className="flex flex-col gap-1 pt-2">
            {informational.map((item) => (
              <li key={item.code} className="flex justify-between gap-4">
                <Text font="secondary-body" color="text-03">
                  {item.label}
                </Text>
                <Text font="secondary-body" color="text-03">
                  {format.number(item.count)}
                </Text>
              </li>
            ))}
          </ul>
        </details>
      )}
      <Text as="p" font="secondary-body" color="text-03">
        {result.readiness_status === "PENDING_INPUTS"
          ? t("readinessPending")
          : result.readiness_status === "FAILED"
            ? t("readinessFailed")
            : isNg
              ? copy.nextNg
              : copy.nextOther}
      </Text>
      <div className="flex flex-wrap gap-2">
        {SHOW_UPSTREAM_SCREENS && (
          <Button
            href={
              result.readiness_run_id
                ? `/admin/financial-readiness?normalization=${result.readiness_run_id}`
                : "/admin/financial-readiness"
            }
            prominence="secondary"
          >
            {t("readiness")}
          </Button>
        )}
        {result.status !== "FAILED" && (
          <Button
            href={
              isNg
                ? pendingQueueHref({ blocker: "REVIEW_UNRESOLVED" })
                : pendingQueueHref({})
            }
          >
            {copy.openPending}
          </Button>
        )}
        <Button
          href="/ton/dre"
          prominence={result.status !== "FAILED" ? "secondary" : "primary"}
        >
          {copy.openDre}
        </Button>
      </div>
    </div>
  );
}

function DataSourcesPage() {
  const t = useTranslations("dataSources");
  const controladoria = useTranslations("controladoria");
  const format = useFormatter();
  const { user } = useUser();
  const canRead = hasPermission(
    user?.effective_permissions ?? [],
    Permission.READ_TON_SOURCES
  );
  const sources = useSWR<ClientSource[]>(
    canRead ? "/api/ton/data-sources" : null,
    errorHandlingFetcher
  );
  const [uploadSource, setUploadSource] = useState<ClientSource | null>(null);
  const [selected, setSelected] = useState<ClientImport | null>(null);

  return (
    <SettingsLayouts.Root width="lg">
      <SettingsLayouts.Header
        icon={SvgFiles}
        title={t("title")}
        description={t("description")}
        divider
      />
      <SettingsLayouts.Body>
        <div className="flex flex-wrap gap-2 pb-6">
          <Button href="/ton/controladoria" prominence="secondary">
            {controladoria("title")}
          </Button>
          <Button href="/ton/data-sources" prominence="secondary">
            {t("title")}
          </Button>
          <Button href="/ton/pendencias" prominence="secondary">
            {t("readiness")}
          </Button>
          <Button href="/ton/dre" prominence="secondary">
            {t("dre")}
          </Button>
        </div>
        {!canRead && (
          <Text font="main-ui-body" color="text-03">
            {t("noAccess")}
          </Text>
        )}
        {sources.isLoading && (
          <div role="status" className="flex items-center gap-2">
            <SvgSimpleLoader />
            <Text font="main-ui-body" color="text-03">
              {t("loading")}
            </Text>
          </div>
        )}
        {sources.error && (
          <Text font="main-ui-body" color="status-error-05">
            {t("loadError")}
          </Text>
        )}
        {sources.data?.length === 0 && (
          <Text font="main-ui-body" color="text-03">
            {t("empty")}
          </Text>
        )}
        {sources.data?.map((source) => (
          <section
            key={source.key}
            className="border-b border-01 py-6 first:pt-0"
          >
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="flex max-w-xl flex-col gap-1">
                <Text as="h2" font="heading-h3" color="text-05">
                  {source.name}
                </Text>
                <Text font="main-ui-body" color="text-03">
                  {source.description}
                </Text>
              </div>
              {source.can_import && (
                <Button
                  onClick={() => setUploadSource(source)}
                  icon={SvgUploadCloud}
                >
                  {source.latest ? t("updateData") : t("addFile")}
                </Button>
              )}
            </div>
            <div className="grid gap-4 pt-5 md:grid-cols-4">
              <div className="flex flex-col gap-1">
                <Text font="secondary-body" color="text-03">
                  {t("status")}
                </Text>
                <TonStatusTag status={source.status} />
              </div>
              <div className="flex flex-col gap-1">
                <Text font="secondary-body" color="text-03">
                  {t("method")}
                </Text>
                <Text font="main-ui-body" color="text-05">
                  {t("uploadMethod", { format: source.format })}
                </Text>
              </div>
              <div className="flex flex-col gap-1">
                <Text font="secondary-body" color="text-03">
                  {t("lastSuccess")}
                </Text>
                <Text font="main-ui-body" color="text-05">
                  {source.last_success_at
                    ? format.dateTime(new Date(source.last_success_at), {
                        dateStyle: "short",
                        timeStyle: "short",
                      })
                    : t("never")}
                </Text>
              </div>
              <div className="flex flex-col gap-1">
                <Text font="secondary-body" color="text-03">
                  {t("lastAttempt")}
                </Text>
                <Text font="main-ui-body" color="text-05">
                  {source.last_attempt_at
                    ? format.dateTime(new Date(source.last_attempt_at), {
                        dateStyle: "short",
                        timeStyle: "short",
                      })
                    : t("never")}
                </Text>
              </div>
            </div>
            {source.latest && (
              <div className="flex flex-wrap items-center gap-4 pt-4">
                <Text font="secondary-body" color="text-03">
                  {source.latest.filename || t("unprocessedFile")}
                </Text>
                <Text font="secondary-body" color="text-03">
                  {t("importedCount", { count: source.latest.imported })}
                </Text>
                <Text font="secondary-body" color="text-03">
                  {t("warningCount", {
                    count: source.latest.warnings + source.latest.errors,
                  })}
                </Text>
              </div>
            )}
            {source.history.length > 0 && (
              <details className="pt-4">
                <summary>
                  <Text font="main-ui-action" color="text-05">
                    {t("history")}
                  </Text>
                </summary>
                <div className="overflow-x-auto pt-3">
                  <table className="w-full" aria-label={t("history")}>
                    <thead>
                      <tr>
                        <th className="p-2 text-start">
                          <Text font="secondary-action">
                            {t("lastAttempt")}
                          </Text>
                        </th>
                        <th className="p-2 text-start">
                          <Text font="secondary-action">{t("chooseFile")}</Text>
                        </th>
                        <th className="p-2 text-start">
                          <Text font="secondary-action">{t("status")}</Text>
                        </th>
                        <th className="p-2 text-start">
                          <Text font="secondary-action">
                            {t("viewDetails")}
                          </Text>
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {source.history.map((item) => (
                        <tr key={item.id} className="border-b border-01">
                          <td className="p-2">
                            <Text font="secondary-body" color="text-03">
                              {format.dateTime(new Date(item.started_at), {
                                dateStyle: "short",
                                timeStyle: "short",
                              })}
                            </Text>
                          </td>
                          <td className="p-2">
                            <Text font="main-ui-body" color="text-05">
                              {item.filename || t("unprocessedFile")}
                            </Text>
                          </td>
                          <td className="p-2">
                            <Text font="secondary-body" color="text-03">
                              {item.status === "SUCCEEDED" &&
                              item.rejected === 0
                                ? t("completed")
                                : item.status === "RUNNING"
                                  ? t("processingStatus")
                                  : item.status === "FAILED"
                                    ? t("failed")
                                    : t("attention")}
                            </Text>
                            <Text font="secondary-body" color="text-03">
                              {t("importedCount", { count: item.imported })}
                            </Text>
                            <Text font="secondary-body" color="text-03">
                              {t("warningCount", {
                                count: item.warnings + item.errors,
                              })}
                            </Text>
                          </td>
                          <td className="p-2">
                            <Button
                              prominence="tertiary"
                              onClick={() => setSelected(item)}
                            >
                              {t("viewDetails")}
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </details>
            )}
          </section>
        ))}
      </SettingsLayouts.Body>
      {uploadSource && (
        <SourceUpload
          source={uploadSource}
          onClose={() => setUploadSource(null)}
          onComplete={(result) => {
            setUploadSource(null);
            setSelected(result);
            void sources.mutate();
          }}
        />
      )}
      {selected && (
        <SideModal open onOpenChange={(open) => !open && setSelected(null)}>
          <SideModal.Content width="md">
            <SideModal.Header
              title={t("importDetails")}
              onClose={() => setSelected(null)}
            />
            <SideModal.Body>
              <ImportDetail result={selected} />
            </SideModal.Body>
          </SideModal.Content>
        </SideModal>
      )}
    </SettingsLayouts.Root>
  );
}

export default DataSourcesPage;
