"use client";

import useSWR from "swr";
import { useFormatter } from "next-intl";
import { Text, Button } from "@opal/components";
import { SvgFileText, SvgDownload, SvgChevronRight, SvgClock } from "@opal/icons";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { hasPermission } from "@/lib/permissions";
import { Permission } from "@/lib/types";
import { useUser } from "@/providers/UserProvider";
import { getBusinessLabel } from "@/lib/ton/labels";
import { TonStatusTag } from "@/views/ton/components/TonStatusTag";
import type { Publication } from "@/views/ton/ControladoriaPage/types";

export default function ReportsPage() {
  const format = useFormatter();
  const { user } = useUser();
  const permissions = user?.effective_permissions ?? [];
  const canReadReports = hasPermission(permissions, Permission.READ_TON_REPORTS);

  const publications = useSWR<Publication[]>(
    canReadReports ? "/api/ton/agent/reports" : null,
    errorHandlingFetcher
  );

  return (
    <div className="flex flex-col gap-6 p-6 max-w-6xl mx-auto w-full">
      {/* Header */}
      <div className="flex flex-col gap-1">
        <Text as="h1" font="heading-h2" color="text-05">
          Relatórios da Controladoria
        </Text>
        <Text as="p" font="main-ui-body" color="text-03">
          Entregáveis executivos oficiais, análises de fechamento e demonstrações auditadas.
        </Text>
      </div>

      {publications.isLoading && (
        <div className="p-8 text-center text-text-03 text-sm">
          Carregando relatórios disponíveis…
        </div>
      )}

      {publications.error && (
        <div className="p-4 rounded-12 bg-status-error-01 text-status-error-05 text-sm">
          Não foi possível carregar os relatórios. Verifique sua autorização.
        </div>
      )}

      {publications.data && publications.data.length === 0 && (
        <div className="border border-01 rounded-16 p-12 text-center background-neutral-00 flex flex-col items-center gap-3">
          <SvgFileText className="w-10 h-10 text-text-02" />
          <Text font="main-ui-action" color="text-05">
            Nenhum relatório publicado ainda
          </Text>
          <Text font="main-ui-body" color="text-03">
            Os relatórios são gerados automaticamente pela rotina de fechamento (R3) ou solicitados no TON.
          </Text>
          <Button href="/ton/rotinas" prominence="secondary">
            Ir para Rotinas
          </Button>
        </div>
      )}

      {publications.data && publications.data.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {publications.data.map((pub) => (
            <div
              key={pub.revision_id}
              className="border border-01 rounded-16 p-5 background-neutral-00 flex flex-col justify-between gap-4 hover:border-02 transition-colors"
            >
                <div className="flex flex-col gap-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-background-neutral-02 text-text-04">
                      {pub.output?.period ?? ""}
                    </span>
                    <TonStatusTag status={pub.status} />
                  </div>

                  <div>
                    <h3 className="text-base font-semibold text-text-05">
                      Relatório de Fechamento Contábil — {pub.output?.scope ?? ""}
                    </h3>
                    <p className="text-xs text-text-03 mt-1">
                      {pub.output?.data_context ?? "Base financeira compilada e analisada."}
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs pt-2 border-t border-01 text-text-03">
                    <div>
                      <span>Bloqueadores: </span>
                      <span className="font-semibold text-text-04">
                        {Object.values(pub.output?.blockers ?? {}).reduce((a, b) => a + b, 0)}
                      </span>
                    </div>
                    <div>
                      <span>Achados: </span>
                      <span className="font-semibold text-text-04">
                        {pub.output?.findings?.length ?? 0}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-3 border-t border-01">
                  <span className="text-xs text-text-03 font-mono">
                    Rev: {pub.revision_id.slice(0, 8)}…
                  </span>
                  <div className="flex items-center gap-2">
                    {pub.download_url && (
                      <Button
                        href={pub.download_url}
                        prominence="tertiary"
                        size="sm"
                        icon={SvgDownload}
                      >
                        Baixar
                      </Button>
                    )}
                    <Button
                      href={`/ton/controladoria/reports/${pub.revision_id}`}
                      size="sm"
                      icon={SvgChevronRight}
                    >
                      Abrir
                    </Button>
                  </div>
                </div>
              </div>
          ))}
        </div>
      )}
    </div>
  );
}
