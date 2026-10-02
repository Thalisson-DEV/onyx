"use client";

import { useState } from "react";
import { useFormatter, useTranslations } from "next-intl";
import useSWR from "swr";
import { useDropzone } from "react-dropzone";
import { BasicModalFooter, Button, Modal, Text } from "@opal/components";
import { SvgFiles, SvgSimpleLoader, SvgUploadCloud } from "@opal/icons";
import { SettingsLayouts } from "@opal/layouts";
import { cn } from "@opal/utils";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { hasPermission } from "@/lib/permissions";
import { Permission } from "@/lib/types";
import { IMPORT_DIAGNOSTIC_KEYS } from "@/lib/ton/import-diagnostics";
import { useUser } from "@/providers/UserProvider";
import { TonStatusTag } from "@/views/ton/components/TonStatusTag";

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
  const extension = source.format.toLowerCase();
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
    <Modal open onOpenChange={(open) => !open && !busy && onClose()}>
      <Modal.Content width="md">
        <Modal.Header
          icon={SvgUploadCloud}
          title={t("uploadTitle", { source: source.name })}
          description={t("uploadDescription", { format: source.format })}
          onClose={() => !busy && onClose()}
        />
        <Modal.Body>
          {guidance && (
            <div className="pb-4">
              <Text font="main-ui-body" color="text-04">
                {guidance}
              </Text>
            </div>
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
            <Text font="secondary-body" color="text-03">
              {file ? file.name : t("dropFile")}
            </Text>
            {file && (
              <Text font="secondary-body" color="text-03">
                {t("fileReady")}
              </Text>
            )}
          </div>
          {busy && (
            <div role="status" className="flex items-center gap-2 pt-4">
              <SvgSimpleLoader />
              <Text font="main-ui-body" color="text-03">
                {t("processing")}
              </Text>
            </div>
          )}
          {error && (
            <div role="alert" className="pt-4">
              <Text font="main-ui-body" color="status-error-05">
                {error}
              </Text>
            </div>
          )}
        </Modal.Body>
        <Modal.Footer>
          <BasicModalFooter
            cancel={
              <Button prominence="secondary" onClick={onClose} disabled={busy}>
                {t("cancel")}
              </Button>
            }
            submit={
              <Button onClick={submit} disabled={!file || busy}>
                {busy ? t("processing") : t("startImport")}
              </Button>
            }
          />
        </Modal.Footer>
      </Modal.Content>
    </Modal>
  );
}

export function ImportDetail({ result }: { result: ClientImport }) {
  const t = useTranslations("dataSources");
  const format = useFormatter();
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
    result.format,
    format.dateTime(new Date(result.started_at), {
      dateStyle: "short",
      timeStyle: "short",
    }),
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

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center gap-3">
        <Text as="h2" font="heading-h3" color="text-05">
          {status}
        </Text>
        <Text font="secondary-body" color="text-03">
          {result.filename || t("unprocessedFile")}
        </Text>
      </div>
      <Text font="secondary-body" color="text-03">
        {metadata}
      </Text>
      {result.status === "FAILED" && (
        <Text font="main-ui-body" color="status-error-05">
          {result.failure_reason === "INVALID_FILE"
            ? t("invalidFileFailure")
            : t("processingFailure")}
        </Text>
      )}
      <div className="grid grid-cols-2 gap-4 border-y border-01 py-4 md:grid-cols-4">
        {(
          [
            ["imported", result.imported],
            ["rejected", result.rejected],
            ["warnings", result.warnings],
            ["needsReview", result.needs_review],
          ] as const
        ).map(([label, count]) => (
          <div key={label} className="flex flex-col gap-1">
            <Text font="heading-h3" color="text-05">
              {count === null ? "—" : format.number(count)}
            </Text>
            <Text font="secondary-body" color="text-03">
              {t(label)}
            </Text>
          </div>
        ))}
      </div>
      {result.available_for_analysis !== null && (
        <Text font="main-ui-body" color="text-05">
          {t("available", { count: result.available_for_analysis })}
        </Text>
      )}
      <div className="flex flex-col gap-2">
        <Text as="h3" font="main-ui-action" color="text-05">
          {t("diagnosticsTitle")}
        </Text>
        {result.diagnostics.length === 0 ? (
          <Text font="main-ui-body" color="text-03">
            {t("noDiagnostics")}
          </Text>
        ) : (
          result.diagnostics.map((item) => {
            const key = Object.entries(IMPORT_DIAGNOSTIC_KEYS).find(
              ([code]) => code === item.code
            )?.[1];
            return (
              <div
                key={item.code}
                className="flex justify-between gap-4 border-b border-01 py-2"
              >
                <Text font="main-ui-body" color="text-05">
                  {key ? t(`diagnostics.${key}`) : t("diagnostics.other")}
                </Text>
                <Text font="main-ui-body" color="text-03">
                  {format.number(item.count)}
                </Text>
              </div>
            );
          })
        )}
      </div>
      <div className="flex flex-col gap-2">
        <Text as="h3" font="main-ui-action" color="text-05">
          {t("downstreamTitle")}
        </Text>
        {result.downstream.includes("financial_review") && (
          <Text font="main-ui-body" color="text-03">
            {t("reviewAffected")}
          </Text>
        )}
        <Text font="main-ui-body" color="text-03">
          {result.readiness_status === "UPDATED"
            ? t("readinessUpdated")
            : result.readiness_status === "PENDING_INPUTS"
              ? t("readinessPending")
              : result.readiness_status === "FAILED"
                ? t("readinessFailed")
                : t("readinessUnknown")}
        </Text>
        <Text font="main-ui-body" color="text-03">
          {t("dreAffected")}
        </Text>
      </div>
      <div className="flex flex-wrap gap-2">
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
        <Button href="/ton/dre" prominence="secondary">
          {t("dre")}
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
        <Modal open onOpenChange={(open) => !open && setSelected(null)}>
          <Modal.Content width="md">
            <Modal.Header
              title={t("importDetails")}
              onClose={() => setSelected(null)}
            />
            <Modal.Body>
              <ImportDetail result={selected} />
            </Modal.Body>
          </Modal.Content>
        </Modal>
      )}
    </SettingsLayouts.Root>
  );
}

export default DataSourcesPage;
