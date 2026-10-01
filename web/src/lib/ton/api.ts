"use client";

import useSWR from "swr";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { hasPermission } from "@/lib/permissions";
import { Permission } from "@/lib/types";
import { useUser } from "@/providers/UserProvider";
import type {
  ClientSource,
  ClosingOutput,
  ReportGroup,
  Routine,
  SpecialistView,
} from "@/lib/ton/types";

export const TON_API = {
  configuration: "/api/ton/agent/configuration",
  closing: "/api/ton/agent/closing",
  routines: "/api/ton/agent/routines",
  specialists: "/api/ton/agent/specialists",
  reportGroups: "/api/ton/agent/reports/groups",
  dataSources: "/api/ton/data-sources",
} as const;

export const TON_REPORTS_RECENT = "/api/ton/agent/reports?limit=25";

export interface TonAccess {
  canRead: boolean;
  canReadReports: boolean;
  canRunReports: boolean;
  canImport: boolean;
  isAdmin: boolean;
}

/** Client-side mirror of the backend gates. Hiding is presentation only. */
export function useTonAccess(): TonAccess {
  const { user } = useUser();
  const permissions = user?.effective_permissions ?? [];
  const canRead =
    hasPermission(permissions, Permission.READ_TON_SOURCES) &&
    hasPermission(permissions, Permission.READ_TON_OCCURRENCES);
  const canReadReports = hasPermission(
    permissions,
    Permission.READ_TON_REPORTS
  );
  return {
    canRead,
    canReadReports,
    canRunReports:
      canRead &&
      canReadReports &&
      hasPermission(permissions, Permission.MANAGE_TON_REPORTS),
    canImport: hasPermission(permissions, Permission.IMPORT_TON_SOURCES),
    isAdmin: hasPermission(permissions, Permission.FULL_ADMIN_PANEL_ACCESS),
  };
}

export function closingKey(unitId?: string | null): string {
  return unitId
    ? `${TON_API.closing}?unit_id=${encodeURIComponent(unitId)}`
    : TON_API.closing;
}

export function useTonClosing(unitId?: string | null) {
  const { canRead } = useTonAccess();
  return useSWR<ClosingOutput>(
    canRead ? closingKey(unitId) : null,
    errorHandlingFetcher,
    { revalidateOnFocus: false }
  );
}

export function useTonRoutines() {
  const { canRead } = useTonAccess();
  return useSWR<Routine[]>(
    canRead ? TON_API.routines : null,
    errorHandlingFetcher
  );
}

export function useTonSpecialists() {
  const { canRead } = useTonAccess();
  return useSWR<SpecialistView[]>(
    canRead ? TON_API.specialists : null,
    errorHandlingFetcher,
    { revalidateOnFocus: false }
  );
}

export function useTonReportGroups() {
  const { canReadReports } = useTonAccess();
  return useSWR<ReportGroup[]>(
    canReadReports ? TON_API.reportGroups : null,
    errorHandlingFetcher
  );
}

export function useTonDataSources() {
  const { canRead } = useTonAccess();
  return useSWR<ClientSource[]>(
    canRead ? TON_API.dataSources : null,
    errorHandlingFetcher
  );
}

export function useTonPersona() {
  const { canRead } = useTonAccess();
  return useSWR<{ persona_id: number | null }>(
    canRead ? TON_API.configuration : null,
    errorHandlingFetcher,
    { revalidateOnFocus: false }
  );
}

/** The backend declares the synthetic demonstration context in plain text. */
export function isSyntheticContext(closing: ClosingOutput | undefined) {
  return !!closing && /sint[eé]tic|synthetic/i.test(closing.data_context);
}
