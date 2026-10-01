"use client";

import useSWR from "swr";
import { useTranslations } from "next-intl";
import { Text } from "@opal/components";
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
  const families = Array.from(new Set(capabilities.map((item) => item.family)));
  return (
    <div className="flex flex-col gap-5 p-6 max-w-6xl mx-auto w-full">
      <Text as="h1" font="heading-h2">
        {t("capabilities")}
      </Text>
      <Text as="p" font="main-ui-body" color="text-03">
        {t("capabilityNote")}
      </Text>
      {registry.isLoading && (
        <Text as="p" font="main-ui-body">
          {t("loading")}
        </Text>
      )}
      {registry.error && (
        <Text as="p" font="main-ui-body">
          {t("error")}
        </Text>
      )}
      <div className="flex flex-wrap gap-3">
        {["Operacional", "Parcial", "Bloqueada", "Não implementada"].map(
          (status) => (
            <div
              key={status}
              role="group"
              aria-label={status}
              className="border border-01 rounded-12 p-3 flex flex-col gap-2"
            >
              <TonStatusTag status={status} />
              <Text font="heading-h3">
                {registry.data
                  ? String(
                      capabilities.filter(
                        (item) => item.status_label === status
                      ).length
                    )
                  : "—"}
              </Text>
            </div>
          )
        )}
      </div>
      {families.map((family) => (
        <details key={family} className="border border-01 rounded-12 p-4">
          <summary>
            <Text font="main-ui-action">{family}</Text>
          </summary>
          <div className="flex flex-col gap-3 pt-3">
            {capabilities
              .filter((item) => item.family === family)
              .map((item) => (
                <div
                  key={item.key}
                  className="border-t border-01 pt-3 flex flex-col gap-2"
                >
                  <Text as="h2" font="main-ui-action">
                    {item.name}
                  </Text>
                  <TonStatusTag status={getBusinessLabel(item.status_label)} />
                  <Text as="p" font="main-ui-body">
                    {item.reason}
                  </Text>
                  <Text as="p" font="secondary-body" color="text-03">
                    {t("capabilityNeeds", {
                      sources: item.required_sources.join(", "),
                      configuration: item.required_configuration.join(", "),
                      owner: item.owner_specialist,
                    })}
                  </Text>
                  <Text as="p" font="secondary-body">
                    {item.next_dependency}
                  </Text>
                </div>
              ))}
          </div>
        </details>
      ))}
    </div>
  );
}
