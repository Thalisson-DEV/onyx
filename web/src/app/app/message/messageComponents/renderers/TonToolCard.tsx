"use client";

import { useTranslations } from "next-intl";
import { Button, Text } from "@opal/components";
import { getBusinessLabel, TON_TOOL_NAMES } from "@/lib/ton/labels";
import { TonStatusTag } from "@/views/ton/components/TonStatusTag";

interface TonToolCardProps {
  toolName: string;
  data: unknown;
}

type JsonValue = string | number | boolean | null | JsonValue[] | JsonObject;
interface JsonObject {
  [key: string]: JsonValue;
}

function isJsonValue(value: unknown): value is JsonValue {
  return (
    value === null ||
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean" ||
    (Array.isArray(value) ? value.every(isJsonValue) : record(value))
  );
}

function record(value: unknown): value is JsonObject {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value) &&
    Object.values(value).every(isJsonValue)
  );
}

interface EvidenceRow {
  source_name?: string;
  sheet_name?: string;
  row_number?: number;
  confidence_level?: string | number;
  record_count?: number;
  status?: string;
  evidence?: string;
}

function evidenceRows(
  value: JsonObject | JsonValue[],
  depth = 0
): EvidenceRow[] {
  if (depth > 4) return [];
  if (Array.isArray(value))
    return value
      .flatMap((item) =>
        record(item) || Array.isArray(item) ? evidenceRows(item, depth + 1) : []
      )
      .slice(0, 10);
  if (!record(value)) return [];
  if (
    typeof value.row_number === "number" ||
    typeof value.sheet_name === "string" ||
    typeof value.record_count === "number"
  )
    return [
      {
        source_name:
          typeof value.source_name === "string"
            ? value.source_name
            : typeof value.source_key === "string" &&
                !/^[0-9a-f]{8}-[0-9a-f-]{27}$/i.test(value.source_key)
              ? value.source_key
              : undefined,
        record_count:
          typeof value.record_count === "number"
            ? value.record_count
            : undefined,
        status: typeof value.status === "string" ? value.status : undefined,
        evidence:
          typeof value.evidence === "string" ? value.evidence : undefined,
        sheet_name:
          typeof value.sheet_name === "string" ? value.sheet_name : undefined,
        row_number:
          typeof value.row_number === "number" ? value.row_number : undefined,
        confidence_level:
          typeof value.confidence_level === "string" ||
          typeof value.confidence_level === "number"
            ? value.confidence_level
            : undefined,
      },
    ];
  return ["evidence", "rows", "items", "details", "finding"]
    .flatMap((key) => {
      const child = value[key];
      return record(child) || Array.isArray(child)
        ? evidenceRows(child, depth + 1)
        : [];
    })
    .slice(0, 10);
}

export function TonToolCard({ toolName, data }: TonToolCardProps) {
  const t = useTranslations("controladoria");
  const labels = useTranslations("tonRuntime");
  const readiness = useTranslations("financialReadiness");
  const payload = record(data) && "data" in data ? data.data : data;
  const body =
    record(payload) && record(payload.output) ? payload.output : payload;
  const publication =
    record(payload) &&
    typeof payload.report_url === "string" &&
    payload.report_url.startsWith("/ton/controladoria/reports/")
      ? payload
      : null;
  const rows = record(body) || Array.isArray(body) ? evidenceRows(body) : [];
  const blockers =
    record(body) && record(body.blockers)
      ? Object.entries(body.blockers).filter(
          (entry): entry is [string, number] => typeof entry[1] === "number"
        )
      : [];
  const sources: JsonValue[] =
    Array.isArray(body) && body.every(isJsonValue)
      ? body
      : record(body) && Array.isArray(body.sources)
        ? body.sources
        : [];
  const sourceRows = sources
    .filter(record)
    .filter(
      (source) =>
        typeof source.acquisition === "string" ||
        typeof source.last_success_at === "string"
    );
  if (!publication && !rows.length && !blockers.length && !sourceRows.length)
    return null;

  return (
    <div className="border border-01 rounded-12 p-3 flex flex-col gap-2">
      <Text font="main-ui-action">
        {TON_TOOL_NAMES[toolName] ?? labels("evidence")}
      </Text>
      {record(data) && typeof data.data_context === "string" && (
        <Text as="p" font="secondary-body" color="text-03">
          {data.data_context}
        </Text>
      )}
      {record(body) && typeof body.dre_status === "string" && (
        <TonStatusTag status={body.dre_status} />
      )}
      {publication && (
        <>
          {typeof publication.status === "string" && (
            <TonStatusTag status={publication.status} />
          )}
          <Button href={String(publication.report_url)} size="sm">
            {labels("openReport")}
          </Button>
          {typeof publication.download_url === "string" &&
            publication.download_url.startsWith("/api/ton/agent/reports/") && (
              <Button
                href={publication.download_url}
                prominence="secondary"
                size="sm"
              >
                {t("download")}
              </Button>
            )}
        </>
      )}
      {blockers.slice(0, 4).map(([key, count]) => (
        <Text key={key} as="p" font="secondary-body">
          {t("blocker", { label: getBusinessLabel(key), count })}
        </Text>
      ))}
      {blockers.length > 0 && (
        <Button href="/ton/pendencias" prominence="secondary" size="sm">
          {t("readiness")}
        </Button>
      )}
      {rows.map((row, index) => (
        <div key={index} className="flex flex-col gap-2">
          {row.record_count !== undefined && (
            <Text as="p" font="secondary-body">
              {readiness("affected", { count: row.record_count })}
            </Text>
          )}
          {row.status && <TonStatusTag status={row.status} />}
          {row.record_count !== undefined && row.source_name && (
            <Text as="p" font="secondary-body">
              {getBusinessLabel(row.source_name)}
            </Text>
          )}
          {row.evidence && (
            <Text as="p" font="secondary-body">
              {getBusinessLabel(row.evidence)}
            </Text>
          )}
          {(row.sheet_name !== undefined || row.row_number !== undefined) && (
            <Text as="p" font="secondary-body">
              {t("evidence", {
                source:
                  typeof row.source_name === "string"
                    ? getBusinessLabel(row.source_name)
                    : t("notAvailable"),
                sheet:
                  typeof row.sheet_name === "string"
                    ? row.sheet_name
                    : t("notAvailable"),
                row:
                  typeof row.row_number === "number"
                    ? row.row_number
                    : t("notAvailable"),
                confidence:
                  typeof row.confidence_level === "string" ||
                  typeof row.confidence_level === "number"
                    ? getBusinessLabel(String(row.confidence_level))
                    : t("notAvailable"),
              })}
            </Text>
          )}
        </div>
      ))}
      {sourceRows.map((source, index) => (
        <div key={index} className="flex justify-between gap-2">
          <Text font="secondary-body">
            {typeof source.name === "string" ? source.name : t("notAvailable")}
          </Text>
          {typeof source.status === "string" && (
            <TonStatusTag status={source.status} />
          )}
        </div>
      ))}
      {sourceRows.length > 0 && (
        <Button href="/ton/data-sources" prominence="secondary" size="sm">
          {t("sources")}
        </Button>
      )}
    </div>
  );
}
