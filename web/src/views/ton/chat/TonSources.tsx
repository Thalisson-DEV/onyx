"use client";

import Link from "next/link";
import { Text, Tooltip } from "@opal/components";
import { SvgArrowUpRight, SvgServer } from "@opal/icons";
import { COPY } from "@/lib/ton/copy";
import { getBusinessLabel, getStatusTone } from "@/lib/ton/labels";
import {
  safeDateTime,
  type DataOrigin,
  type WorkSource,
} from "@/lib/ton/work-log";

const S = COPY.work.sources;

function pillTone(status: string): string {
  const tone = getStatusTone(status);
  if (tone === "success") return "success";
  if (tone === "warning") return "warning";
  if (tone === "error") return "danger";
  return "neutral";
}

interface SourceGroup {
  id: string;
  label: string;
  tool: WorkSource["tool"];
  items: WorkSource[];
}

/** One chip per kind of data; repeated queries list their subjects on hover. */
function groupSources(sources: WorkSource[]): SourceGroup[] {
  const groups = new Map<string, SourceGroup>();
  for (const source of sources) {
    const group = groups.get(source.label);
    if (group) group.items.push(source);
    else
      groups.set(source.label, {
        id: source.id,
        label: source.label,
        tool: source.tool,
        items: [source],
      });
  }
  return [...groups.values()];
}

function SourceChip({ group, index }: { group: SourceGroup; index: number }) {
  const Icon = group.tool.icon;
  const single = group.items.length === 1 ? group.items[0] : undefined;
  const subject = single ? single.subject : String(group.items.length);
  const name = subject ? `${group.label} · ${subject}` : group.label;
  const tooltip = single
    ? (single.summary ?? undefined)
    : group.items
        .map((item) => [item.subject, item.summary].filter(Boolean).join(": "))
        .filter(Boolean)
        .join(" | ") || undefined;
  return (
    <li>
      <Tooltip side="top" tooltip={tooltip}>
        <Link
          href={group.tool.href}
          className="ton-source-chip"
          aria-label={S.open(name)}
          style={{ animationDelay: `${index * 35}ms` }}
        >
          <span className="ton-source-chip-icon" aria-hidden>
            <Icon />
          </span>
          <Text font="secondary-action" color="inherit" maxLines={1}>
            {group.label}
          </Text>
          {subject && (
            <Text font="secondary-body" color="text-03" maxLines={1}>
              {subject}
            </Text>
          )}
          <SvgArrowUpRight className="ton-source-chip-go" aria-hidden />
        </Link>
      </Tooltip>
    </li>
  );
}

function OriginRow({ origin }: { origin: DataOrigin }) {
  const imported = safeDateTime(origin.importedAt);
  const detail = [
    origin.file,
    imported ? S.imported(imported) : null,
    origin.acquisition,
  ]
    .filter(Boolean)
    .join(" · ");
  return (
    <li className="ton-origin">
      <span className="ton-source-chip-icon" aria-hidden>
        <SvgServer />
      </span>
      <span className="flex min-w-0 flex-1 flex-col">
        <Text font="secondary-action" color="text-05">
          {origin.name}
        </Text>
        {detail && (
          <Text font="secondary-body" color="text-03">
            {detail}
          </Text>
        )}
      </span>
      {origin.status && (
        <span className="ton-pill" data-tone={pillTone(origin.status)}>
          {getBusinessLabel(origin.status)}
        </span>
      )}
    </li>
  );
}

export interface TonSourcesProps {
  sources: WorkSource[];
  origins: DataOrigin[];
}

/**
 * Where the answer comes from: each TON query that ran, linked to the page
 * that shows the same data, and the imported files behind them.
 */
export default function TonSources({ sources, origins }: TonSourcesProps) {
  if (!sources.length && !origins.length) return null;
  const groups = groupSources(sources);
  return (
    <section className="ton-sources" aria-label={S.title}>
      <span className="flex items-baseline gap-2">
        <Text font="secondary-action" color="text-04">
          {S.title}
        </Text>
        <Text font="secondary-body" color="text-03">
          {S.count(sources.length)}
        </Text>
      </span>
      {sources.length > 0 && (
        <ul className="ton-source-chips">
          {groups.map((group, index) => (
            <SourceChip key={group.id} group={group} index={index} />
          ))}
        </ul>
      )}
      {origins.length > 0 && (
        <div className="flex flex-col gap-1.5">
          <Text font="secondary-body" color="text-03">
            {S.origins}
          </Text>
          <ul className="flex flex-col gap-1.5">
            {origins.map((origin) => (
              <OriginRow key={origin.name} origin={origin} />
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
