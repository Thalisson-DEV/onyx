"use client";

import useSWR from "swr";
import { useFormatter, useTranslations } from "next-intl";
import { Button, Text } from "@opal/components";
import { SvgSimpleLoader } from "@opal/icons";
import { useUser } from "@/providers/UserProvider";
import { hasPermission } from "@/lib/permissions";
import { Permission } from "@/lib/types";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { useR3Execution } from "@/lib/ton/hooks";
import { TonStatusTag } from "@/views/ton/components/TonStatusTag";
import type { ClosingOutput } from "@/views/ton/ControladoriaPage/types";

interface R3ExecutionProps {
  unitId?: string | null;
}

export function R3Execution({ unitId }: R3ExecutionProps) {
  const t = useTranslations("controladoria");
  const labels = useTranslations("tonRuntime");
  const format = useFormatter();
  const { user } = useUser();
  const permissions = user?.effective_permissions ?? [];
  const canRead =
    hasPermission(permissions, Permission.READ_TON_SOURCES) &&
    hasPermission(permissions, Permission.READ_TON_OCCURRENCES);
  const canReadResults = hasPermission(
    permissions,
    Permission.READ_TON_REPORTS
  );
  const canRun =
    canRead &&
    canReadResults &&
    hasPermission(permissions, Permission.MANAGE_TON_REPORTS);
  const query = unitId ? `?unit_id=${encodeURIComponent(unitId)}` : "";
  const snapshot = useSWR<ClosingOutput>(
    canRead ? `/api/ton/agent/closing${query}` : null,
    errorHandlingFetcher
  );
  const execution = useR3Execution(
    snapshot.data,
    canRun,
    user?.id,
    canReadResults
  );
  return (
    <div
      className="flex flex-col gap-3 border border-01 rounded-12 p-4"
      aria-live="polite"
      aria-busy={execution.running}
    >
      {canRun && (
        <Button
          onClick={execution.run}
          disabled={execution.running || !snapshot.data}
          icon={execution.running ? SvgSimpleLoader : undefined}
        >
          {execution.running
            ? labels("starting")
            : execution.failed
              ? t("retry")
              : t("runNow")}
        </Button>
      )}
      {snapshot.error && (
        <Text as="p" font="main-ui-body">
          {t("error")}
        </Text>
      )}
      {execution.running && (
        <>
          <Text as="p" font="main-ui-action">
            {labels("started")}
          </Text>
          <Text as="p" font="main-ui-body">
            {labels("running")}
          </Text>
        </>
      )}
      {execution.startedAt && (
        <Text as="p" font="secondary-body">
          {labels("startedAt", {
            date: format.dateTime(new Date(execution.startedAt), {
              dateStyle: "short",
              timeStyle: "short",
            }),
          })}
        </Text>
      )}
      {execution.failed && (
        <Text as="p" font="main-ui-body" color="text-03">
          {t("runError")}
        </Text>
      )}
      {!execution.running && !execution.failed && execution.latest && (
        <>
          <Text as="p" font="main-ui-action">
            {labels("completed")}
          </Text>
          <TonStatusTag status={execution.latest.status} />
          <Text as="p" font="main-ui-body">
            {execution.latest.output.executive_brief.RESULTADO}
          </Text>
          <Text as="p" font="secondary-body">
            {labels("persisted")}
          </Text>
        </>
      )}
      {execution.latest && (
        <>
          <Button
            href={`/ton/controladoria/reports/${execution.latest.revision_id}`}
            prominence="secondary"
          >
            {t("openResult")}
          </Button>
          <Button
            href={`/ton/controladoria/reports/${execution.latest.revision_id}`}
            prominence="tertiary"
          >
            {labels("openReport")}
          </Button>
          <details>
            <summary>
              <Text font="main-ui-action">{t("steps")}</Text>
            </summary>
            <div className="flex flex-col gap-2 pt-2">
              {execution.latest.steps.map((step, index) => (
                <div key={`${step.specialist}-${step.code}-${index}`}>
                  <Text as="p" font="main-ui-body">
                    {t("step", {
                      specialist: step.specialist,
                      name: step.code,
                      status: step.status,
                    })}
                  </Text>
                  {step.reason && (
                    <Text as="p" font="secondary-body" color="text-03">
                      {step.reason}
                    </Text>
                  )}
                </div>
              ))}
            </div>
          </details>
        </>
      )}
    </div>
  );
}
