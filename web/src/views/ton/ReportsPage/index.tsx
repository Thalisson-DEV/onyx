"use client";

import "@/views/ton/chat/assistant.css";

import { useState } from "react";
import type { Route } from "next";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { Button, LineItemButton, Popover, Text } from "@opal/components";
import { SvgDownload, SvgSquarePlus } from "@opal/icons";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { useTonReportGroups } from "@/lib/ton/api";
import { COPY, formatPeriod, formatRelativeDateTime } from "@/lib/ton/copy";
import { getBusinessLabel } from "@/lib/ton/labels";
import type { ArtifactKind } from "@/lib/ton/artifacts";
import type { Publication } from "@/lib/ton/types";
import { ErrorState, LoadingBlock } from "@/views/ton/components/ui";
import {
  FilterBar,
  PageFrame,
  PageHead,
  Tag,
  ViewTabs,
} from "@/views/ton/components/kit";
import { ARTIFACT_ICONS } from "@/views/ton/chat/artifacts/ArtifactCard";
import { CREATE_ITEMS } from "@/views/ton/ChatPage/CreateMenu";

const R = COPY.reports;

export function reportTitle(publication: Publication): string {
  return getBusinessLabel(publication.report_type ?? "MONTHLY_CLOSE");
}

function origin(publication: Publication): string {
  return publication.routine_code
    ? COPY.reports.byRoutine(publication.routine_code)
    : COPY.reports.byAssistant;
}

interface ChatArtifact {
  artifact_id: string;
  artifact_kind: ArtifactKind;
  title: string;
  subtitle: string | null;
  created_at: string;
  versions: number;
  slides: number;
  blocks: number;
  chat_session_id: string;
  chat_name: string | null;
  chat_updated: string;
}

type View = "all" | ArtifactKind | "official";

function artifactHref(item: ChatArtifact): Route {
  const query = new URLSearchParams({
    chatId: item.chat_session_id,
    artefato: item.artifact_id,
  });
  // SAFETY: /ton/chat is a static route; only its query varies.
  return `/ton/chat?${query.toString()}` as Route;
}

/** "Criar com o TON": the chat opens with the chosen result already marked. */
function CreateButton() {
  const router = useRouter();
  return (
    <Popover>
      <Popover.Trigger asChild>
        <Button icon={SvgSquarePlus}>{R.create}</Button>
      </Popover.Trigger>
      <Popover.Content side="bottom" align="end" width="xl">
        <Popover.Menu>
          {CREATE_ITEMS.map((item) => (
            <LineItemButton
              key={item.key}
              sizePreset="main-ui"
              rounding={2}
              icon={ARTIFACT_ICONS[item.key]}
              title={item.label}
              description={item.description}
              onClick={() =>
                // SAFETY: /ton/chat is a static route; only its query varies.
                router.push(`/ton/chat?criar=${item.key}` as Route)
              }
            />
          ))}
        </Popover.Menu>
      </Popover.Content>
    </Popover>
  );
}

