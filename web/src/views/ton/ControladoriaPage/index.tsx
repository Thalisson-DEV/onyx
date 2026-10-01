"use client";

import { useState } from "react";
import { useFormatter, useTranslations } from "next-intl";
import useSWR from "swr";
import { Button, InputSingleSelect, Text } from "@opal/components";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { hasPermission } from "@/lib/permissions";
import { Permission } from "@/lib/types";
import { useUser } from "@/providers/UserProvider";
import { getBusinessLabel } from "@/lib/ton/labels";
import { TonStatusTag } from "@/views/ton/components/TonStatusTag";
import { R3Execution } from "@/views/ton/components/R3Execution";
import type {
  ClosingOutput,
  ReportGroup,
  Routine,
} from "@/views/ton/ControladoriaPage/types";

interface ClosingContentProps {
  output: ClosingOutput;
  compact?: boolean;
}

export function ClosingContent({
  output,
  compact = false,
}: ClosingContentProps) {
  const t = useTranslations("controladoria");
  const dre = useTranslations("dre");
  const format = useFormatter();
  const blockers = Object.entries(output.blockers).sort(
    ([, a], [, b]) => b - a
  );
  return (
    <div className="flex flex-col gap-4">
      <div
        role="note"
        className="border border-01 rounded-12 p-4 background-neutral-01 flex flex-col gap-2"
      >
        <Text as="p" font="main-ui-body">
          {output.data_context}
        </Text>
        <Text as="p" font="secondary-body">
          {t("period", {
            period: format.dateTime(new Date(`${output.period}T12:00:00Z`), {
              month: "long",
              year: "numeric",
            }),
            scope: output.scope,
          })}
        </Text>
        <Text as="p" font="secondary-body" color="text-03">
          {t("periodNote")}
        </Text>
      </div>
      <section className="flex flex-col gap-2">
        <Text as="h2" font="heading-h3">
          {t("summary")}
        </Text>
        {Object.entries(output.executive_brief).map(([label, value]) => (
          <div
            key={label}
            className="border border-01 rounded-12 p-3 flex flex-col gap-1"
          >
            <Text font="main-ui-action">{getBusinessLabel(label)}</Text>
            <Text as="p" font="main-ui-body">
              {value}
            </Text>
          </div>
        ))}
      </section>
      <section className="flex flex-col gap-2">
        <Text as="h2" font="heading-h3">
          {t("readiness")}
        </Text>
        {(compact ? blockers.slice(0, 3) : blockers).map(([label, count]) => (
          <div
            key={label}
            className="flex flex-wrap items-center justify-between gap-3 border border-01 rounded-12 p-3"
          >
            <Text font="main-ui-body">
              {t("blocker", { label: getBusinessLabel(label), count })}
            </Text>
            <Button
              href={`/ton/pendencias?normalization=${output.normalization_run_id ?? ""}&unit=${output.unit_id ?? ""}&period=${output.period}`}
              size="sm"
              prominence="secondary"
            >
              {dre("resolve")}
            </Button>
          </div>
        ))}
      </section>
      <section className="flex flex-col gap-2">
        <Text as="h2" font="heading-h3">
          {t("findings")}
        </Text>
        {output.findings.length === 0 && (
          <Text as="p" font="main-ui-body" color="text-03">
            {t("noFindings")}
          </Text>
        )}
        {(compact ? output.findings.slice(0, 3) : output.findings).map(
          (finding) => (
            <div
              key={finding.id}
              className="border border-01 rounded-12 p-3 flex flex-col gap-2"
            >
              <Text as="h3" font="main-ui-action">
                {finding.title}
              </Text>
              <TonStatusTag status={finding.status} />
              {finding.recommendations.map((action) => (
                <Text key={action} as="p" font="main-ui-body">
                  {action}
                </Text>
              ))}
              {finding.evidence.map((evidence) => (
                <Text
                  key={evidence.id}
                  as="p"
                  font="secondary-body"
                  color="text-03"
                >
                  {t("evidence", {
                    source: t("notAvailable"),
                    sheet: evidence.sheet_name ?? t("notAvailable"),
                    row: evidence.row_number ?? t("notAvailable"),
                    confidence: getBusinessLabel(evidence.confidence_level),
                  })}
                </Text>
              ))}
            </div>
          )
        )}
        {output.findings_may_have_more && (
          <Text as="p" font="secondary-body">
            {t("moreFindings")}
          </Text>
        )}
      </section>
      {!compact && (
        <>
          <section className="flex flex-col gap-2">
            <Text as="h2" font="heading-h3">
              {t("specialists")}
            </Text>
            {output.specialists.map((specialist) => (
              <div
                key={specialist.key}
                className="border border-01 rounded-12 p-3 flex flex-col gap-2"
              >
                <Text font="main-ui-action">{specialist.name}</Text>
                <TonStatusTag status={specialist.status} />
                <Text as="p" font="main-ui-body">
                  {specialist.reason}
                </Text>
                {[...specialist.limitations, ...specialist.actions].map(
                  (detail) => (
                    <Text
                      key={detail}
                      as="p"
                      font="secondary-body"
                      color="text-03"
                    >
                      {detail}
                    </Text>
                  )
                )}
              </div>
            ))}
          </section>
          <section className="flex flex-col gap-2">
            <Text as="h2" font="heading-h3">
              {t("sources")}
            </Text>
            {output.sources.map((source) => (
              <div
                key={source.key}
                className="border border-01 rounded-12 p-3 flex flex-col gap-2"
              >
                <Text font="main-ui-action">{source.name}</Text>
                <TonStatusTag status={source.status} />
                <Text as="p" font="secondary-body">
                  {t("integration", {
                    acquisition: source.acquisition,
                    status: source.direct_integration,
                  })}
                </Text>
                <Text as="p" font="secondary-body">
                  {t("lastImport", {
                    date: source.last_success_at
                      ? format.dateTime(new Date(source.last_success_at), {
                          dateStyle: "short",
                          timeStyle: "short",
                        })
                      : t("notAvailable"),
                  })}
                </Text>
              </div>
            ))}
          </section>
        </>
      )}
    </div>
  );
}

