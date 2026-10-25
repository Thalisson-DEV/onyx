"use client";

import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Button, Text } from "@opal/components";
import {
  SvgAlertTriangle,
  SvgCheckCircle,
  SvgClipboard,
  SvgUploadCloud,
} from "@opal/icons";
import { useTonClosing, useTonDataSources } from "@/lib/ton/api";
import {
  COPY,
  formatNumber,
  formatPeriod,
  formatRelativeDateTime,
} from "@/lib/ton/copy";
import { getBusinessLabel } from "@/lib/ton/labels";
import { summarizeSources } from "@/lib/ton/sources";
import type { ClientImport, ClientSource } from "@/lib/ton/types";
import { ImportDetail, SourceUpload } from "@/views/ton/DataSourcesPage";
import PasteTable, { PASTE_COLUMNS } from "@/views/ton/SourcesPage/PasteTable";
import {
  ErrorState,
  LoadingBlock,
  StatusDot,
  sourceTone,
} from "@/views/ton/components/ui";
import {
  Drawer,
  DrawerSection,
  PageFrame,
  PageHead,
  Tag,
  TonMark,
  type TagTone,
} from "@/views/ton/components/kit";

const NG_SOURCE = "financial_launches";

/** One line that says whether the DRE can trust its sources today. */
function HealthLine({
  sources,
  ngDirect,
}: {
  sources: ClientSource[];
  ngDirect: string | undefined;
}) {
  const { required, imported, attention, latest, healthy } =
    summarizeSources(sources);
  const missing = required.length - imported.length;
  const headline = healthy
    ? COPY.sources.health.healthy
    : imported.length === 0
      ? COPY.sources.health.empty
      : missing > 0
        ? COPY.sources.health.missing(missing)
        : COPY.sources.health.attention(attention.length);
  return (
    <div className="tn-statusline" data-tone={healthy ? "ok" : "warn"}>
      {healthy ? <SvgCheckCircle size={16} /> : <SvgAlertTriangle size={16} />}
      <span className="font-semibold">{headline}</span>
      <span className="tn-statusline-meta">
        {COPY.sources.statusMeta(
          imported.length,
          required.length,
          latest ? formatRelativeDateTime(latest) : COPY.sources.never
        )}
      </span>
      <span className="tn-spacer" />
      <span className="tn-statusline-meta">{COPY.sources.health.nowTitle}</span>
      <Tag tone="ok">{COPY.sources.health.nowBadge}</Tag>
      <span className="tn-statusline-meta">
        {COPY.sources.health.nextTitle}
      </span>
      <Tag>{ngDirect ?? COPY.sources.health.nextBadge}</Tag>
    </div>
  );
}

function statusTone(status: string): TagTone {
  const tone = sourceTone(status);
  return tone === "success"
    ? "ok"
    : tone === "danger"
      ? "danger"
      : tone === "warning"
        ? "warn"
        : tone === "brand"
          ? "info"
          : "neutral";
}

interface SourceDrawerProps {
  source: ClientSource;
  directIntegration: string | undefined;
  justImported: ClientImport | null;
  onUpload: (source: ClientSource) => void;
  onPaste: (source: ClientSource) => void;
  onClose: () => void;
}

