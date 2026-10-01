"use client";

import { useRef, useState } from "react";
import { useFormatter, useTranslations } from "next-intl";
import useSWR from "swr";
import { Button, InputSingleSelect, Text } from "@opal/components";
import { SvgBarChart, SvgSimpleLoader } from "@opal/icons";
import { SettingsLayouts } from "@opal/layouts";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { hasPermission } from "@/lib/permissions";
import { Permission } from "@/lib/types";
import { useUser } from "@/providers/UserProvider";
import CapabilitiesPanel from "@/views/ton/ControladoriaPage/CapabilitiesPanel";
import type {
  ClosingOutput,
  Publication,
  Routine,
} from "@/views/ton/ControladoriaPage/types";

interface ClosingContentProps {
  output: ClosingOutput;
}

const EXECUTIVE_ORDER = [
  "RESULTADO",
  "PROBLEMA",
  "IMPACTO",
  "CAUSA / HIPÓTESE",
  "AÇÃO",
];

export function ClosingContent({ output }: ClosingContentProps) {
  const t = useTranslations("controladoria");
  const format = useFormatter();
  return (
    <div className="flex flex-col gap-6">
      <div
        role="note"
        className="rounded-12 border border-01 background-neutral-02 p-4"
      >
        <Text as="p" font="main-ui-body" color="text-05">
          {output.data_context}
        </Text>
        <Text as="p" font="main-ui-muted" color="text-03">
          {t("period", {
            period: format.dateTime(new Date(`${output.period}T12:00:00Z`), {
              month: "long",
              year: "numeric",
            }),
            scope: output.scope,
          })}
        </Text>
        <Text as="p" font="main-ui-muted" color="text-03">
          {t("periodNote")}
        </Text>
      </div>
      <section className="flex flex-col gap-2">
        <Text as="h2" font="heading-h3" color="text-05">
          {t("summary")}
        </Text>
        {Object.entries(output.executive_brief)
          .sort(
            ([first], [second]) =>
              EXECUTIVE_ORDER.indexOf(first) - EXECUTIVE_ORDER.indexOf(second)
          )
          .map(([label, value]) => (
            <div key={label} className="flex flex-col gap-1">
              <Text as="h3" font="main-ui-action" color="text-05">
                {label}
              </Text>
              <Text as="p" font="main-ui-body" color="text-03">
                {value}
              </Text>
            </div>
          ))}
      </section>
      <section id="readiness" className="flex flex-col gap-2">
        <Text as="h2" font="heading-h3" color="text-05">
          {t("readiness")}
        </Text>
        <Text as="p" font="main-ui-body" color="text-05">
          {output.dre_status}
        </Text>
        {Object.entries(output.blockers).map(([label, count]) => (
          <Text key={label} as="p" font="main-ui-body" color="text-03">
            {t("blocker", { label, count })}
          </Text>
        ))}
      </section>
      <section id="findings" className="flex flex-col gap-3">
        <Text as="h2" font="heading-h3" color="text-05">
          {t("findings")}
        </Text>
        <Text as="p" font="main-ui-muted" color="text-03">
          {output.findings_scope}
        </Text>
        {output.findings.length === 0 && (
          <Text as="p" font="main-ui-body" color="text-03">
            {t("noFindings")}
          </Text>
        )}
        {output.findings.map((finding) => (
          <div
            key={finding.id}
            className="rounded-12 border border-01 p-4 flex flex-col gap-2"
          >
            <Text as="h3" font="main-ui-action" color="text-05">
              {finding.title}
            </Text>
            <Text as="p" font="main-ui-muted" color="text-03">
              {finding.status}
            </Text>
            {finding.recommendations.map((action, index) => (
              <Text key={index} as="p" font="main-ui-body" color="text-03">
                {action}
              </Text>
            ))}
            {finding.evidence.map((evidence) => (
              <Text
                key={evidence.id}
                as="p"
                font="secondary-body"
                color="text-03"
                wordWrap="wrap-anywhere"
              >
                {t("evidence", {
                  source: evidence.source_snapshot_id ?? t("notAvailable"),
                  sheet: evidence.sheet_name ?? t("notAvailable"),
                  row: evidence.row_number ?? t("notAvailable"),
                  confidence: evidence.confidence_level,
                })}
              </Text>
            ))}
          </div>
        ))}
        {output.findings_may_have_more && (
          <Text as="p" font="main-ui-muted" color="text-03">
            {t("moreFindings")}
          </Text>
        )}
      </section>
      <section id="specialists" className="flex flex-col gap-3">
        <Text as="h2" font="heading-h3" color="text-05">
          {t("specialists")}
        </Text>
        <div className="grid gap-3 md:grid-cols-3">
          {output.specialists.map((specialist) => (
            <div
              key={specialist.key}
              className="rounded-12 border border-01 p-4 flex flex-col gap-2 min-w-0"
            >
              <Text as="h3" font="main-ui-action" color="text-05">
                {t("specialist", {
                  name: specialist.name,
                  status: specialist.status,
                })}
              </Text>
              <Text as="p" font="main-ui-body" color="text-03">
                {specialist.reason}
              </Text>
              {specialist.actions.map((action, index) => (
                <Text key={index} as="p" font="main-ui-body" color="text-03">
                  {action}
                </Text>
              ))}
              {specialist.limitations.map((limitation, index) => (
                <Text key={index} as="p" font="secondary-body" color="text-03">
                  {limitation}
                </Text>
              ))}
            </div>
          ))}
        </div>
      </section>
      <section id="sources" className="flex flex-col gap-3">
        <Text as="h2" font="heading-h3" color="text-05">
          {t("sources")}
        </Text>
        {output.sources.map((source) => (
          <div
            key={source.key}
            className="border-b border-01 pb-3 flex flex-col gap-1"
          >
            <Text as="h3" font="main-ui-action" color="text-05">
              {source.name}
            </Text>
            <Text as="p" font="main-ui-body" color="text-03">
              {source.status}
            </Text>
            <Text as="p" font="main-ui-muted" color="text-03">
              {t("lastImport", {
                date: source.last_success_at
                  ? format.dateTime(new Date(source.last_success_at), {
                      dateStyle: "medium",
                      timeStyle: "short",
                    })
                  : t("notAvailable"),
              })}
            </Text>
            <Text as="p" font="main-ui-muted" color="text-03">
              {t("integration", {
                acquisition: source.acquisition,
                status: source.direct_integration,
              })}
            </Text>
          </div>
        ))}
      </section>
    </div>
  );
}

