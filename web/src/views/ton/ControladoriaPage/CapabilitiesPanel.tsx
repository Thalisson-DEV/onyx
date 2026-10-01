"use client";

import useSWR from "swr";
import { useTranslations } from "next-intl";
import { Text } from "@opal/components";
import { errorHandlingFetcher } from "@/lib/fetcher";

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

interface CapabilitiesPanelProps {
  unitId: string | undefined;
}

export default function CapabilitiesPanel({ unitId }: CapabilitiesPanelProps) {
  const t = useTranslations("controladoria");
  const registry = useSWR<Capability[]>(
    unitId
      ? `/api/ton/agent/capabilities${unitId === "consolidated" ? "" : `?unit_id=${encodeURIComponent(unitId)}`}`
      : null,
    errorHandlingFetcher
  );
  return (
    <section id="capabilities" className="flex flex-col gap-3 py-6">
      <Text as="h2" font="heading-h3" color="text-05">
        {t("capabilities")}
      </Text>
      <Text as="p" font="main-ui-muted" color="text-03">
        {t("capabilityNote")}
      </Text>
      {registry.isLoading && (
        <Text as="p" font="main-ui-body" color="text-03">
          {t("loading")}
        </Text>
      )}
      {registry.error && (
        <Text as="p" font="main-ui-body" color="text-05">
          {t("error")}
        </Text>
      )}
      {!registry.error &&
        registry.data &&
        Array.from(new Set(registry.data.map((item) => item.family))).map(
          (family) => (
            <details key={family} className="rounded-12 border border-01 p-4">
              <summary className="cursor-pointer">
                <Text as="span" font="main-ui-body" color="text-05">
                  {family}
                </Text>
              </summary>
              <div className="flex flex-col gap-4 pt-4">
                {registry.data
                  ?.filter((item) => item.family === family)
                  .map((item) => (
                    <div
                      key={item.key}
                      className="flex flex-col gap-1 border-b border-01 pb-3"
                    >
                      <Text as="h3" font="main-ui-body" color="text-05">
                        {t("routine", {
                          key: item.key.startsWith("SOURCE_")
                            ? item.family
                            : item.key,
                          name: item.name,
                          status: item.status_label,
                        })}
                      </Text>
                      <Text as="p" font="main-ui-muted" color="text-03">
                        {item.reason}
                      </Text>
                      <Text as="p" font="main-ui-muted" color="text-03">
                        {t("capabilityNeeds", {
                          sources: item.required_sources.join(", "),
                          configuration: item.required_configuration.join("; "),
                          owner: item.owner_specialist,
                        })}
                      </Text>
                      <Text as="p" font="main-ui-muted" color="text-03">
                        {item.next_dependency}
                      </Text>
                    </div>
                  ))}
              </div>
            </details>
          )
        )}
    </section>
  );
}
