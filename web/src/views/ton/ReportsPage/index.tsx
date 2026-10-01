"use client";

import { useState } from "react";
import useSWR from "swr";
import { useFormatter, useTranslations } from "next-intl";
import { Text, Button } from "@opal/components";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { hasPermission } from "@/lib/permissions";
import { Permission } from "@/lib/types";
import { useUser } from "@/providers/UserProvider";
import { TonStatusTag } from "@/views/ton/components/TonStatusTag";
import { getBusinessLabel } from "@/lib/ton/labels";
import type {
  Publication,
  ReportGroup,
} from "@/views/ton/ControladoriaPage/types";

interface ReportHistoryProps {
  revisionId: string;
  total: number;
}

function ReportHistory({ revisionId, total }: ReportHistoryProps) {
  const t = useTranslations("controladoria");
  const labels = useTranslations("tonRuntime");
  const format = useFormatter();
  const [offset, setOffset] = useState(0);
  const history = useSWR<Publication[]>(
    `/api/ton/agent/reports/${revisionId}/history?offset=${offset}`,
    errorHandlingFetcher
  );
  return (
    <div className="flex flex-col gap-2 pt-3">
      {history.isLoading && <Text font="main-ui-body">{t("loading")}</Text>}
      {history.error && <Text font="main-ui-body">{t("error")}</Text>}
      {history.data?.map((publication) => (
        <div
          key={publication.revision_id}
          className="flex flex-wrap justify-between gap-2 border-t border-01 pt-2"
        >
          <Text font="secondary-body">
            {t("published", {
              date: format.dateTime(new Date(publication.output.generated_at), {
                dateStyle: "short",
                timeStyle: "short",
              }),
              status: publication.status,
            })}
          </Text>
          <Button
            href={publication.report_url}
            prominence="secondary"
            size="sm"
          >
            {t("openResult")}
          </Button>
        </div>
      ))}
      {total > 25 && (
        <div className="flex gap-2">
          <Button
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - 25))}
            prominence="secondary"
          >
            {labels("previous")}
          </Button>
          <Button
            disabled={offset + 25 >= total}
            onClick={() => setOffset(offset + 25)}
            prominence="secondary"
          >
            {labels("next")}
          </Button>
        </div>
      )}
    </div>
  );
}

interface ReportGroupCardProps {
  group: ReportGroup;
}

function ReportGroupCard({ group }: ReportGroupCardProps) {
  const t = useTranslations("controladoria");
  const labels = useTranslations("tonRuntime");
  const format = useFormatter();
  const [open, setOpen] = useState(false);
  const publication = group.latest;
  return (
    <div
      role="article"
      className="flex flex-col gap-3 border border-01 rounded-12 p-4"
    >
      <Text as="h2" font="heading-h3">
        {t("period", {
          period: format.dateTime(
            new Date(`${publication.output.period}T12:00:00Z`),
            { month: "long", year: "numeric" }
          ),
          scope: publication.output.scope,
        })}
      </Text>
      <TonStatusTag status={publication.status} />
      {publication.report_type && (
        <Text font="main-ui-action">
          {getBusinessLabel(publication.report_type)}
        </Text>
      )}
      <Text as="p" font="main-ui-body">
        {publication.output.executive_brief.RESULTADO}
      </Text>
      <Text as="p" font="secondary-body" color="text-03">
        {publication.output.data_context}
      </Text>
      <div className="flex gap-2">
        <Button href={publication.report_url} size="sm">
          {t("openResult")}
        </Button>
        <Button
          href={publication.download_url}
          prominence="secondary"
          size="sm"
        >
          {t("download")}
        </Button>
      </div>
      {group.previous_count > 0 && (
        <details onToggle={(event) => setOpen(event.currentTarget.open)}>
          <summary>
            <Text font="main-ui-action">
              {labels("olderReports", { count: group.previous_count })}
            </Text>
          </summary>
          {open && (
            <ReportHistory
              revisionId={publication.revision_id}
              total={group.previous_count}
            />
          )}
        </details>
      )}
    </div>
  );
}

export default function ReportsPage() {
  const t = useTranslations("controladoria");
  const { user } = useUser();
  const canRead = hasPermission(
    user?.effective_permissions ?? [],
    Permission.READ_TON_REPORTS
  );
  const groups = useSWR<ReportGroup[]>(
    canRead ? "/api/ton/agent/reports/groups" : null,
    errorHandlingFetcher
  );
  return (
    <div className="flex flex-col gap-5 p-6 max-w-6xl mx-auto w-full">
      <Text as="h1" font="heading-h2">
        {t("reports")}
      </Text>
      {!canRead && <Text font="main-ui-body">{t("noAccess")}</Text>}
      {groups.isLoading && <Text font="main-ui-body">{t("loading")}</Text>}
      {groups.error && <Text font="main-ui-body">{t("error")}</Text>}
      {groups.data?.length === 0 && (
        <Text font="main-ui-body">{t("noReports")}</Text>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {groups.data?.map((group) => (
          <ReportGroupCard key={group.latest.revision_id} group={group} />
        ))}
      </div>
    </div>
  );
}
