"use client";

import Link from "next/link";
import type { Route } from "next";
import useSWR from "swr";
import { Text } from "@opal/components";
import {
  SvgArrowUpRight,
  SvgBarChart,
  SvgBookOpen,
  SvgCalendar,
  SvgChevronRight,
  SvgClipboard,
  SvgFileText,
  SvgServer,
  SvgShield,
  SvgSparkle,
  SvgUsers,
  SvgLock,
} from "@opal/icons";
import type { IconFunctionComponent } from "@opal/types";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { getFirstPermittedAdminRoute } from "@/lib/permissions";
import { useUser } from "@/providers/UserProvider";
import {
  useTonDataSources,
  useTonPersona,
  useTonReportGroups,
  useTonSpecialists,
} from "@/lib/ton/api";
import { COPY, formatRelativeDateTime } from "@/lib/ton/copy";
import {
  EmptyState,
  IconTile,
  PageContainer,
  PageHeader,
  StatusDot,
  specialistTone,
  type TonTone,
} from "@/views/ton/components/ui";

interface R3Schedule {
  enabled: boolean;
  schedule: string;
  next_run_at: string | null;
}

interface AdminEntryProps {
  icon: IconFunctionComponent;
  title: string;
  description: string;
  href: Route;
  status?: { tone: TonTone; label: string } | null;
  technical?: boolean;
}

function AdminEntry({
  icon,
  title,
  description,
  href,
  status,
  technical,
}: AdminEntryProps) {
  return (
    <Link
      href={href}
      className="ton-card ton-card-interactive ton-focusable flex items-start gap-4 p-5"
    >
      <IconTile icon={icon} />
      <div className="flex flex-col gap-1 min-w-0 flex-1">
        <span className="flex items-center gap-2">
          <Text font="main-ui-action" color="text-05">
            {title}
          </Text>
          {technical && (
            <span className="ton-pill" title={COPY.admin.technicalHint}>
              {COPY.admin.technicalBadge}
            </span>
          )}
        </span>
        <Text as="p" font="secondary-body" color="text-03">
          {description}
        </Text>
        {status && (
          <span className="flex items-center gap-1.5 pt-1">
            <StatusDot tone={status.tone} />
            <Text font="secondary-body" color="text-04">
              {status.label}
            </Text>
          </span>
        )}
      </div>
      {technical ? (
        <SvgArrowUpRight size={16} className="shrink-0 text-text-03" />
      ) : (
        <SvgChevronRight size={16} className="shrink-0 text-text-03" />
      )}
    </Link>
  );
}

export default function TonAdminPage() {
  const { hasAdminAccess, adminCapabilities } = useUser();
  const sources = useTonDataSources();
  const specialists = useTonSpecialists();
  const reports = useTonReportGroups();
  const persona = useTonPersona();
  const schedule = useSWR<R3Schedule>(
    hasAdminAccess ? "/api/ton/agent/routines/R3/schedule" : null,
    errorHandlingFetcher
  );

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

  const technicalRoute = (getFirstPermittedAdminRoute(adminCapabilities) ||
    "/admin/language-models") as Route;
  const configured = sources.data?.filter((source) => source.source_id) ?? [];
  const current = configured.filter((source) => source.status === "CURRENT");
  const operational = (specialists.data ?? []).filter(
    (item) => specialistTone(item.status) !== "neutral"
  );
  const versions = (reports.data ?? []).reduce(
    (sum, group) => sum + group.previous_count + 1,
    0
  );

  return (
    <PageContainer>
      <PageHeader
        eyebrow={COPY.admin.eyebrow}
        title={COPY.admin.title}
        description={COPY.admin.description}
      />

      <section
        aria-labelledby="ton-admin-product"
        className="flex flex-col gap-3"
      >
        <h2 id="ton-admin-product" className="ton-eyebrow">
          {COPY.admin.productSection}
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <AdminEntry
            icon={SvgUsers}
            title={COPY.admin.access.title}
            description={COPY.admin.access.description}
            href={"/admin/users" as Route}
            technical
          />
          <AdminEntry
            icon={SvgServer}
            title={COPY.admin.sources.title}
            description={COPY.admin.sources.description}
            href="/ton/fontes"
            status={
              sources.data
                ? {
                    tone:
                      current.length === configured.length &&
                      configured.length > 0
                        ? "success"
                        : "warning",
                    label: COPY.admin.sources.status(
                      current.length,
                      configured.length
                    ),
                  }
                : null
            }
          />
          <AdminEntry
            icon={SvgCalendar}
            title={COPY.admin.automations.title}
            description={COPY.admin.automations.description}
            href="/ton/automacoes"
            status={
              schedule.data
                ? schedule.data.enabled && schedule.data.next_run_at
                  ? {
                      tone: "success",
                      label: COPY.admin.automations.enabled(
                        formatRelativeDateTime(schedule.data.next_run_at)
                      ),
                    }
                  : { tone: "neutral", label: COPY.admin.automations.disabled }
                : null
            }
          />
          <AdminEntry
            icon={SvgSparkle}
            title={COPY.admin.specialists.title}
            description={COPY.admin.specialists.description}
            href="/ton/especialistas"
            status={
              specialists.data
                ? {
                    tone: operational.length ? "success" : "neutral",
                    label: COPY.admin.specialists.status(
                      operational.length,
                      specialists.data.length
                    ),
                  }
                : null
            }
          />
          <AdminEntry
            icon={SvgShield}
            title={COPY.admin.readiness.title}
            description={COPY.admin.readiness.description}
            href={"/admin/financial-readiness" as Route}
            technical
          />
          <AdminEntry
            icon={SvgClipboard}
            title={COPY.admin.dre.title}
            description={COPY.admin.dre.description}
            href={"/admin/dre" as Route}
            technical
          />
          <AdminEntry
            icon={SvgFileText}
            title={COPY.admin.reports.title}
            description={COPY.admin.reports.description}
            href="/ton/relatorios"
            status={
              reports.data
                ? {
                    tone: "brand",
                    label: COPY.admin.reports.status(
                      reports.data.length,
                      versions
                    ),
                  }
                : null
            }
          />
          <AdminEntry
            icon={SvgBookOpen}
            title={COPY.admin.coverage.title}
            description={COPY.admin.coverage.description}
            href="/ton/cobertura"
          />
          <AdminEntry
            icon={SvgBarChart}
            title={COPY.admin.assistant.title}
            description={COPY.admin.assistant.description}
            href="/ton/chat"
            status={
              persona.data
                ? persona.data.persona_id != null
                  ? { tone: "success", label: COPY.admin.assistant.ready }
                  : { tone: "warning", label: COPY.admin.assistant.missing }
                : null
            }
          />
        </div>
      </section>

      <section
        aria-labelledby="ton-admin-technical"
        className="ton-card flex flex-col sm:flex-row sm:items-center gap-4 p-5"
      >
        <IconTile icon={SvgServer} tone="neutral" size="lg" />
        <div className="flex flex-col gap-1 min-w-0 flex-1">
          <Text
            as="h2"
            id="ton-admin-technical"
            font="heading-h3"
            color="text-05"
          >
            {COPY.admin.technical.title}
          </Text>
          <Text as="p" font="secondary-body" color="text-03">
            {COPY.admin.technical.description}
          </Text>
        </div>
        <Link
          href={technicalRoute}
          className="ton-focusable ton-brand-text flex items-center gap-1 shrink-0 rounded-08 px-1"
        >
          <Text font="secondary-action" color="inherit">
            {COPY.admin.technical.open}
          </Text>
          <SvgArrowUpRight size={14} />
        </Link>
      </section>
    </PageContainer>
  );
}
