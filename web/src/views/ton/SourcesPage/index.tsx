"use client";

import { useState } from "react";
import { Button, Text } from "@opal/components";
import {
  SvgChevronDown,
  SvgLock,
  SvgServer,
  SvgUploadCloud,
} from "@opal/icons";
import { useTonClosing, useTonDataSources } from "@/lib/ton/api";
import { COPY, formatNumber, formatRelativeDateTime } from "@/lib/ton/copy";
import { getBusinessLabel } from "@/lib/ton/labels";
import type { ClientImport, ClientSource } from "@/lib/ton/types";
import { ImportDetail, SourceUpload } from "@/views/ton/DataSourcesPage";
import {
  IconTile,
  LoadingBlock,
  PageContainer,
  PageHeader,
  StatusDot,
  StatusPill,
  TonCard,
  sourceTone,
} from "@/views/ton/components/ui";

const NG_SOURCE = "financial_launches";

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5 min-w-0">
      <span className="ton-eyebrow">{label}</span>
      <Text font="main-ui-action" color="text-05">
        {value}
      </Text>
    </div>
  );
}

interface SourceCardProps {
  source: ClientSource;
  directIntegration: string | undefined;
  onUpload: (source: ClientSource) => void;
  justImported: ClientImport | null;
}

function SourceCard({
  source,
  directIntegration,
  onUpload,
  justImported,
}: SourceCardProps) {
  const [historyOpen, setHistoryOpen] = useState(false);
  const [selected, setSelected] = useState<ClientImport | null>(null);
  const latest = source.latest;
  const isNg = source.key === NG_SOURCE;
  const detail = justImported ?? selected;
  return (
    <TonCard as="article" className="flex flex-col gap-4 p-5">
      <div className="flex flex-wrap items-start gap-4">
        <IconTile icon={SvgServer} size="lg" />
        <div className="flex flex-col gap-1 min-w-0 flex-1">
          <Text as="h2" font="heading-h3" color="text-05">
            {source.name}
          </Text>
          <Text font="secondary-body" color="text-03">
            {source.description}
          </Text>
        </div>
        <StatusPill tone={sourceTone(source.status)}>
          {getBusinessLabel(source.status)}
        </StatusPill>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 rounded-12 bg-background-neutral-01 p-4">
        <Fact
          label={COPY.sources.acquisition}
          value={COPY.sources.fileFormat(source.format)}
        />
        <Fact
          label={COPY.sources.lastUpdate}
          value={
            source.last_success_at
              ? formatRelativeDateTime(source.last_success_at)
              : COPY.sources.never
          }
        />
        <Fact
          label={COPY.sources.records}
          value={latest ? formatNumber(latest.imported) : "—"}
        />
        <Fact
          label={COPY.sources.warnings}
          value={latest ? formatNumber(latest.warnings + latest.errors) : "—"}
        />
      </div>

      <div className="flex items-start gap-3 rounded-12 border border-dashed border-02 p-3">
        <IconTile icon={SvgLock} size="sm" tone="neutral" />
        <div className="flex flex-col gap-0.5 min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <Text font="main-ui-action" color="text-05">
              {COPY.sources.directTitle}
            </Text>
            <StatusPill tone="neutral">
              {isNg
                ? (directIntegration ?? COPY.sources.pendingAccess)
                : (directIntegration ?? COPY.sources.directNotConfigured)}
            </StatusPill>
          </div>
          <Text font="secondary-body" color="text-03">
            {isNg
              ? COPY.sources.directExplainNg
              : COPY.sources.directExplainOther}
          </Text>
        </div>
      </div>

      {latest && latest.downstream.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="ton-eyebrow">{COPY.sources.usedBy}</span>
          {latest.downstream.map((item) => (
            <StatusPill key={item} tone="brand">
              {COPY.sources.downstream[item] ?? getBusinessLabel(item)}
            </StatusPill>
          ))}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        {source.can_import && source.source_id && (
          <Button icon={SvgUploadCloud} onClick={() => onUpload(source)}>
            {COPY.sources.update}
          </Button>
        )}
        {source.history.length > 0 && (
          <Button
            prominence="tertiary"
            rightIcon={SvgChevronDown}
            onClick={() => setHistoryOpen((value) => !value)}
          >
            {historyOpen
              ? COPY.sources.hideHistory
              : `${COPY.sources.history} (${source.history.length})`}
          </Button>
        )}
      </div>

      {historyOpen && (
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
                  tone={item.status === "SUCCEEDED" ? "success" : "warning"}
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
      )}
      {detail && (
        <div className="rounded-12 border border-01 p-4">
          <ImportDetail result={detail} />
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
      {sources.error && (
        <TonCard className="p-5">
          <Text font="main-ui-body" color="text-03">
            {COPY.common.error}
          </Text>
        </TonCard>
      )}
      <div className="flex flex-col gap-4">
        {sources.data?.map((source) => (
          <SourceCard
            key={source.key}
            source={source}
            directIntegration={
              closing.data?.sources.find((item) => item.key === source.key)
                ?.direct_integration
            }
            onUpload={setUploadSource}
            justImported={imported?.key === source.key ? imported.result : null}
          />
        ))}
      </div>
      {uploadSource && (
        <SourceUpload
          source={uploadSource}
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