export default function ControladoriaPage() {
  const t = useTranslations("controladoria");
  const nav = useTranslations("tonNavigation");
  const { user } = useUser();
  const permissions = user?.effective_permissions ?? [];
  const canRead =
    hasPermission(permissions, Permission.READ_TON_SOURCES) &&
    hasPermission(permissions, Permission.READ_TON_OCCURRENCES);
  const canReadReports = hasPermission(
    permissions,
    Permission.READ_TON_REPORTS
  );
  const isAdmin = hasPermission(
    permissions,
    Permission.FULL_ADMIN_PANEL_ACCESS
  );
  const [unit, setUnit] = useState("");
  const units = useSWR<{ id: string; code: string; name: string | null }[]>(
    canRead ? "/api/ton/financial-domain/units?limit=25" : null,
    errorHandlingFetcher
  );
  const unitId = unit || (isAdmin ? "consolidated" : units.data?.[0]?.id);
  const snapshot = useSWR<ClosingOutput>(
    canRead && unitId
      ? `/api/ton/agent/closing${unitId === "consolidated" ? "" : `?unit_id=${encodeURIComponent(unitId)}`}`
      : null,
    errorHandlingFetcher
  );
  const routines = useSWR<Routine[]>(
    canRead ? "/api/ton/agent/routines" : null,
    errorHandlingFetcher
  );
  const reports = useSWR<ReportGroup[]>(
    canReadReports ? "/api/ton/agent/reports/groups" : null,
    errorHandlingFetcher
  );
  if (!canRead)
    return (
      <Text as="p" font="main-ui-body">
        {t("noAccess")}
      </Text>
    );
  return (
    <div className="flex flex-col gap-5 p-6 max-w-6xl mx-auto w-full">
      <div className="flex flex-wrap justify-between items-center gap-3">
        <Text as="h1" font="heading-h2">
          {t("title")}
        </Text>
        <Button href="/ton/chat">{t("chat")}</Button>
      </div>
      <InputSingleSelect value={unitId ?? ""} onValueChange={setUnit}>
        <InputSingleSelect.Trigger
          aria-label={t("scope")}
          placeholder={t("scope")}
        />
        <InputSingleSelect.Content>
          {isAdmin && (
            <InputSingleSelect.Item value="consolidated">
              {t("consolidated")}
            </InputSingleSelect.Item>
          )}
          {units.data?.map((item) => (
            <InputSingleSelect.Item key={item.id} value={item.id}>
              {getBusinessLabel(item.name ?? item.code)}
            </InputSingleSelect.Item>
          ))}
        </InputSingleSelect.Content>
      </InputSingleSelect>
      {snapshot.isLoading && (
        <Text as="p" font="main-ui-body">
          {t("loading")}
        </Text>
      )}
      {snapshot.error && (
        <Text as="p" font="main-ui-body">
          {t("error")}
        </Text>
      )}
      <div className="flex flex-wrap gap-2">
        <Button href="/ton/dre" prominence="secondary">
          {nav("dre")}
        </Button>
        <Button href="/ton/pendencias" prominence="secondary">
          {nav("readiness")}
        </Button>
        <Button href="/ton/data-sources" prominence="secondary">
          {nav("sources")}
        </Button>
        <Button href="/ton/especialistas" prominence="secondary">
          {nav("specialists")}
        </Button>
      </div>
      {snapshot.data && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="border border-01 rounded-12 p-3 flex flex-col gap-2">
              <Text font="main-ui-action">{t("dre")}</Text>
              <TonStatusTag status={snapshot.data.dre_status} />
            </div>
            <div className="border border-01 rounded-12 p-3 flex flex-col gap-2">
              <Text font="main-ui-action">{nav("readiness")}</Text>
              <Text font="heading-h3">
                {String(
                  Object.values(snapshot.data.blockers).reduce(
                    (sum, count) => sum + count,
                    0
                  )
                )}
              </Text>
            </div>
            <div className="border border-01 rounded-12 p-3 flex flex-col gap-2">
              <Text font="main-ui-action">{nav("sources")}</Text>
              <Text font="heading-h3">
                {String(snapshot.data.sources.length)}
              </Text>
            </div>
          </div>
          <R3Execution unitId={snapshot.data.unit_id} />
          <ClosingContent output={snapshot.data} compact />
        </>
      )}
      <section className="flex flex-col gap-2">
        <Text as="h2" font="heading-h3">
          {t("reports")}
        </Text>
        {reports.data?.slice(0, 3).map(({ latest }) => (
          <Button
            key={latest.revision_id}
            href={latest.report_url}
            prominence="secondary"
          >
            {t("period", {
              period: latest.output.period,
              scope: latest.output.scope,
            })}
          </Button>
        ))}
        <Button href="/ton/relatorios" prominence="tertiary">
          {nav("reports")}
        </Button>
      </section>
      <section className="flex flex-col gap-2">
        <Text as="h2" font="heading-h3">
          {t("routines")}
        </Text>
        {routines.data?.slice(0, 3).map((routine) => (
          <Text key={routine.key} as="p" font="main-ui-body">
            {t("routine", {
              key: routine.key,
              name: routine.name,
              status: routine.status,
            })}
          </Text>
        ))}
        <Button href="/ton/rotinas" prominence="tertiary">
          {nav("routines")}
        </Button>
      </section>
    </div>
  );
}
