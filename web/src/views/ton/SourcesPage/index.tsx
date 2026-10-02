"use client";

import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Button, Text } from "@opal/components";
import {
  SvgAlertTriangle,
  SvgCheckCircle,
  SvgChevronDown,
  SvgChevronUp,
  SvgFileText,
  SvgLock,
  SvgServer,
  SvgUploadCloud,
} from "@opal/icons";
import { cn } from "@opal/utils";
import { useTonClosing, useTonDataSources } from "@/lib/ton/api";
import {
  COPY,
  formatNumber,
  formatPeriod,
  formatRelativeDateTime,
} from "@/lib/ton/copy";
import { getBusinessLabel } from "@/lib/ton/labels";
import type { ClientImport, ClientSource } from "@/lib/ton/types";
import { ImportDetail, SourceUpload } from "@/views/ton/DataSourcesPage";
import {
  ErrorState,
  IconTile,
  LoadingBlock,
  Metric,
  PageContainer,
  PageHeader,
  StatusDot,
  StatusPill,
  TonCard,
  sourceTone,
} from "@/views/ton/components/ui";

const NG_SOURCE = "financial_launches";

function HealthSummary({
  sources,
  ngDirect,
}: {
  sources: ClientSource[];
  ngDirect: string | undefined;
}) {
  const configured = sources.filter((source) => source.source_id);
  const current = configured.filter((source) => source.status === "CURRENT");
  const attention = configured.filter(
    (source) => source.status === "ATTENTION" || source.status === "FAILED"
  );
  const latest = configured
    .map((source) => source.last_success_at)
    .filter((value): value is string => !!value)
    .sort()
    .at(-1);
  const healthy = configured.length > 0 && attention.length === 0;
  return (
    <TonCard className="flex flex-col gap-5 p-5 sm:p-6">
      <div className="flex items-start gap-4">
        <IconTile
          icon={healthy ? SvgCheckCircle : SvgAlertTriangle}
          tone={healthy ? "brand" : "warning"}
          size="lg"
        />
        <div className="flex flex-col gap-1 min-w-0">
          <Text as="h2" font="heading-h3" color="text-05">
            {healthy
              ? COPY.sources.health.healthy
              : COPY.sources.health.attention(attention.length)}
          </Text>
          <Text as="p" font="secondary-body" color="text-03">
            {COPY.sources.health.body}
          </Text>
        </div>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Metric
          label={COPY.sources.health.configured}
          value={`${formatNumber(current.length)}/${formatNumber(configured.length)}`}
          detail={COPY.sources.health.current}
          tone={healthy ? "success" : "warning"}
        />
        <Metric
          label={COPY.sources.lastUpdate}
          value={latest ? formatRelativeDateTime(latest) : COPY.sources.never}
        />
        <Metric
          label={COPY.sources.acquisition}
          value={COPY.sources.health.manual}
          detail={COPY.sources.health.manualDetail}
        />
        <Metric
          label={COPY.sources.health.ngDirect}
          value={ngDirect ?? COPY.sources.pendingAccess}
          detail={COPY.sources.health.ngDirectDetail}
          tone="neutral"
        />
      </div>
      <ol
        aria-label={COPY.sources.health.pathLabel}
        className="grid grid-cols-1 md:grid-cols-2 gap-3"
      >
        <li className="flex items-start gap-3 rounded-12 bg-background-neutral-01 p-3">
          <IconTile icon={SvgFileText} size="sm" />
          <div className="flex flex-col gap-0.5">
            <span className="flex items-center gap-2">
              <Text font="secondary-action" color="text-05">
                {COPY.sources.health.nowTitle}
              </Text>
              <StatusPill tone="success">
                {COPY.sources.health.nowBadge}
              </StatusPill>
            </span>
            <Text font="secondary-body" color="text-03">
              {COPY.sources.health.nowBody}
            </Text>
          </div>
        </li>
        <li className="flex items-start gap-3 rounded-12 border border-dashed border-02 p-3">
          <IconTile icon={SvgLock} size="sm" tone="neutral" />
          <div className="flex flex-col gap-0.5">
            <span className="flex items-center gap-2">
              <Text font="secondary-action" color="text-05">
                {COPY.sources.health.nextTitle}
              </Text>
              <StatusPill tone="neutral">
                {COPY.sources.health.nextBadge}
              </StatusPill>
            </span>
            <Text font="secondary-body" color="text-03">
              {COPY.sources.directExplainNg}
            </Text>
          </div>
        </li>
      </ol>
    </TonCard>
  );
}