function ArtifactRows({ rows }: { rows: ChatArtifact[] }) {
  const router = useRouter();
  return (
    <table className="tp-table">
      <thead>
        <tr>
          <th scope="col">{R.columns.title}</th>
          <th scope="col">{R.columns.kind}</th>
          <th scope="col">{R.columns.conversation}</th>
          <th scope="col" className="tp-end">
            {R.columns.versions}
          </th>
          <th scope="col">{R.columns.updated}</th>
          <th scope="col">
            <span className="sr-only">{R.openChat}</span>
          </th>
        </tr>
      </thead>
      <tbody>
        {rows.map((item) => {
          const Icon = ARTIFACT_ICONS[item.artifact_kind];
          const href = artifactHref(item);
          return (
            <tr
              key={item.artifact_id}
              className="tp-row"
              tabIndex={0}
              aria-label={item.title}
              onClick={() => router.push(href)}
              onKeyDown={(event) => {
                if (event.key === "Enter") router.push(href);
              }}
            >
              <td className="tp-wrap">
                <span className="tp-strong block">{item.title}</span>
                <span className="tp-muted block">
                  {item.subtitle ??
                    (item.artifact_kind === "apresentacao"
                      ? R.meta.slides(item.slides)
                      : R.meta.blocks(item.blocks))}
                </span>
              </td>
              <td>
                <span className="inline-flex items-center gap-2">
                  <Icon size={14} aria-hidden />
                  {COPY.artifacts.kinds[item.artifact_kind]}
                </span>
              </td>
              <td className="tp-muted tp-wrap">
                {item.chat_name || COPY.chat.header.untitled}
              </td>
              <td className="tp-end">{item.versions}</td>
              <td className="tp-muted">
                {item.created_at ? formatRelativeDateTime(item.created_at) : ""}
              </td>
              <td className="tp-end">
                <Button href={href} size="sm" prominence="secondary">
                  {R.openChat}
                </Button>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function OfficialRows() {
  const reports = useTonReportGroups();
  if (reports.isLoading) return <LoadingBlock label={COPY.common.loading} />;
  if (reports.error) return <ErrorState onRetry={() => reports.mutate()} />;
  const groups = reports.data ?? [];
  return (
    <>
      <div className="px-4 pt-3 pb-2">
        <Text font="secondary-body" color="text-03">
          {groups.length ? R.officialHint : R.empty}
        </Text>
      </div>
      {groups.length > 0 && (
        <div className="overflow-x-auto border-t border-01">
          <table className="tp-table">
            <thead>
              <tr>
                <th scope="col">{R.officialColumns.report}</th>
                <th scope="col">{R.officialColumns.period}</th>
                <th scope="col">{R.officialColumns.origin}</th>
                <th scope="col">{R.officialColumns.status}</th>
                <th scope="col">
                  <span className="sr-only">{R.open}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {groups.map(({ latest }) => (
                <tr key={latest.revision_id}>
                  <td className="tp-wrap">
                    <span className="tp-strong block">
                      {reportTitle(latest)}
                    </span>
                    <span className="tp-muted block">
                      {R.generatedAt(
                        formatRelativeDateTime(latest.output.generated_at)
                      )}
                    </span>
                  </td>
                  <td className="tp-muted">
                    {`${formatPeriod(latest.output.period)} · ${latest.output.scope}`}
                  </td>
                  <td className="tp-muted">{origin(latest)}</td>
                  <td>
                    <Tag>{getBusinessLabel(latest.status)}</Tag>
                  </td>
                  <td className="tp-end">
                    <span className="inline-flex gap-1">
                      <Button
                        href={latest.download_url}
                        size="sm"
                        prominence="tertiary"
                        icon={SvgDownload}
                        tooltip={R.download}
                        aria-label={R.download}
                      />
                      <Button
                        href={latest.report_url}
                        size="sm"
                        prominence="secondary"
                      >
                        {R.open}
                      </Button>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

/**
 * What the TON built in conversations: dashboards, decks and reports, one
 * row each at its latest version. The formal closing reports stay a view.
 */
export default function ReportsPage() {
  const artifacts = useSWR<ChatArtifact[]>(
    "/api/ton/agent/artifacts",
    errorHandlingFetcher
  );
  const [view, setView] = useState<View>("all");
  const [search, setSearch] = useState("");
  const list = artifacts.data ?? [];
  const count = (kind: ArtifactKind) =>
    list.filter((item) => item.artifact_kind === kind).length;
  const needle = search.trim().toLocaleLowerCase("pt-BR");
  const rows = list.filter(
    (item) =>
      (view === "all" || item.artifact_kind === view) &&
      (!needle ||
        `${item.title} ${item.subtitle ?? ""} ${item.chat_name ?? ""}`
          .toLocaleLowerCase("pt-BR")
          .includes(needle))
  );
  return (
    <PageFrame>
      <PageHead
        title={R.title}
        description={R.description}
        actions={<CreateButton />}
      />
      <ViewTabs
        label={R.title}
        value={view}
        onChange={setView}
        views={[
          { key: "all", label: R.views.all, count: list.length },
          { key: "painel", label: R.views.painel, count: count("painel") },
          {
            key: "apresentacao",
            label: R.views.apresentacao,
            count: count("apresentacao"),
          },
          {
            key: "relatorio",
            label: R.views.relatorio,
            count: count("relatorio"),
          },
          { key: "official", label: R.views.official, tone: "neutral" },
        ]}
      />
      <section className="tn-card" aria-label={R.title}>
        {view === "official" ? (
          <OfficialRows />
        ) : (
          <>
            <div className="px-4 pt-3 pb-3">
              <FilterBar
                search={{
                  value: search,
                  onChange: setSearch,
                  placeholder: R.search,
                }}
              />
            </div>
            {artifacts.isLoading && (
              <LoadingBlock label={COPY.common.loading} />
            )}
            {artifacts.error && (
              <ErrorState onRetry={() => artifacts.mutate()} />
            )}
            {artifacts.data && rows.length === 0 && (
              <div className="px-4 pb-4">
                <Text font="secondary-body" color="text-03">
                  {list.length ? R.noMatch : R.emptyArtifacts}
                </Text>
              </div>
            )}
            {rows.length > 0 && (
              <div className="overflow-x-auto border-t border-01">
                <ArtifactRows rows={rows} />
              </div>
            )}
          </>
        )}
      </section>
    </PageFrame>
  );
}