export default function ControladoriaPage() {
  const t = useTranslations("controladoria");
  const format = useFormatter();
  const { user } = useUser();
  const permissions = user?.effective_permissions ?? [];
  const canRead =
    hasPermission(permissions, Permission.READ_TON_SOURCES) &&
    hasPermission(permissions, Permission.READ_TON_OCCURRENCES);
  const canReadReports = hasPermission(
    permissions,
    Permission.READ_TON_REPORTS
  );
  const canRun =
    canRead &&
    canReadReports &&
    hasPermission(permissions, Permission.MANAGE_TON_REPORTS);
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
  const configuration = useSWR<{ persona_id: number | null }>(
    canRead ? "/api/ton/agent/configuration" : null,
    errorHandlingFetcher
  );
  const routines = useSWR<Routine[]>(
    canRead ? "/api/ton/agent/routines" : null,
    errorHandlingFetcher
  );
  const publications = useSWR<Publication[]>(
    canReadReports ? "/api/ton/agent/reports" : null,
    errorHandlingFetcher
  );
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState(false);
  const [result, setResult] = useState<Publication | null>(null);
  const requestId = useRef<string | null>(null);
  const inFlight = useRef(false);

  async function runR3() {
    if (!canRun || inFlight.current || !snapshot.data) return;
    inFlight.current = true;
    setRunning(true);
    setRunError(false);
    requestId.current ??= crypto.randomUUID();
    try {
      const response = await fetch("/api/ton/agent/routines/R3/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          request_id: requestId.current,
          normalization_run_id: snapshot.data.normalization_run_id,
          structure_version_id: snapshot.data.structure_version_id,
          period: snapshot.data.period,
          unit_id: snapshot.data.unit_id,
        }),
      });
      if (!response.ok) throw new Error("R3 request failed");
      const publication: Publication = await response.json();
      setResult(publication);
      requestId.current = null;
      await publications.mutate();
    } catch {
      setRunError(true);
    } finally {
      inFlight.current = false;
      setRunning(false);
    }
  }

  return (
    <SettingsLayouts.Root width="lg">
      <SettingsLayouts.Header
        icon={SvgBarChart}
        title={t("title")}
        description={t("description")}
        divider
      />
      <SettingsLayouts.Body>
        <div className="flex flex-wrap gap-2 pb-5">
          {configuration.data?.persona_id && (
            <Button href={`/app?agentId=${configuration.data.persona_id}`}>
              {t("chat")}
            </Button>
          )}
          <Button href="/ton/data-sources" prominence="secondary">
            {t("sources")}
          </Button>
          <Button href="/admin/financial-readiness" prominence="secondary">
            {t("readiness")}
          </Button>
          <Button href="/admin/dre" prominence="secondary">
            {t("dre")}
          </Button>
          <Button href="#specialists" prominence="secondary">
            {t("specialists")}
          </Button>
          <Button href="#routines" prominence="secondary">
            {t("routines")}
          </Button>
          <Button href="#reports" prominence="secondary">
            {t("reports")}
          </Button>
          <Button href="#capabilities" prominence="secondary">
            {t("capabilities")}
          </Button>
        </div>
        {!canRead && (
          <Text as="p" font="main-ui-body" color="text-03">
            {t("noAccess")}
          </Text>
        )}
        {canRead && (
          <div className="pb-5 max-w-sm">
            <InputSingleSelect
              value={unitId}
              onValueChange={(value) => {
                setUnit(value);
                requestId.current = null;
                setResult(null);
              }}
              disabled={running}
            >
              <InputSingleSelect.Trigger
                placeholder={t("scope")}
                aria-label={t("scope")}
              />
              <InputSingleSelect.Content>
                {isAdmin && (
                  <InputSingleSelect.Item value="consolidated">
                    {t("consolidated")}
                  </InputSingleSelect.Item>
                )}
                {units.data?.map((item) => (
                  <InputSingleSelect.Item key={item.id} value={item.id}>
                    {item.name || item.code}
                  </InputSingleSelect.Item>
                ))}
              </InputSingleSelect.Content>
            </InputSingleSelect>
          </div>
        )}
        {snapshot.isLoading && (
          <div role="status" className="flex gap-2 pb-5">
            <SvgSimpleLoader />
            <Text font="main-ui-body" color="text-03">
              {t("loading")}
            </Text>
          </div>
        )}
        {(snapshot.error || units.error) && (
          <div role="alert" className="flex flex-col gap-2 pb-5">
            <Text font="main-ui-body" color="status-error-05">
              {t("error")}
            </Text>
            <Button
              onClick={() => {
                void snapshot.mutate();
                void units.mutate();
              }}
              prominence="secondary"
            >
              {t("retry")}
            </Button>
          </div>
        )}
        {canRead && !isAdmin && units.data?.length === 0 && (
          <Text as="p" font="main-ui-body" color="text-03">
            {t("noUnits")}
          </Text>
        )}
        {canRead && snapshot.data && !snapshot.error && (
          <ClosingContent output={snapshot.data} />
        )}
        <section id="routines" className="flex flex-col gap-3 py-6">
          <Text as="h2" font="heading-h3" color="text-05">
            {t("routines")}
          </Text>
          {routines.error && (
            <Text font="main-ui-body" color="status-error-05">
              {t("error")}
            </Text>
          )}
          {routines.data?.map((routine) => (
            <div
              key={routine.key}
              className="border-b border-01 pb-3 flex flex-col gap-1"
            >
              <Text as="h3" font="main-ui-action" color="text-05">
                {t("routine", {
                  key: routine.key,
                  name: routine.name,
                  status: routine.status,
                })}
              </Text>
              <Text as="p" font="main-ui-muted" color="text-03">
                {routine.reason}
              </Text>
              <Text as="p" font="main-ui-muted" color="text-03">
                {routine.schedule}
              </Text>
              {routine.manual_available && (
                <div className="flex flex-wrap gap-2 pt-2">
                  <Button
                    disabled={!canRun || running || !snapshot.data}
                    onClick={() => void runR3()}
                  >
                    {running ? t("running") : t("runNow")}
                  </Button>
                </div>
              )}
            </div>
          ))}
          {runError && (
            <Text as="p" font="main-ui-body" color="status-error-05">
              {t("runError")}
            </Text>
          )}
          {result && (
            <div role="status" className="flex flex-col gap-2">
              <Text font="main-ui-body" color="text-05">
                {result.status}
              </Text>
              <Button href={result.report_url} prominence="secondary">
                {t("openResult")}
              </Button>
            </div>
          )}
        </section>
        {canRead && <CapabilitiesPanel unitId={unitId} />}
        <section id="reports" className="flex flex-col gap-3 pb-6">
          <Text as="h2" font="heading-h3" color="text-05">
            {t("reports")}
          </Text>
          {publications.error && (
            <Text font="main-ui-body" color="status-error-05">
              {t("error")}
            </Text>
          )}
          {publications.data?.length === 0 && (
            <Text font="main-ui-muted" color="text-03">
              {t("noReports")}
            </Text>
          )}
          {publications.data?.map((publication) => (
            <div
              key={publication.revision_id}
              className="flex flex-wrap items-center justify-between gap-2 border-b border-01 pb-3"
            >
              <Text font="main-ui-body" color="text-03">
                {t("published", {
                  date: format.dateTime(
                    new Date(publication.output.generated_at),
                    { dateStyle: "medium", timeStyle: "short" }
                  ),
                  status: publication.status,
                })}
              </Text>
              <Button href={publication.report_url} prominence="secondary">
                {t("openResult")}
              </Button>
            </div>
          ))}
        </section>
      </SettingsLayouts.Body>
    </SettingsLayouts.Root>
  );
}
