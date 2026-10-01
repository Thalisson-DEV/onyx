"use client";

import { useFormatter, useTranslations } from "next-intl";
import useSWR from "swr";
import { Button, Text } from "@opal/components";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { ClosingContent } from "@/views/ton/ControladoriaPage";
import { TonStatusTag } from "@/views/ton/components/TonStatusTag";
import type { Publication } from "@/views/ton/ControladoriaPage/types";

interface ReportPageProps {
  revisionId: string;
}

export default function ReportPage({ revisionId }: ReportPageProps) {
  const t = useTranslations("controladoria");
  const nav = useTranslations("tonNavigation");
  const format = useFormatter();
  const report = useSWR<Publication>(
    `/api/ton/agent/reports/${encodeURIComponent(revisionId)}`,
    errorHandlingFetcher
  );
  return (
    <div className="flex flex-col gap-5 p-6 max-w-5xl mx-auto w-full">
      <div className="flex flex-wrap gap-2">
        <Button href="/ton/relatorios" prominence="secondary">
          {nav("reports")}
        </Button>
        <Button href="/ton/controladoria" prominence="tertiary">
          {nav("central")}
        </Button>
        {report.data?.download_url && (
          <Button href={report.data.download_url}>{t("download")}</Button>
        )}
      </div>
      <Text as="h1" font="heading-h2">
        {t("reports")}
      </Text>
      {report.isLoading && (
        <Text as="p" font="main-ui-body">
          {t("loading")}
        </Text>
      )}
      {report.error && (
        <Text as="p" font="main-ui-body" color="status-error-05">
          {t("error")}
        </Text>
      )}
      {report.data && !report.error && (
        <>
          <div className="flex flex-wrap gap-3 items-center">
            <TonStatusTag status={report.data.status} />
            <Text font="secondary-body">
              {format.dateTime(new Date(report.data.output.generated_at), {
                dateStyle: "medium",
                timeStyle: "short",
              })}
            </Text>
          </div>
          <ClosingContent output={report.data.output} />
          {report.data.steps.length > 0 && (
            <details className="border border-01 rounded-12 p-4">
              <summary>
                <Text font="main-ui-action">{t("steps")}</Text>
              </summary>
              <div className="flex flex-col gap-2 pt-3">
                {report.data.steps.map((step) => (
                  <div
                    key={`${step.specialist}:${step.code}`}
                    className="flex flex-wrap justify-between gap-3 border-b border-01 py-2"
                  >
                    <Text font="main-ui-body">
                      {t("step", {
                        specialist: step.specialist,
                        name: step.code,
                        status: step.status,
                      })}
                    </Text>
                    <TonStatusTag status={step.status} />
                    <Text as="p" font="secondary-body">
                      {step.reason}
                    </Text>
                  </div>
                ))}
              </div>
            </details>
          )}
        </>
      )}
    </div>
  );
}