/** Everything about one source: how it arrives, its imports, what failed. */
function SourceDrawer({
  source,
  directIntegration,
  justImported,
  onUpload,
  onPaste,
  onClose,
}: SourceDrawerProps) {
  const latest = source.latest;
  const [selected, setSelected] = useState<ClientImport | null>(
    justImported ?? latest
  );
  const isNg = source.key === NG_SOURCE;
  return (
    <Drawer
      open
      onClose={onClose}
      storageKey="source"
      defaultWidth={760}
      eyebrow={COPY.sources.title}
      title={source.name}
      description={source.description}
      summary={
        <>
          <div className="tn-stat">
            <span className="tn-stat-label">{COPY.sources.lastUpdate}</span>
            <span className="tn-figure-sm">
              {source.last_success_at
                ? formatRelativeDateTime(source.last_success_at)
                : COPY.sources.never}
            </span>
          </div>
          <div className="tn-stat">
            <span className="tn-stat-label">{COPY.sources.records}</span>
            <span className="tn-figure-sm">
              {latest ? formatNumber(latest.imported) : "—"}
            </span>
          </div>
          <div className="tn-stat">
            <span className="tn-stat-label">{COPY.sources.rejectedShort}</span>
            <span className="tn-figure-sm">
              {latest ? formatNumber(latest.rejected) : "—"}
            </span>
          </div>
          <Tag tone={statusTone(source.status)}>
            {getBusinessLabel(source.status)}
          </Tag>
        </>
      }
      footer={
        <>
          <span className="tn-spacer" />
          {source.can_import && PASTE_COLUMNS[source.key] && (
            <Button
              prominence="secondary"
              icon={SvgClipboard}
              onClick={() => onPaste(source)}
            >
              {COPY.sources.pasteOpen}
            </Button>
          )}
          {source.can_import && (
            <Button icon={SvgUploadCloud} onClick={() => onUpload(source)}>
              {COPY.sources.update}
            </Button>
          )}
        </>
      }
    >
      <DrawerSection title={COPY.sources.acquisition}>
        <Text font="main-ui-body" color="text-05">
          {COPY.sources.fileFormat(source.format)}
        </Text>
        {latest && latest.downstream.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5">
            <Text font="secondary-body" color="text-03">
              {COPY.sources.usedBy}
            </Text>
            {latest.downstream.map((item) => (
              <Tag key={item} tone="brand">
                {COPY.sources.downstream[item] ?? getBusinessLabel(item)}
              </Tag>
            ))}
          </div>
        )}
      </DrawerSection>
      <DrawerSection title={COPY.sources.directTitle}>
        <span className="flex flex-wrap items-center gap-2">
          <Tag>
            {isNg
              ? (directIntegration ?? COPY.sources.pendingAccess)
              : (directIntegration ?? COPY.sources.directNotConfigured)}
          </Tag>
        </span>
        <Text font="secondary-body" color="text-03">
          {isNg
            ? COPY.sources.directExplainNg
            : COPY.sources.directExplainOther}
        </Text>
      </DrawerSection>
      {source.history.length > 0 && (
        <DrawerSection
          title={`${COPY.sources.history} (${source.history.length})`}
        >
          <div className="flex flex-col">
            {source.history.map((item) => (
              <button
                key={item.id}
                type="button"
                className="tn-kv ton-focusable"
                aria-pressed={selected?.id === item.id}
                onClick={() =>
                  setSelected(selected?.id === item.id ? null : item)
                }
              >
                <StatusDot
                  tone={
                    item.status === "SUCCEEDED"
                      ? "success"
                      : item.status === "FAILED"
                        ? "danger"
                        : "warning"
                  }
                />
                <span className="flex-1 min-w-0 text-start truncate">
                  {item.filename}
                </span>
                <span className="tn-hint">
                  {`${COPY.sources.importedRows(item.imported, item.rejected)} · ${formatRelativeDateTime(item.finished_at ?? item.started_at)}`}
                </span>
              </button>
            ))}
          </div>
        </DrawerSection>
      )}
      {selected && (
        <DrawerSection title={COPY.sources.importDetail}>
          <ImportDetail result={selected} sourceKey={source.key} />
        </DrawerSection>
      )}
    </Drawer>
  );
}

