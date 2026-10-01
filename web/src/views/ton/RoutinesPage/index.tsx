"use client";

import useSWR from "swr";
import { useFormatter, useTranslations } from "next-intl";
import { Text } from "@opal/components";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { hasPermission } from "@/lib/permissions";
import { Permission } from "@/lib/types";
import { useUser } from "@/providers/UserProvider";
import { TonStatusTag } from "@/views/ton/components/TonStatusTag";
import { R3Execution } from "@/views/ton/components/R3Execution";
import type { Routine } from "@/views/ton/ControladoriaPage/types";

export default function RoutinesPage() {
  const t = useTranslations("controladoria");
  const format = useFormatter();
  const { user } = useUser();
  const canRead = hasPermission(
    user?.effective_permissions ?? [],
    Permission.READ_TON_SOURCES
  );
  const routines = useSWR<Routine[]>(
    canRead ? "/api/ton/agent/routines" : null,
    errorHandlingFetcher
  );
  return (
    <div className="flex flex-col gap-5 p-6 max-w-6xl mx-auto w-full">
      <Text as="h1" font="heading-h2">
        {t("routines")}
      </Text>
      {!canRead && (
        <Text as="p" font="main-ui-body">
          {t("noAccess")}
        </Text>
      )}
      {routines.isLoading && (
        <Text as="p" font="main-ui-body">
          {t("loading")}
        </Text>
      )}
      {routines.error && (
        <Text as="p" font="main-ui-body">
          {t("error")}
        </Text>
      )}
      {routines.data?.map((routine) => (
        <div
          key={routine.key}
          role="article"
          className="flex flex-col gap-3 border border-01 rounded-12 p-4"
        >
          <Text as="h2" font="heading-h3">
            {t("routine", {
              key: routine.key,
              name: routine.name,
              status: routine.status,
            })}
          </Text>
          <TonStatusTag status={routine.status} />
          <Text as="p" font="main-ui-body">
            {routine.reason}
          </Text>
          <Text as="p" font="main-ui-body" color="text-03">
            {routine.schedule}
          </Text>
          {routine.next_run && (
            <Text as="p" font="secondary-body">
              {t("nextRoutineRun", {
                date: format.dateTime(new Date(routine.next_run), {
                  dateStyle: "short",
                  timeStyle: "short",
                  timeZone: "America/Sao_Paulo",
                }),
              })}
            </Text>
          )}
          {routine.last_run && (
            <Text as="p" font="secondary-body">
              {t("lastRoutineRun", {
                date: format.dateTime(new Date(routine.last_run), {
                  dateStyle: "short",
                  timeStyle: "short",
                  timeZone: "America/Sao_Paulo",
                }),
                result: routine.last_result ?? t("notAvailable"),
              })}
            </Text>
          )}
          {routine.manual_available && routine.key === "R3" && <R3Execution />}
        </div>
      ))}
    </div>
  );
}