interface SourceRowProps {
  source: ClientSource;
  directIntegration: string | undefined;
  onUpload: (source: ClientSource) => void;
  justImported: ClientImport | null;
}

function SourceRow({
  source,
  directIntegration,
  onUpload,
  justImported,
}: SourceRowProps) {
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<ClientImport | null>(null);
  const latest = source.latest;
  const isNg = source.key === NG_SOURCE;
  const detail = justImported ?? selected;
  const issues = latest ? latest.warnings + latest.errors : 0;
  return (
    <TonCard as="article" className="flex flex-col">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-3 p-4 sm:p-5">
        <div className="flex items-center gap-3 min-w-0 flex-1 basis-64">
          <IconTile icon={SvgServer} />
          <div className="flex flex-col min-w-0">
            <Text as="h2" font="main-ui-action" color="text-05">
              {source.name}
            </Text>
            <Text font="secondary-body" color="text-03" maxLines={1}>
              {source.description}
            </Text>
          </div>
        </div>
        <dl className="grid grid-cols-3 gap-x-5 gap-y-1 basis-80 grow sm:grow-0">
          <div className="flex flex-col">
            <dt className="ton-eyebrow">{COPY.sources.updatedShort}</dt>
            <dd>
              <Text font="secondary-action" color="text-05">
                {source.last_success_at
                  ? formatRelativeDateTime(source.last_success_at)
                  : COPY.sources.never}
              </Text>
            </dd>
          </div>
          <div className="flex flex-col">
            <dt className="ton-eyebrow">{COPY.sources.records}</dt>
            <dd>
              <Text font="secondary-action" color="text-05">
                {latest ? formatNumber(latest.imported) : "—"}
              </Text>
            </dd>
          </div>
          <div className="flex flex-col">
            <dt className="ton-eyebrow">{COPY.sources.warnings}</dt>
            <dd>
              <span className={cn(issues > 0 && "text-status-warning-05")}>
                <Text
                  font="secondary-action"
                  color={issues > 0 ? "inherit" : "text-05"}
                >
                  {latest ? formatNumber(issues) : "—"}
                </Text>
              </span>
            </dd>
          </div>
        </dl>
        <div className="flex items-center gap-2 ms-auto">
          <StatusPill tone={sourceTone(source.status)}>
            {getBusinessLabel(source.status)}
          </StatusPill>
          {source.can_import && source.source_id && (
            <Button
              size="md"
              icon={SvgUploadCloud}
              onClick={() => onUpload(source)}
            >
              {COPY.sources.update}
            </Button>
          )}
          <Button
            size="md"
            prominence="tertiary"
            icon={open ? SvgChevronUp : SvgChevronDown}
            aria-expanded={open}
            aria-label={
              open
                ? COPY.sources.hideDetails(source.name)
                : COPY.sources.showDetails(source.name)
            }
            onClick={() => setOpen((value) => !value)}
          />
        </div>
      </div>

      {(open || detail) && (
        <div className="flex flex-col gap-4 border-t border-01 p-4 sm:p-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="flex flex-col gap-1 rounded-12 bg-background-neutral-01 p-3">
              <span className="ton-eyebrow">{COPY.sources.acquisition}</span>
              <Text font="secondary-action" color="text-05">
                {COPY.sources.fileFormat(source.format)}
              </Text>
              {latest && latest.downstream.length > 0 && (
                <div className="flex flex-wrap items-center gap-1.5 pt-1">
                  <Text font="secondary-body" color="text-03">
                    {COPY.sources.usedBy}
                  </Text>
                  {latest.downstream.map((item) => (
                    <StatusPill key={item} tone="brand">
                      {COPY.sources.downstream[item] ?? getBusinessLabel(item)}
                    </StatusPill>
                  ))}
                </div>
              )}
            </div>
            <div className="flex flex-col gap-1 rounded-12 border border-dashed border-02 p-3">
              <span className="flex flex-wrap items-center gap-2">
                <span className="ton-eyebrow">{COPY.sources.directTitle}</span>
                <StatusPill tone="neutral">
                  {isNg
                    ? (directIntegration ?? COPY.sources.pendingAccess)
                    : (directIntegration ?? COPY.sources.directNotConfigured)}
                </StatusPill>
              </span>
              <Text font="secondary-body" color="text-03">
                {isNg
                  ? COPY.sources.directExplainNg
                  : COPY.sources.directExplainOther}
              </Text>
            </div>
          </div>

          {source.history.length > 0 && (
            <section className="flex flex-col gap-2">
              <span className="ton-eyebrow">{`${COPY.sources.history} (${source.history.length})`}</span>
              <ul className="flex flex-col divide-y divide-border-01 rounded-12 border border-01">
                {source.history.map((item) => (
                  <li key={item.id}>
                    {/* History rows select an import; Opal has no list-row button. */}
                    <button
                      type="button"
                      onClick={() =>
                        setSelected(selected?.id === item.id ? null : item)
                      }
                      aria-expanded={selected?.id === item.id}
                      className="ton-row-link ton-focusable flex w-full flex-wrap items-center gap-3 px-3 py-2.5 text-start"
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
                      <span className="flex-1 min-w-0">
                        <Text font="secondary-action" color="text-05">
                          {item.filename}
                        </Text>
                      </span>
                      <Text font="secondary-body" color="text-03">
                        {`${COPY.sources.importedRows(item.imported, item.rejected)} · ${formatRelativeDateTime(item.finished_at ?? item.started_at)}`}
                      </Text>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}
          {detail && (
            <div className="rounded-12 border border-01 p-4">
              <ImportDetail result={detail} />
            </div>
          )}
        </div>
      )}
    </TonCard>
  );
}

export default function SourcesPage() {
  const sources = useTonDataSources();
  const closing = useTonClosing();
  const [uploadSource, setUploadSource] = useState<ClientSource | null>(null);
  const [imported, setImported] = useState<{
    key: string;
    result: ClientImport;
  } | null>(null);
  const searchParams = useSearchParams();
  const requested = searchParams.get("importar");
  const until = searchParams.get("ate");
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

  return (
    <PageContainer>
      <PageHeader
        title={COPY.sources.title}
        description={COPY.sources.description}
      />
      {sources.isLoading && (
        <TonCard className="p-5">
          <LoadingBlock label={COPY.common.loading} />
        </TonCard>
      )}
      {sources.error && <ErrorState onRetry={() => sources.mutate()} />}
      {sources.data && (
        <>
          <HealthSummary
            sources={sources.data}
            ngDirect={directFor(NG_SOURCE)}
          />
          <section
            className="flex flex-col gap-3"
            aria-labelledby="ton-sources-list"
          >
            <h2 id="ton-sources-list" className="ton-eyebrow">
              {COPY.sources.listTitle}
            </h2>
            {sources.data.map((source) => (
              <SourceRow
                key={source.key}
                source={source}
                directIntegration={directFor(source.key)}
                onUpload={setUploadSource}
                justImported={
                  imported?.key === source.key ? imported.result : null
                }
              />
            ))}
          </section>
        </>
      )}
      {uploadSource && (
        <SourceUpload
          source={uploadSource}
          guidance={guidanceFor(uploadSource)}
          onClose={() => setUploadSource(null)}
          onComplete={(result) => {
            setImported({ key: uploadSource.key, result });
            setUploadSource(null);
            void sources.mutate();
            void closing.mutate();
          }}
        />
      )}
    </PageContainer>
  );
}