export default function SourcesPage() {
  const sources = useTonDataSources();
  const closing = useTonClosing();
  const [uploadSource, setUploadSource] = useState<ClientSource | null>(null);
  const [pasteSource, setPasteSource] = useState<ClientSource | null>(null);
  const [imported, setImported] = useState<{
    key: string;
    result: ClientImport;
  } | null>(null);
  const searchParams = useSearchParams();
  const requested = searchParams.get("importar");
  const until = searchParams.get("ate");
  const focusedKey = searchParams.get("detalhe");
  // The source whose details are open; a link can ask for one directly.
  const [openKey, setOpenKey] = useState<string | null>(focusedKey);
  const opened = useRef(false);
  // Workflows such as missing actuals link straight to the right upload.
  useEffect(() => {
    if (opened.current || !requested || !sources.data) return;
    const match = sources.data.find((item) => item.key === requested);
    if (match) {
      opened.current = true;
      setUploadSource(match);
    }
  }, [requested, sources.data]);
  function guidanceFor(source: ClientSource): string | undefined {
    if (source.key !== NG_SOURCE) return undefined;
    if (until && /^\d{4}-\d{2}$/.test(until)) {
      const from = formatPeriod(`${until.slice(0, 4)}-01-01`).toLowerCase();
      const to = formatPeriod(`${until}-01`).toLowerCase();
      return COPY.decisionLoop.uploadGuidance.ngRange(`de ${from} a ${to}`);
    }
    return COPY.decisionLoop.uploadGuidance.ng;
  }
  const directFor = (key: string) =>
    closing.data?.sources.find((item) => item.key === key)?.direct_integration;

  const open = sources.data?.find((item) => item.key === openKey) ?? null;
  const summary = sources.data ? summarizeSources(sources.data) : null;

  return (
    <PageFrame>
      <PageHead
        title={COPY.sources.title}
        description={COPY.sources.description}
        status={
          summary ? (
            <Tag tone={summary.healthy ? "ok" : "warn"}>
              {summary.healthy
                ? COPY.sources.health.current
                : COPY.sources.health.withRejections(summary.attention.length)}
            </Tag>
          ) : undefined
        }
      />
      {sources.isLoading && <LoadingBlock label={COPY.common.loading} />}
      {sources.error && <ErrorState onRetry={() => sources.mutate()} />}
      {sources.data && (
        <>
          <HealthLine sources={sources.data} ngDirect={directFor(NG_SOURCE)} />
          <section className="tn-card" aria-label={COPY.sources.listTitle}>
            <div className="overflow-x-auto">
              <table className="tp-table">
                <thead>
                  <tr>
                    <th scope="col">{COPY.sources.table.source}</th>
                    <th scope="col">{COPY.sources.table.status}</th>
                    <th scope="col">{COPY.sources.updatedShort}</th>
                    <th scope="col" className="tp-end">
                      {COPY.sources.records}
                    </th>
                    <th scope="col" className="tp-end">
                      {COPY.sources.rejectedShort}
                    </th>
                    <th scope="col">
                      <span className="sr-only">
                        {COPY.sources.table.actions}
                      </span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {sources.data.map((source) => {
                    const latest = source.latest;
                    const rejected = latest ? latest.rejected : 0;
                    return (
                      <tr
                        key={source.key}
                        className="tp-row"
                        tabIndex={0}
                        aria-label={COPY.sources.showDetails(source.name)}
                        onClick={() => setOpenKey(source.key)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter") setOpenKey(source.key);
                        }}
                      >
                        <td className="tp-wrap">
                          <span className="flex flex-col">
                            <span className="tp-strong">{source.name}</span>
                            <span className="tp-muted">
                              {source.description}
                            </span>
                          </span>
                        </td>
                        <td>
                          <Tag tone={statusTone(source.status)}>
                            {getBusinessLabel(source.status)}
                          </Tag>
                        </td>
                        <td className="tp-muted">
                          {source.last_success_at
                            ? formatRelativeDateTime(source.last_success_at)
                            : COPY.sources.never}
                        </td>
                        <td className="tp-end tn-num">
                          {latest ? formatNumber(latest.imported) : "—"}
                        </td>
                        <td className="tp-end tn-num">
                          {rejected > 0 ? (
                            <TonMark>{formatNumber(rejected)}</TonMark>
                          ) : latest ? (
                            "0"
                          ) : (
                            "—"
                          )}
                        </td>
                        <td className="tp-end">
                          <span className="inline-flex gap-2">
                            {source.can_import && PASTE_COLUMNS[source.key] && (
                              <Button
                                size="sm"
                                prominence="tertiary"
                                icon={SvgClipboard}
                                onClick={(event) => {
                                  event.stopPropagation();
                                  setPasteSource(source);
                                }}
                              >
                                {COPY.sources.pasteOpen}
                              </Button>
                            )}
                            {source.can_import && (
                              <Button
                                size="sm"
                                prominence="secondary"
                                icon={SvgUploadCloud}
                                onClick={(event) => {
                                  event.stopPropagation();
                                  setUploadSource(source);
                                }}
                              >
                                {COPY.sources.update}
                              </Button>
                            )}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
      {open && (
        <SourceDrawer
          key={`${open.key}-${imported?.key === open.key ? imported.result.id : ""}`}
          source={open}
          directIntegration={directFor(open.key)}
          justImported={imported?.key === open.key ? imported.result : null}
          onUpload={setUploadSource}
          onPaste={setPasteSource}
          onClose={() => setOpenKey(null)}
        />
      )}
      {pasteSource && (
        <PasteTable
          source={pasteSource}
          onClose={() => setPasteSource(null)}
          onComplete={(result) => {
            setImported({ key: pasteSource.key, result });
            setOpenKey(pasteSource.key);
            setPasteSource(null);
            void sources.mutate();
            void closing.mutate();
          }}
        />
      )}
      {uploadSource && (
        <SourceUpload
          source={uploadSource}
          guidance={guidanceFor(uploadSource)}
          onClose={() => setUploadSource(null)}
          onComplete={(result) => {
            setImported({ key: uploadSource.key, result });
            setOpenKey(uploadSource.key);
            setUploadSource(null);
            void sources.mutate();
            void closing.mutate();
          }}
        />
      )}
    </PageFrame>
  );
}
