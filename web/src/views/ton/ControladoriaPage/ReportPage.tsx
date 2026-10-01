"use client";

import { useFormatter, useTranslations } from "next-intl";
import useSWR from "swr";
import { Button, Text } from "@opal/components";
import {
  SvgFileText,
  SvgDownload,
  SvgArrowLeft,
  SvgCheckCircle,
  SvgAlertTriangle,
  SvgClock,
  SvgSimpleLoader,
} from "@opal/icons";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { ClosingContent } from "@/views/ton/ControladoriaPage";
import { getBusinessLabel } from "@/lib/ton/labels";
import { TonStatusTag } from "@/views/ton/components/TonStatusTag";
import type { Publication } from "@/views/ton/ControladoriaPage/types";

interface ReportPageProps {
  revisionId: string;
}

export default function ReportPage({ revisionId }: ReportPageProps) {
  const t = useTranslations("controladoria");
  const format = useFormatter();
  const report = useSWR<Publication>(
    `/api/ton/agent/reports/${encodeURIComponent(revisionId)}`,
    errorHandlingFetcher
  );

  return (
    <div className="flex flex-col gap-6 p-6 max-w-5xl mx-auto w-full">
      {/* Top Navigation & Actions Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-01">
        <div className="flex items-center gap-3">
          <Button
            href="/ton/relatorios"
            prominence="tertiary"
            size="sm"
            icon={SvgArrowLeft}
          >
            Voltar aos Relatórios
          </Button>
          <span className="text-text-02">/</span>
          <span className="text-xs text-text-03 font-mono truncate max-w-[200px]">
            {revisionId}
          </span>
        </div>

        {report.data && (
          <div className="flex items-center gap-2">
            <Button href="/ton/controladoria" prominence="tertiary" size="sm">
              Controladoria
            </Button>
            {report.data.download_url && (
              <Button
                href={report.data.download_url}
                size="sm"
                icon={SvgDownload}
              >
                {t("download")}
              </Button>
            )}
          </div>
        )}
      </div>

      {report.isLoading && (
        <div role="status" className="flex items-center gap-3 py-12 justify-center">
          <SvgSimpleLoader className="animate-spin w-5 h-5 text-action-selection-01" />
          <Text font="main-ui-body" color="text-03">
            {t("loading")}
          </Text>
        </div>
      )}

      {report.error && (
        <div role="alert" className="p-4 rounded-12 bg-status-error-01 border border-status-error-02">
          <Text font="main-ui-body" color="status-error-05">
            {t("error")}
          </Text>
        </div>
      )}

      {report.data && !report.error && (
        <div className="flex flex-col gap-6">
          {/* Executive Header Banner */}
          <div className="rounded-16 border border-01 background-neutral-00 p-6 flex flex-col gap-4 shadow-sm">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-10 bg-background-neutral-01 border border-01 flex items-center justify-center text-action-selection-01 shrink-0">
                  <SvgFileText className="w-5 h-5" />
                </div>
                <div className="flex flex-col">
                  <Text as="h1" font="heading-h2" color="text-05">
                    Relatório do Fechamento
                  </Text>
                  <span className="text-xs text-text-03">
                    Rotina {report.data.routine_code} · {report.data.output.scope} · Competência {report.data.output.period}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <TonStatusTag status={report.data.status} />
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-01 text-xs">
              <div>
                <span className="text-text-03 block">Período</span>
                <span className="font-semibold text-text-05">
                  {report.data.output.period}
                </span>
              </div>
              <div>
                <span className="text-text-03 block">Escopo</span>
                <span className="font-semibold text-text-05">
                  {report.data.output.scope}
                </span>
              </div>
              <div>
                <span className="text-text-03 block">Status DRE</span>
                <span className="font-semibold text-text-05">
                  {getBusinessLabel(report.data.output.dre_status)}
                </span>
              </div>
              <div>
                <span className="text-text-03 block">Gerado em</span>
                <span className="font-semibold text-text-05">
                  {report.data.output.generated_at
                    ? format.dateTime(new Date(report.data.output.generated_at), {
                        dateStyle: "short",
                        timeStyle: "short",
                      })
                    : "—"}
                </span>
              </div>
            </div>
          </div>

          {/* Core Analysis Content (Executive Brief, Findings, Readiness, Specialists, Sources) */}
          <ClosingContent output={report.data.output} />

          {/* Routine Execution Steps */}
          {report.data.steps && report.data.steps.length > 0 && (
            <section className="rounded-16 border border-01 background-neutral-00 p-5 flex flex-col gap-4">
              <Text as="h2" font="heading-h3" color="text-05">
                {t("steps")}
              </Text>
              <div className="flex flex-col gap-2">
                {report.data.steps.map((step, index) => (
                  <div
                    key={index}
                    className="p-3 rounded-8 bg-background-neutral-01 border border-01 flex items-start justify-between gap-3 text-xs"
                  >
                    <div className="flex flex-col gap-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-text-05">
                          {step.specialist}
                        </span>
                        <span className="text-text-03">({step.code})</span>
                      </div>
                      {step.reason && (
                        <span className="text-text-04">{step.reason}</span>
                      )}
                    </div>
                    <TonStatusTag status={step.status} />
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Traceability disclosure */}
          <details className="rounded-12 border border-01 background-neutral-01 p-4 text-xs group">
            <summary className="cursor-pointer text-text-03 hover:text-text-05 select-none font-medium flex items-center justify-between list-none">
              <span>Rastreabilidade e Identificadores Técnicos</span>
              <span className="text-[10px] transform group-open:rotate-180 transition-transform">
                ▼
              </span>
            </summary>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-3 text-xs text-text-04 font-mono">
              <div>
                <strong className="text-text-03 font-sans">Revision ID: </strong>
                <span>{report.data.revision_id}</span>
              </div>
              <div>
                <strong className="text-text-03 font-sans">Report ID: </strong>
                <span>{report.data.report_id}</span>
              </div>
              <div>
                <strong className="text-text-03 font-sans">Run ID: </strong>
                <span>{report.data.run_id}</span>
              </div>
              <div>
                <strong className="text-text-03 font-sans">Routine Code: </strong>
                <span>{report.data.routine_code}</span>
              </div>
            </div>
          </details>
        </div>
      )}
    </div>
  );
}
