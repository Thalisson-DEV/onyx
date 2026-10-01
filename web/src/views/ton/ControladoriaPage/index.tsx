"use client";

import { useRef, useState } from "react";
import { useFormatter, useTranslations } from "next-intl";
import useSWR from "swr";
import { Button, InputSingleSelect, Text } from "@opal/components";
import { TonStatusTag } from "@/views/ton/components/TonStatusTag";
import {
  SvgBarChart,
  SvgSimpleLoader,
  SvgAlertTriangle,
  SvgCheckCircle,
  SvgClock,
  SvgUploadCloud,
  SvgFileText,
  SvgManageAgent,
  SvgSliders,
  SvgChevronRight,
  SvgExternalLink,
} from "@opal/icons";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { hasPermission } from "@/lib/permissions";
import { Permission } from "@/lib/types";
import { useUser } from "@/providers/UserProvider";
import { getBusinessLabel, getStatusTone } from "@/lib/ton/labels";
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
      {/* Context note */}
      <div
        role="note"
        className="rounded-12 border border-01 background-neutral-01 p-4 flex flex-col gap-1"
      >
        <div className="flex items-center gap-2">
          <SvgAlertTriangle className="w-4 h-4 text-status-warning-05 shrink-0" />
          <Text as="p" font="main-ui-body" color="text-05">
            {output.data_context}
          </Text>
        </div>
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

      {/* Executive Brief Grid */}
      <section className="flex flex-col gap-3">
        <Text as="h2" font="heading-h3" color="text-05">
          {t("summary")}
        </Text>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {Object.entries(output.executive_brief)
            .sort(
              ([first], [second]) =>
                EXECUTIVE_ORDER.indexOf(first) - EXECUTIVE_ORDER.indexOf(second)
            )
            .map(([label, value]) => (
              <div
                key={label}
                className="border border-01 rounded-12 p-4 background-neutral-00 flex flex-col gap-1.5"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs uppercase tracking-wider font-semibold text-text-03">
                    {label}
                  </span>
                </div>
                <p className="text-sm text-text-04 leading-relaxed">{value}</p>
              </div>
            ))}
        </div>
      </section>

      {/* Readiness & Blockers */}
      <section id="readiness" className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <Text as="h2" font="heading-h3" color="text-05">
            {t("readiness")}
          </Text>
          <TonStatusTag status={output.dre_status} />
        </div>

        <div className="flex flex-col gap-3">
          {Object.entries(output.blockers).map(([label, count]) => (
            <div
              key={label}
              className="border border-01 rounded-12 p-4 background-neutral-00 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:border-02 transition-colors"
            >
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <TonStatusTag status="PENDING" />
                  <Text font="main-ui-action" color="text-05">
                    {t("blocker", { label: getBusinessLabel(label), count })}
                  </Text>
                </div>
                <p className="text-xs text-text-03">
                  Exige intervenção humana para classificação ou pareamento
                  contábil antes do fechamento.
                </p>
              </div>

              <Button href="/ton/pendencias" size="sm" prominence="secondary">
                Resolver
              </Button>
            </div>
          ))}
        </div>
      </section>

      {/* Findings */}
      <section id="findings" className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <Text as="h2" font="heading-h3" color="text-05">
            {t("findings")}
          </Text>
          <span className="text-xs text-text-03">{output.findings_scope}</span>
        </div>

        {output.findings.length === 0 && (
          <div className="p-4 rounded-12 border border-01 background-neutral-00 text-sm text-text-03">
            {t("noFindings")}
          </div>
        )}

        <div className="flex flex-col gap-3">
          {output.findings.map((finding) => (
            <div
              key={finding.id}
              className="rounded-12 border border-01 background-neutral-00 p-4 flex flex-col gap-3"
            >
              <div className="flex items-start justify-between gap-3">
                <Text as="h3" font="main-ui-action" color="text-05">
                  {finding.title}
                </Text>
                <TonStatusTag status={finding.status} />
              </div>

              {finding.recommendations.length > 0 && (
                <div className="flex flex-col gap-1 text-sm text-text-04">
                  <span className="font-semibold text-xs text-text-03">
                    Recomendações:
                  </span>
                  {finding.recommendations.map((action, index) => (
                    <p
                      key={index}
                      className="text-sm text-text-04 leading-relaxed"
                    >
                      • {action}
                    </p>
                  ))}
                </div>
              )}

              {finding.evidence.length > 0 && (
                <div className="pt-2 border-t border-01 flex flex-col gap-1 text-xs text-text-03">
                  {finding.evidence.map((evidence) => (
                    <div
                      key={evidence.id}
                      className="flex flex-wrap gap-x-3 gap-y-1"
                    >
                      <span>
                        <strong>Fonte:</strong>{" "}
                        {evidence.source_snapshot_id ?? t("notAvailable")}
                      </span>
                      <span>
                        <strong>Planilha:</strong>{" "}
                        {evidence.sheet_name ?? t("notAvailable")}
                      </span>
                      <span>
                        <strong>Linha:</strong>{" "}
                        {evidence.row_number ?? t("notAvailable")}
                      </span>
                      <span>
                        <strong>Confiança:</strong> {evidence.confidence_level}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Specialists */}
      <section id="specialists" className="flex flex-col gap-3">
        <Text as="h2" font="heading-h3" color="text-05">
          {t("specialists")}
        </Text>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {output.specialists.map((specialist) => (
            <div
              key={specialist.key}
              className="rounded-12 border border-01 background-neutral-00 p-4 flex flex-col justify-between gap-3 min-w-0"
            >
              <div className="flex flex-col gap-1">
                <div className="flex items-center justify-between gap-2">
                  <div className="truncate">
                    <Text as="h3" font="main-ui-action" color="text-05">
                      {specialist.name}
                    </Text>
                  </div>
                  <TonStatusTag status={specialist.status} />
                </div>
                <p className="text-xs text-text-03 line-clamp-2">
                  {specialist.reason}
                </p>
              </div>

              {specialist.actions.length > 0 && (
                <div className="text-xs text-text-04 pt-2 border-t border-01">
                  <span className="font-semibold text-text-03">
                    Ações recomendadas:
                  </span>
                  {specialist.actions.slice(0, 2).map((act, i) => (
                    <p key={i} className="truncate">
                      • {act}
                    </p>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Sources */}
      <section id="sources" className="flex flex-col gap-3">
        <Text as="h2" font="heading-h3" color="text-05">
          {t("sources")}
        </Text>
        <div className="grid gap-3 sm:grid-cols-2">
          {output.sources.map((source) => (
            <div
              key={source.key}
              className="border border-01 rounded-12 p-4 background-neutral-00 flex flex-col gap-2"
            >
              <div className="flex items-center justify-between">
                <Text as="h3" font="main-ui-action" color="text-05">
                  {source.name}
                </Text>
                <TonStatusTag status={source.status} />
              </div>
              <div className="flex flex-col gap-1 text-xs text-text-03">
                <p>
                  {t("lastImport", {
                    date: source.last_success_at
                      ? format.dateTime(new Date(source.last_success_at), {
                          dateStyle: "medium",
                          timeStyle: "short",
                        })
                      : t("notAvailable"),
                  })}
                </p>
                <p>
                  {t("integration", {
                    acquisition: source.acquisition,
                    status: source.direct_integration,
                  })}
                </p>
              </div>
            </div>
          ))}
        </div>
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
      const pub: Publication = await response.json();
      setResult(pub);
      requestId.current = null;
      await publications.mutate();
      await routines.mutate();
    } catch {
      setRunError(true);
    } finally {
      inFlight.current = false;
      setRunning(false);
    }
  }

  if (!canRead) {
    return (
      <div role="alert" className="p-6 max-w-6xl mx-auto">
        <Text as="p" font="main-ui-body" color="text-03">
          {t("noAccess")}
        </Text>
      </div>
    );
  }

  const blockerCount = Object.values(snapshot.data?.blockers ?? {}).reduce(
    (a, b) => a + b,
    0
  );

  return (
    <div className="flex flex-col gap-6 p-6 max-w-6xl mx-auto w-full">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-01">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2.5">
            <SvgBarChart className="w-7 h-7 text-action-selection-01" />
            <Text as="h1" font="heading-h2" color="text-05">
              {t("title")}
            </Text>
          </div>
          <Text as="p" font="main-ui-body" color="text-03">
            {t("description")}
          </Text>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          {/* Scope Selector */}
          {units.data && units.data.length > 0 && (
            <div className="min-w-[180px]">
              <InputSingleSelect
                value={unitId ?? ""}
                onValueChange={(val) => setUnit(val)}
              >
                <InputSingleSelect.Trigger
                  placeholder={t("consolidated")}
                  aria-label={t("consolidated")}
                />
                <InputSingleSelect.Content>
                  {isAdmin && (
                    <InputSingleSelect.Item value="consolidated">
                      {t("consolidated")}
                    </InputSingleSelect.Item>
                  )}
                  {units.data.map((u) => (
                    <InputSingleSelect.Item key={u.id} value={u.id}>
                      {u.name ? `${u.code} · ${u.name}` : u.code}
                    </InputSingleSelect.Item>
                  ))}
                </InputSingleSelect.Content>
              </InputSingleSelect>
            </div>
          )}

          {/* Primary CTA */}
          {configuration.data?.persona_id && (
            <Button href="/ton/chat">{t("chat")}</Button>
          )}

          {/* Secondary CTA */}
          {canRun && (
            <Button
              prominence="secondary"
              disabled={running || !snapshot.data}
              onClick={runR3}
              icon={running ? SvgSimpleLoader : undefined}
            >
              {running ? t("running") : t("runNow")}
            </Button>
          )}
        </div>
      </div>

      {/* Execution Error Notice */}
      {runError && (
        <div
          role="alert"
          className="p-4 rounded-12 bg-status-error-01 border border-status-error-02 text-status-error-05 text-sm flex items-center justify-between"
        >
          <span>{t("runError")}</span>
          <Button prominence="tertiary" size="sm" onClick={runR3}>
            {t("retry")}
          </Button>
        </div>
      )}

      {/* Persisted Result Banner */}
      {result && (
        <div className="p-4 rounded-12 bg-status-success-01 border border-status-success-02 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <SvgCheckCircle className="w-5 h-5 text-status-success-05 shrink-0" />
            <span className="text-sm font-medium text-status-success-05">
              Fechamento concluído com sucesso.
            </span>
          </div>
          <Button href={result.report_url} size="sm">
            {t("openResult")}
          </Button>
        </div>
      )}

      {/* Executive Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <div className="border border-01 rounded-12 p-3.5 background-neutral-00 flex flex-col justify-between">
          <span className="text-xs text-text-03">Fechamento</span>
          <div className="mt-1">
            <TonStatusTag status={snapshot.data?.dre_status ?? "PENDING"} />
          </div>
        </div>

        <div className="border border-01 rounded-12 p-3.5 background-neutral-00 flex flex-col justify-between">
          <span className="text-xs text-text-03">DRE</span>
          <div className="flex items-center justify-between mt-1">
            <span className="text-sm font-semibold text-text-05">
              {snapshot.data?.dre_status === "READY"
                ? "Pronta"
                : "Com bloqueios"}
            </span>
            <Button href="/ton/dre" prominence="tertiary" size="sm">
              Ver
            </Button>
          </div>
        </div>

        <div className="border border-01 rounded-12 p-3.5 background-neutral-00 flex flex-col justify-between">
          <span className="text-xs text-text-03">Pendências</span>
          <div className="flex items-center justify-between mt-1">
            <span className="text-sm font-semibold text-status-warning-05">
              {blockerCount} bloqueios
            </span>
            <Button href="/ton/pendencias" prominence="tertiary" size="sm">
              Resolver
            </Button>
          </div>
        </div>

        <div className="border border-01 rounded-12 p-3.5 background-neutral-00 flex flex-col justify-between">
          <span className="text-xs text-text-03">Fontes</span>
          <div className="flex items-center justify-between mt-1">
            <span className="text-sm font-semibold text-text-05">
              {snapshot.data?.sources?.length ?? 2} ativas
            </span>
            <Button href="/ton/data-sources" prominence="tertiary" size="sm">
              Fontes
            </Button>
          </div>
        </div>

        <div className="border border-01 rounded-12 p-3.5 background-neutral-00 flex flex-col justify-between col-span-2 sm:col-span-1">
          <span className="text-xs text-text-03">Última análise</span>
          <div className="mt-1 text-xs text-text-04 font-medium">
            {snapshot.data?.generated_at
              ? format.dateTime(new Date(snapshot.data.generated_at), {
                  dateStyle: "short",
                  timeStyle: "short",
                })
              : "Hoje"}
          </div>
        </div>
      </div>

      {/* Main Content & Activity */}
      {snapshot.data && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Analysis & Findings (2 cols) */}
          <div className="lg:col-span-2 flex flex-col gap-6">
            <ClosingContent output={snapshot.data} />
          </div>

          {/* Activity & Quick Shortcuts (1 col) */}
          <div className="flex flex-col gap-5">
            {/* Quick Actions */}
            <div className="border border-01 rounded-16 p-4 background-neutral-00 flex flex-col gap-3">
              <Text font="main-ui-action" color="text-05">
                Acesso Rápido
              </Text>
              <div className="flex flex-col gap-1">
                <Button
                  href="/ton/dre"
                  prominence="tertiary"
                  icon={SvgBarChart}
                >
                  Demonstrativo DRE
                </Button>
                <Button
                  href="/ton/pendencias"
                  prominence="tertiary"
                  icon={SvgAlertTriangle}
                >
                  Pendências do Fechamento
                </Button>
                <Button
                  href="/ton/data-sources"
                  prominence="tertiary"
                  icon={SvgUploadCloud}
                >
                  Atualizar Fontes (Upload)
                </Button>
                <Button
                  href="/ton/relatorios"
                  prominence="tertiary"
                  icon={SvgFileText}
                >
                  Relatórios Publicados
                </Button>
                <Button
                  href="/ton/especialistas"
                  prominence="tertiary"
                  icon={SvgManageAgent}
                >
                  Especialistas (9 agentes)
                </Button>
                <Button
                  href="/ton/rotinas"
                  prominence="tertiary"
                  icon={SvgSliders}
                >
                  Rotinas Automáticas (R1–R9)
                </Button>
              </div>
            </div>

            {/* Published Reports summary */}
            <div className="border border-01 rounded-16 p-4 background-neutral-00 flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <Text font="main-ui-action" color="text-05">
                  Últimos Relatórios
                </Text>
                <Button href="/ton/relatorios" prominence="tertiary" size="sm">
                  Todos
                </Button>
              </div>

              <div className="flex flex-col gap-2">
                {publications.data?.slice(0, 3).map((pub) => (
                  <a
                    key={pub.revision_id}
                    href={`/ton/controladoria/reports/${pub.revision_id}`}
                    className="p-2.5 rounded-8 hover:bg-background-neutral-01 border border-01 flex items-center justify-between gap-2 transition-colors"
                  >
                    <div className="flex flex-col min-w-0">
                      <span className="text-xs font-semibold text-text-05 truncate">
                        Fechamento {pub.output?.period ?? ""}
                      </span>
                      <span className="text-xs text-text-03">
                        {pub.routine_code} · {pub.output?.scope ?? ""}
                      </span>
                    </div>
                    <SvgChevronRight className="w-3.5 h-3.5 text-text-03 shrink-0" />
                  </a>
                ))}

                {(!publications.data || publications.data.length === 0) && (
                  <span className="text-xs text-text-03 py-2">
                    {t("noReports")}
                  </span>
                )}
              </div>
            </div>

            {/* Routines summary */}
            <div className="border border-01 rounded-16 p-4 background-neutral-00 flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <Text font="main-ui-action" color="text-05">
                  Rotinas Operacionais
                </Text>
                <Button href="/ton/rotinas" prominence="tertiary" size="sm">
                  Rotinas
                </Button>
              </div>

              <div className="flex flex-col gap-2 text-xs">
                {routines.data?.slice(0, 3).map((rt) => (
                  <div
                    key={rt.key}
                    className="flex items-center justify-between py-1 border-b border-01 last:border-0"
                  >
                    <span className="font-semibold text-text-04">
                      {rt.key} — {rt.name}
                    </span>
                    <TonStatusTag status={rt.status} />
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
