"use client";

import { useTranslations } from "next-intl";
import useSWR from "swr";
import { Button, Text } from "@opal/components";
import { SvgFileText } from "@opal/icons";
import { SettingsLayouts } from "@opal/layouts";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { ClosingContent } from "@/views/ton/ControladoriaPage";
import type { Publication } from "@/views/ton/ControladoriaPage/types";

interface ReportPageProps {
  revisionId: string;
}

export default function ReportPage({ revisionId }: ReportPageProps) {
  const t = useTranslations("controladoria");
  const report = useSWR<Publication>(
    `/api/ton/agent/reports/${encodeURIComponent(revisionId)}`,
    errorHandlingFetcher
  );
  return (
    <SettingsLayouts.Root width="lg">
      <SettingsLayouts.Header
        icon={SvgFileText}
        title={t("reportTitle")}
        divider
      />
      <SettingsLayouts.Body>
        <div className="flex flex-wrap gap-2 pb-6">
          <Button href="/ton/controladoria" prominence="secondary">
            {t("title")}
          </Button>
          {report.data && (
            <Button href={report.data.download_url} prominence="secondary">
              {t("download")}
            </Button>
          )}
        </div>
        {report.isLoading && (
          <div role="status">
            <Text font="main-ui-body" color="text-03">
              {t("loading")}
            </Text>
          </div>
        )}
        {report.error && (
          <div role="alert">
            <Text font="main-ui-body" color="status-error-05">
              {t("error")}
            </Text>
          </div>
        )}
        {report.data && !report.error && (
          <div className="flex flex-col gap-6">
            <Text as="p" font="main-ui-body" color="text-05">
              {report.data.status}
            </Text>
            <ClosingContent output={report.data.output} />
            <section className="flex flex-col gap-2">
              <Text as="h2" font="heading-h3" color="text-05">
                {t("steps")}
              </Text>
              {report.data.steps.map((step, index) => (
                <div key={index} className="border-b border-01 pb-2">
                  <Text as="p" font="main-ui-body" color="text-05">
                    {t("step", {
                      specialist: step.specialist,
                      name: step.code,
                      status: step.status,
                    })}
                  </Text>
                  {step.reason && (
                    <Text as="p" font="main-ui-muted" color="text-03">
                      {step.reason}
                    </Text>
                  )}
                </div>
              ))}
            </section>
          </div>
        )}
      </SettingsLayouts.Body>
    </SettingsLayouts.Root>
  );
}
