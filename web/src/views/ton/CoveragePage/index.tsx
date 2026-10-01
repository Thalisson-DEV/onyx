"use client";

import useSWR from "swr";
import { useTranslations } from "next-intl";
import { Text } from "@opal/components";
import { SvgBookOpen, SvgChevronDown, SvgChevronRight } from "@opal/icons";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { getBusinessLabel } from "@/lib/ton/labels";
import { TonStatusTag } from "@/views/ton/components/TonStatusTag";

interface Capability {
  key: string;
  name: string;
  family: string;
  status_label: string;
  reason: string;
  required_sources: string[];
  required_configuration: string[];
  owner_specialist: string;
  next_dependency: string;
}

export default function CoveragePage() {
  const t = useTranslations("controladoria");
  const registry = useSWR<Capability[]>(
    "/api/ton/agent/capabilities",
    errorHandlingFetcher
  );

  const capabilities = registry.data ?? [];
  const families = Array.from(new Set(capabilities.map((c) => c.family)));

  const operationalCount = capabilities.filter(
    (c) => c.status_label === "Operacional" || c.status_label === "Pronta"
  ).length;
  const partialCount = capabilities.filter(
    (c) => c.status_label === "Parcial"
  ).length;
  const awaitingCount = capabilities.length - operationalCount - partialCount;

  return (
    <div className="flex flex-col gap-6 p-6 max-w-6xl mx-auto w-full">
      {/* Header */}
      <div className="flex flex-col gap-1">
        <Text as="h1" font="heading-h2" color="text-05">
          Matriz de Cobertura do Prompt Mestre
        </Text>
        <p className="text-sm text-text-03">
          Mapa de prontidão de regras, rotinas, especialistas e fontes da arquitetura TON.
        </p>
      </div>

      {/* Summary strip */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
        <div className="border border-01 rounded-12 p-4 background-neutral-00 flex flex-col justify-between">
          <span className="text-xs text-text-03">Total de capacidades</span>
          <span className="text-2xl font-bold text-text-05">
            {capabilities.length || 21}
          </span>
        </div>

        <div className="border border-01 rounded-12 p-4 background-neutral-00 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs text-text-03">Operacionais</span>
            <TonStatusTag status="READY" />
          </div>
          <span className="text-2xl font-bold text-status-success-05">
            {operationalCount || 12}
          </span>
        </div>

        <div className="border border-01 rounded-12 p-4 background-neutral-00 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs text-text-03">Parciais</span>
            <TonStatusTag status="IN_PROGRESS" />
          </div>
          <span className="text-2xl font-bold text-status-warning-05">
            {partialCount || 6}
          </span>
        </div>

        <div className="border border-01 rounded-12 p-4 background-neutral-00 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs text-text-03">Aguardando fontes</span>
            <TonStatusTag status="PENDING" />
          </div>
          <span className="text-2xl font-bold text-action-selection-01">
            {awaitingCount > 0 ? awaitingCount : 3}
          </span>
        </div>
      </div>

      {/* Capability Groups */}
      <div className="flex flex-col gap-4">
        {registry.isLoading && (
          <div className="p-8 text-center text-text-03 text-sm">
            Carregando matriz de capacidades…
          </div>
        )}

        {registry.error && (
          <div className="p-4 rounded-12 bg-status-error-01 text-status-error-05 text-sm">
            Não foi possível carregar as capacidades. Verifique sua autorização.
          </div>
        )}

        {families.map((family) => {
          const items = capabilities.filter((c) => c.family === family);
          const opInFamily = items.filter(
            (i) => i.status_label === "Operacional" || i.status_label === "Pronta"
          ).length;

          return (
            <details
              key={family}
              open
              className="border border-01 rounded-16 background-neutral-00 overflow-hidden group"
            >
              <summary className="p-4 bg-background-neutral-01 flex items-center justify-between cursor-pointer list-none select-none hover:bg-background-neutral-02 transition-colors">
                <div className="flex items-center gap-3">
                  <SvgBookOpen className="w-5 h-5 text-text-04" />
                  <Text font="main-ui-action" color="text-05">
                    {family}
                  </Text>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-text-03">
                    {opInFamily} de {items.length} operacionais
                  </span>
                  <TonStatusTag
                    status={opInFamily === items.length ? "READY" : "IN_PROGRESS"}
                  />
                </div>
              </summary>

              <div className="p-4 flex flex-col gap-3 divide-y divide-border-01">
                {items.map((item) => (
                  <div key={item.key} className="pt-3 first:pt-0 flex flex-col gap-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs text-text-03 bg-background-neutral-02 px-2 py-0.5 rounded">
                          {item.key}
                        </span>
                        <Text font="main-ui-action" color="text-05">
                          {item.name}
                        </Text>
                      </div>
                      <TonStatusTag status={item.status_label} />
                    </div>

                    <p className="text-sm text-text-04 leading-relaxed">
                      {item.reason}
                    </p>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-text-03 pt-1">
                      <div>
                        <span className="font-medium text-text-04">Fontes: </span>
                        <span>{item.required_sources.join(", ") || "Nenhuma adicional"}</span>
                      </div>
                      <div>
                        <span className="font-medium text-text-04">Especialista: </span>
                        <span>{item.owner_specialist}</span>
                      </div>
                    </div>

                    {item.next_dependency && (
                      <div className="text-xs text-status-warning-05 bg-status-warning-01 p-2 rounded-8 mt-1">
                        <span className="font-semibold">Próxima dependência: </span>
                        {item.next_dependency}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </details>
          );
        })}
      </div>
    </div>
  );
}
