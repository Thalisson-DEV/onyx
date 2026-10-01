"use client";

import { useState } from "react";
import useSWR from "swr";
import { useFormatter, useTranslations } from "next-intl";
import { Text, Button, Modal } from "@opal/components";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { TonStatusTag } from "@/views/ton/components/TonStatusTag";
import { useUser } from "@/providers/UserProvider";
import { hasPermission } from "@/lib/permissions";
import { Permission } from "@/lib/types";

export interface Specialist {
  key: string;
  name: string;
  objective: string;
  status: string;
  reason: string;
  required_sources: string[];
  available_capabilities: string[];
  blocked_capabilities: string[];
  last_execution: string | null;
  interaction: "coordinator";
}

export default function SpecialistsPage() {
  const t = useTranslations("controladoria");
  const labels = useTranslations("tonRuntime");
  const format = useFormatter();
  const { user } = useUser();
  const canRead = hasPermission(
    user?.effective_permissions ?? [],
    Permission.READ_TON_SOURCES
  );
  const registry = useSWR<Specialist[]>(
    canRead ? "/api/ton/agent/specialists" : null,
    errorHandlingFetcher
  );
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const selected = registry.data?.find((item) => item.key === selectedKey);
  return (
    <div className="flex flex-col gap-5 p-6 max-w-6xl mx-auto w-full">
      <Text as="h1" font="heading-h2">
        {t("specialists")}
      </Text>
      <Text as="p" font="main-ui-body" color="text-03">
        {labels("coordinator")}
      </Text>
      {!canRead && (
        <Text as="p" font="main-ui-body">
          {t("noAccess")}
        </Text>
      )}
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
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {registry.data?.map((item) => (
          <div
            key={item.key}
            role="article"
            className="border border-01 rounded-12 p-4 flex flex-col gap-3"
          >
            <Text as="h2" font="heading-h3">
              {item.name}
            </Text>
            <TonStatusTag status={item.status} />
            <Text as="p" font="main-ui-body">
              {item.objective}
            </Text>
            <Text as="p" font="secondary-body" color="text-03">
              {item.reason}
            </Text>
            <Button
              prominence="secondary"
              onClick={() => setSelectedKey(item.key)}
            >
              {labels("details")}
            </Button>
          </div>
        ))}
      </div>
      <Modal
        open={selected != null}
        onOpenChange={(open) => {
          if (!open) setSelectedKey(null);
        }}
      >
        {selected && (
          <Modal.Content width="md">
            <Modal.Header
              title={selected.name}
              description={selected.objective}
            />
            <Modal.Body>
              <div className="flex flex-col gap-4">
                <TonStatusTag status={selected.status} />
                <Text as="p" font="main-ui-body">
                  {selected.reason}
                </Text>
                {(
                  [
                    [labels("requiredSources"), selected.required_sources],
                    [labels("available"), selected.available_capabilities],
                    [labels("blocked"), selected.blocked_capabilities],
                  ] as const
                ).map(([title, values]) => (
                  <div key={title} className="flex flex-col gap-1">
                    <Text font="main-ui-action">{title}</Text>
                    {values.length ? (
                      values.map((value) => (
                        <Text
                          key={value}
                          as="p"
                          font="main-ui-body"
                          color="text-03"
                        >
                          {value}
                        </Text>
                      ))
                    ) : (
                      <Text as="p" font="main-ui-body">
                        {t("notAvailable")}
                      </Text>
                    )}
                  </div>
                ))}
                <Text as="p" font="secondary-body">
                  {labels("lastExecution", {
                    date: selected.last_execution
                      ? format.dateTime(new Date(selected.last_execution), {
                          dateStyle: "short",
                          timeStyle: "short",
                        })
                      : t("notAvailable"),
                  })}
                </Text>
              </div>
            </Modal.Body>
            <Modal.Footer>
              <Button
                prominence="secondary"
                onClick={() => setSelectedKey(null)}
              >
                {labels("close")}
              </Button>
              <Button href="/ton/chat">{t("chat")}</Button>
            </Modal.Footer>
          </Modal.Content>
        )}
      </Modal>
    </div>
  );
}
