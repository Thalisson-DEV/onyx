"use client";

import React from "react";
import { Button, Text } from "@opal/components";
import {
  SvgFileText,
  SvgDownload,
  SvgExternalLink,
  SvgCheckCircle,
  SvgAlertTriangle,
  SvgFiles,
  SvgInfo,
} from "@opal/icons";
import { getBusinessLabel } from "@/lib/ton/labels";
import { TonStatusTag } from "@/views/ton/components/TonStatusTag";

interface TonToolCardProps {
  toolName: string;
  data: unknown;
}

export function TonToolCard({ toolName, data }: TonToolCardProps) {
  if (!data || typeof data !== "object") return null;

  const rawObj = data as Record<string, unknown>;
  const payload =
    "data" in rawObj && rawObj.data !== undefined ? rawObj.data : rawObj;

  if (!payload || typeof payload !== "object") return null;

  // 1. Report publication result (R3 / Closing Report)
  if ("report_url" in payload && typeof payload.report_url === "string") {
    const pub = payload as {
      report_url: string;
      download_url?: string;
      status?: string;
      routine_code?: string;
      period?: string;
      output?: { dre_status?: string; blockers?: Record<string, number> };
    };

    return (
      <div className="rounded-12 border border-01 background-neutral-00 p-3.5 flex flex-col gap-2.5 my-1 max-w-lg shadow-sm">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <SvgFileText className="w-4 h-4 text-action-selection-01 shrink-0" />
            <span className="text-xs font-semibold text-text-05">
              Relatório do Fechamento {pub.period ? `(${pub.period})` : ""}
            </span>
          </div>
          {pub.status && (
            <TonStatusTag status={pub.status} />
          )}
        </div>

        {pub.output?.blockers && Object.keys(pub.output.blockers).length > 0 && (
          <div className="flex flex-wrap gap-1.5 text-xs">
            {Object.entries(pub.output.blockers).slice(0, 3).map(([k, count]) => (
              <span
                key={k}
                className="bg-background-neutral-01 px-2 py-0.5 rounded text-text-04"
              >
                {getBusinessLabel(k)}: {count}
              </span>
            ))}
          </div>
        )}

        <div className="flex items-center gap-2 pt-1">
          <Button href={pub.report_url} size="sm" icon={SvgExternalLink}>
            Abrir Relatório
          </Button>
          {pub.download_url && (
            <Button
              href={pub.download_url}
              prominence="secondary"
              size="sm"
              icon={SvgDownload}
            >
              Baixar
            </Button>
          )}
        </div>
      </div>
    );
  }

  // 2. DRE Readiness / Blockers
  if ("dre_status" in payload && typeof payload.dre_status === "string") {
    const readiness = payload as {
      dre_status: string;
      period?: string;
      scope?: string;
      blockers?: Record<string, number>;
    };

    const blockers = readiness.blockers ?? {};
    const blockerCount = Object.values(blockers).reduce((a, b) => a + b, 0);

    return (
      <div className="rounded-12 border border-01 background-neutral-00 p-3.5 flex flex-col gap-2.5 my-1 max-w-lg shadow-sm">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <SvgAlertTriangle className="w-4 h-4 text-status-warning-05 shrink-0" />
            <span className="text-xs font-semibold text-text-05">
              Prontidão da DRE
            </span>
          </div>
          <TonStatusTag status={readiness.dre_status} />
        </div>

        <div className="flex flex-col gap-1.5 text-xs text-text-04">
          <div className="flex items-center justify-between">
            <span>Bloqueios pendentes:</span>
            <span className="font-semibold text-text-05">{blockerCount}</span>
          </div>
          {Object.entries(blockers).slice(0, 4).map(([label, count]) => (
            <div
              key={label}
              className="flex items-center justify-between bg-background-neutral-01 px-2 py-1 rounded"
            >
              <span className="truncate">{getBusinessLabel(label)}</span>
              <span className="font-semibold ms-2">{count}</span>
            </div>
          ))}
        </div>

        <div className="pt-1">
          <Button href="/ton/pendencias" prominence="secondary" size="sm">
            Ver todas as pendências
          </Button>
        </div>
      </div>
    );
  }

  // 3. Evidence / Single Lineage
  if (
    "source_snapshot_id" in payload ||
    "sheet_name" in payload ||
    "row_number" in payload
  ) {
    const evidence = payload as {
      source_snapshot_id?: string | null;
      sheet_name?: string | null;
      row_number?: number | null;
      confidence_level?: string | number | null;
      details?: string | null;
    };

    return (
      <div className="rounded-12 border border-01 background-neutral-00 p-3.5 flex flex-col gap-2 my-1 max-w-lg shadow-sm">
        <div className="flex items-center gap-2 text-xs font-semibold text-text-05">
          <SvgInfo className="w-4 h-4 text-action-selection-01" />
          Evidência Contábil
        </div>
        <div className="grid grid-cols-2 gap-2 text-xs bg-background-neutral-01 p-2.5 rounded-8">
          <div>
            <span className="text-text-03">Planilha: </span>
            <span className="font-medium text-text-05">
              {evidence.sheet_name ?? "—"}
            </span>
          </div>
          <div>
            <span className="text-text-03">Linha: </span>
            <span className="font-medium text-text-05">
              {evidence.row_number ?? "—"}
            </span>
          </div>
          <div className="col-span-2">
            <span className="text-text-03">Confiança: </span>
            <TonStatusTag status={String(evidence.confidence_level ?? "100%")} />
          </div>
        </div>
      </div>
    );
  }

  // 4. Sources list
  const sourcesList = Array.isArray(payload)
    ? payload
    : "sources" in payload && Array.isArray((payload as any).sources)
      ? (payload as any).sources
      : null;

  if (
    sourcesList &&
    sourcesList.length > 0 &&
    ("acquisition" in sourcesList[0] || "last_success_at" in sourcesList[0])
  ) {
    return (
      <div className="rounded-12 border border-01 background-neutral-00 p-3.5 flex flex-col gap-2.5 my-1 max-w-lg shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-semibold text-text-05">
            <SvgFiles className="w-4 h-4 text-action-selection-01" />
            Fontes Financeiras ({sourcesList.length})
          </div>
          <Button href="/ton/data-sources" prominence="tertiary" size="sm">
            Gerenciar
          </Button>
        </div>

        <div className="flex flex-col gap-1.5 text-xs">
          {sourcesList.slice(0, 4).map((src: any, idx: number) => (
            <div
              key={src.id ?? src.key ?? idx}
              className="flex items-center justify-between p-2 rounded bg-background-neutral-01 border border-01"
            >
              <div className="flex flex-col min-w-0">
                <span className="font-medium text-text-05 truncate">
                  {src.name ?? src.source_id ?? "Fonte"}
                </span>
                <span className="text-[10px] text-text-03">
                  {src.acquisition ?? "Importação"}
                </span>
              </div>
              <TonStatusTag status={src.status} />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return null;
}
