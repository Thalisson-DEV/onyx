"use client";

import useSWR from "swr";
import { Text } from "@opal/components";
import { SvgChevronDown, SvgLock } from "@opal/icons";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { getBusinessLabel } from "@/lib/ton/labels";
import { COPY, formatNumber } from "@/lib/ton/copy";
import { useUser } from "@/providers/UserProvider";
import {
  BackLink,
  EmptyState,
  ErrorState,
  LoadingBlock,
  PageContainer,
  PageHeader,
  StatusPill,
  TonCard,
  type TonTone,
} from "@/views/ton/components/ui";

interface Capability {
  key: string;
  name: string;
  family: string;
  status_label: string;
  reason: string;
  required_sources: string[];
  required_configuration: string[];
  owner_specialist: string;
  next_dependency: string;
}

const STATUSES: { label: string; tone: TonTone }[] = [
  { label: "Operacional", tone: "success" },
  { label: "Parcial", tone: "warning" },
  { label: "Bloqueada", tone: "danger" },
  { label: "Não implementada", tone: "neutral" },
];

function toneOf(status: string): TonTone {
  return STATUSES.find((item) => item.label === status)?.tone ?? "neutral";
}

export default function CoveragePage() {
  const { hasAdminAccess } = useUser();
  const registry = useSWR<Capability[]>(
    hasAdminAccess ? "/api/ton/agent/capabilities" : null,
    errorHandlingFetcher
  );
  const capabilities = registry.data ?? [];
  const families = Array.from(new Set(capabilities.map((item) => item.family)));

  if (!hasAdminAccess) {
    return (
      <PageContainer>
        <EmptyState
          icon={SvgLock}
          title={COPY.admin.noAccessTitle}
          description={COPY.admin.noAccessDescription}
        />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <BackLink href="/ton/administracao" label={COPY.admin.back} />
      <PageHeader
        eyebrow={COPY.coverage.eyebrow}
        title={COPY.coverage.title}
        description={COPY.coverage.description}
      />
      {registry.isLoading && (
        <TonCard className="p-5">
          <LoadingBlock label={COPY.common.loading} />
        </TonCard>
      )}
      {registry.error && <ErrorState onRetry={() => registry.mutate()} />}
      {registry.data && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            {STATUSES.map((status) => (
              <TonCard
                key={status.label}
                as="div"
                className="flex flex-col gap-2 p-4"
              >
                <StatusPill tone={status.tone}>{status.label}</StatusPill>
                <span className="ton-metric">
                  <Text font="heading-h2" color="inherit">
                    {formatNumber(
                      capabilities.filter(
                        (item) => item.status_label === status.label
                      ).length
                    )}
                  </Text>
                </span>
              </TonCard>
            ))}
          </div>
          <div className="flex flex-col gap-3">
            {families.map((family) => {
              const items = capabilities.filter(
                (item) => item.family === family
              );
              return (
                <details key={family} className="ton-card group">
                  <summary className="ton-focusable flex items-center justify-between gap-3 p-4 cursor-pointer list-none rounded-12">
                    <span className="flex flex-col">
                      <Text font="main-ui-action" color="text-05">
                        {family}
                      </Text>
                      <Text font="secondary-body" color="text-03">
                        {COPY.coverage.count(items.length)}
                      </Text>
                    </span>
                    <SvgChevronDown
                      size={16}
                      className="shrink-0 transition-transform group-open:rotate-180"
                    />
                  </summary>
                  <ul className="flex flex-col divide-y divide-border-01 px-4 pb-2">
                    {items.map((item) => (
                      <li key={item.key} className="flex flex-col gap-1.5 py-3">
                        <span className="flex flex-wrap items-center gap-2">
                          <Text as="h2" font="main-ui-action" color="text-05">
                            {item.name}
                          </Text>
                          <StatusPill tone={toneOf(item.status_label)}>
                            {getBusinessLabel(item.status_label)}
                          </StatusPill>
                        </span>
                        <Text as="p" font="secondary-body" color="text-04">
                          {item.reason}
                        </Text>
                        <Text as="p" font="secondary-body" color="text-03">
                          {COPY.coverage.needs(
                            item.required_sources.join(", ") || "—",
                            item.owner_specialist
                          )}
                        </Text>
                        {item.next_dependency && (
                          <Text as="p" font="secondary-body" color="text-03">
                            {`${COPY.coverage.next}: ${item.next_dependency}`}
                          </Text>
                        )}
                      </li>
                    ))}
                  </ul>
                </details>
              );
            })}
          </div>
        </>
      )}
    </PageContainer>
  );
}
