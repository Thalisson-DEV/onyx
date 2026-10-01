"use client";

import { useRef, useState } from "react";
import useSWR from "swr";
import { useFormatter, useTranslations } from "next-intl";
import { Text, Button, Modal } from "@opal/components";
import {
  SvgSliders,
  SvgCheckCircle,
  SvgClock,
  SvgSimpleLoader,
  SvgAlertTriangle,
  SvgFileText,
  SvgChevronRight,
} from "@opal/icons";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { hasPermission } from "@/lib/permissions";
import { Permission } from "@/lib/types";
import { useUser } from "@/providers/UserProvider";
import { getBusinessLabel } from "@/lib/ton/labels";
import { TonStatusTag } from "@/views/ton/components/TonStatusTag";
import type { Routine, Publication, ClosingOutput } from "@/views/ton/ControladoriaPage/types";

interface RoutineDefinition {
  code: string;
  name: string;
  cadence: string;
  schedule: string;
  description: string;
  specialist: string;
}

const ROUTINE_DEFINITIONS: RoutineDefinition[] = [
  {
    code: "R1",
    name: "Ingestão e Validação de Fontes",
    cadence: "Diária",
    schedule: "Todos os dias às 03:00",
    description: "Verifica integridade de planilhas e diagnósticos de importação do NG e Faturamento.",
    specialist: "Controladoria & Conciliação",
  },
  {
    code: "R2",
    name: "Sanidade e Pareamento Contábil",
    cadence: "Diária",
    schedule: "Todos os dias às 04:30",
    description: "Cruza movimentações financeiras com extratos e detecta inconsistências de saldo.",
    specialist: "Controladoria & Conciliação",
  },
  {
    code: "R3",
    name: "Fechamento Mensal e DRE",
    cadence: "Mensal (Flagship)",
    schedule: "Dia 01 de cada mês às 06:00",
    description: "Execução orquestrada de 21 regras determinísticas, apuração de prontidão e geração do relatório executivo.",
    specialist: "Controladoria Geral",
  },
  {
    code: "R4",
    name: "Revisão Orçamentária e Dotação",
    cadence: "Quinzenal",
    schedule: "Dias 05 e 20 às 08:00",
    description: "Compara limites de dotação aprovados com comprometimentos reais em cada obra.",
    specialist: "Planejamento & Orçamento",
  },
  {
    code: "R5",
    name: "Conformidade Contratual e Alçadas",
    cadence: "Semanal",
    schedule: "Toda segunda-feira às 07:00",
    description: "Audita se pagamentos e compras possuem contrato assinado e alçada autorizada.",
    specialist: "Gestão de Contratos",
  },
  {
    code: "R6",
    name: "Auditoria de Frota e Diesel",
    cadence: "Semanal",
    schedule: "Toda terça-feira às 07:00",
    description: "Analisa desvios de consumo de diesel por hora trabalhada de maquinário pesado.",
    specialist: "Frota & Equipamentos",
  },
  {
    code: "R7",
    name: "Conciliação de Medições de Obras",
    cadence: "Semanal",
    schedule: "Toda quarta-feira às 07:00",
    description: "Cruza relatórios diários de obra (RDO) com medições faturadas de subempreiteiros.",
    specialist: "Engenharia & Obras",
  },
  {
    code: "R8",
    name: "Conferência Fiscal e Retenções",
    cadence: "Mensal",
    schedule: "Dia 10 de cada mês às 09:00",
    description: "Valida retenções de ISS, IRRF e INSS para geração e conferência das guias municipais/federais.",
    specialist: "Fiscal & Tributário",
  },
  {
    code: "R9",
    name: "Consolidação Executiva da Diretoria",
    cadence: "Mensal",
    schedule: "Primeiro dia útil após fechamento",
    description: "Compila achados de todos os especialistas em sumário executivo para a diretoria Vale Norte.",
    specialist: "Compliance & Governança",
  },
];

export default function RoutinesPage() {
  const format = useFormatter();
  const { user } = useUser();
  const permissions = user?.effective_permissions ?? [];
  const canRead = hasPermission(permissions, Permission.READ_TON_SOURCES);
  const canRun =
    canRead &&
    hasPermission(permissions, Permission.READ_TON_REPORTS) &&
    hasPermission(permissions, Permission.MANAGE_TON_REPORTS);

  const routines = useSWR<Routine[]>(
    canRead ? "/api/ton/agent/routines" : null,
    errorHandlingFetcher
  );
  const snapshot = useSWR<ClosingOutput>(
    canRead ? "/api/ton/agent/closing" : null,
    errorHandlingFetcher
  );
  const publications = useSWR<Publication[]>(
    canRead ? "/api/ton/agent/reports" : null,
    errorHandlingFetcher
  );

  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState(false);
  const [result, setResult] = useState<Publication | null>(null);
  const [showStepsModal, setShowStepsModal] = useState(false);
  const requestId = useRef<string | null>(null);
  const inFlight = useRef(false);

  const r3Backend = routines.data?.find((r) => r.key === "R3");
  const latestReport = publications.data?.[0];

  async function runR3() {
    if (!canRun || inFlight.current || !snapshot.data) return;
    inFlight.current = true;
    setRunning(true);
    setRunError(false);
    requestId.current ??= crypto.randomUUID();
    try {
      const response = await fetch("/api/ton/agent/routines/R3/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          request_id: requestId.current,
          normalization_run_id: snapshot.data.normalization_run_id,
          structure_version_id: snapshot.data.structure_version_id,
          period: snapshot.data.period,
          unit_id: snapshot.data.unit_id,
        }),
      });
      if (!response.ok) throw new Error("R3 execution failed");
      const pub: Publication = await response.json();
      setResult(pub);
      requestId.current = null;
      await publications.mutate();
      await routines.mutate();
    } catch {
      setRunError(true);
    } finally {
      inFlight.current = false;
      setRunning(false);
    }
  }

  return (
    <div className="flex flex-col gap-6 p-6 max-w-6xl mx-auto w-full">
      {/* Page Header */}
      <div className="flex flex-col gap-1">
        <Text as="h1" font="heading-h2" color="text-05">
          Rotinas Operacionais do TON
        </Text>
        <Text as="p" font="main-ui-body" color="text-03">
          Orquestração automatizada e auditável de checagens financeiras, contábeis e de obras (R1 a R9).
        </Text>
      </div>

      {/* Flagship R3 Banner */}
      <div className="border-2 border-theme-primary-04 rounded-16 p-6 background-neutral-00 flex flex-col gap-4 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-01">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-12 bg-action-selection-02 text-action-selection-01">
              <SvgSliders className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <Text font="heading-h3" color="text-05">
                  R3 — Fechamento Mensal e DRE Oficial
                </Text>
                <TonStatusTag status="READY" />
              </div>
              <p className="text-sm text-text-03">
                Execução central que consolida as 21 etapas de sanidade, conformidade e cálculo da DRE.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {canRun && (
              <Button
                disabled={running || !snapshot.data}
                onClick={runR3}
                icon={running ? SvgSimpleLoader : undefined}
              >
                {running ? "Executando fechamento…" : "Executar fechamento agora"}
              </Button>
            )}
          </div>
        </div>

        {runError && (
          <div className="p-3 rounded-8 bg-status-error-01 border border-status-error-02 text-status-error-05 text-sm">
            A execução falhou. Tente novamente para recuperar ou concluir a mesma solicitação.
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 pt-1">
          <div>
            <Text font="main-ui-muted" color="text-03">
              Cadência
            </Text>
            <p className="text-sm font-semibold text-text-05">
              Mensal (Dia 01 às 06:00)
            </p>
          </div>

          <div>
            <Text font="main-ui-muted" color="text-03">
              Último status
            </Text>
            <div className="flex items-center gap-1.5 mt-0.5">
              <TonStatusTag status={r3Backend?.status ?? "READY"} />
            </div>
          </div>

          <div>
            <Text font="main-ui-muted" color="text-03">
              Último resultado
            </Text>
            <Text font="main-ui-body" color="text-04">
              {r3Backend?.last_result ?? "Fechamento preliminar disponível"}
            </Text>
          </div>

          <div>
            <Text font="main-ui-muted" color="text-03">
              Ações
            </Text>
            <div className="flex items-center gap-3 mt-0.5">
              {(result || latestReport) && (
                <Button
                  href={`/ton/controladoria/reports/${result?.revision_id ?? latestReport?.revision_id}`}
                  prominence="secondary"
                  size="sm"
                >
                  Ver relatório
                </Button>
              )}
              <Button
                prominence="tertiary"
                size="sm"
                onClick={() => setShowStepsModal(true)}
              >
                Ver 21 etapas
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* R1 - R9 List */}
      <div className="flex flex-col gap-3">
        <Text as="h2" font="heading-h3" color="text-05">
          Todas as Rotinas (R1 a R9)
        </Text>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {ROUTINE_DEFINITIONS.map((def) => {
            const backendInfo = routines.data?.find((r) => r.key === def.code);
            const status = backendInfo?.status ?? (def.code === "R3" ? "READY" : "ACTIVE");

            return (
              <div
                key={def.code}
                className="border border-01 rounded-12 p-4 background-neutral-00 flex flex-col justify-between gap-3 hover:border-02 transition-colors"
              >
                <div className="flex flex-col gap-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-background-neutral-02 text-text-04">
                      {def.code}
                    </span>
                    <TonStatusTag status={status} />
                  </div>

                  <Text font="main-ui-action" color="text-05">
                    {def.name}
                  </Text>
                  <p className="text-xs text-text-04 line-clamp-2">
                    {def.description}
                  </p>
                </div>

                <div className="pt-2 border-t border-01 flex flex-col gap-1 text-xs">
                  <div className="flex items-center justify-between text-text-03">
                    <span>Cadência:</span>
                    <span className="text-text-04 font-medium">{def.cadence}</span>
                  </div>
                  <div className="flex items-center justify-between text-text-03">
                    <span>Especialista:</span>
                    <span className="text-text-04 truncate max-w-[170px]">{def.specialist}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 21 Steps Modal */}
      {showStepsModal && (
        <Modal
          open={showStepsModal}
          onOpenChange={(open) => {
            if (!open) setShowStepsModal(false);
          }}
        >
          <Modal.Content width="md">
            <Modal.Header
              title="Etapas da Rotina R3 — Fechamento Mensal"
              description="Detalhamento das 21 etapas determinísticas executadas pelo motor da controladoria."
            />
            <Modal.Body>
              <div className="flex flex-col gap-3 max-h-[60vh] overflow-y-auto pr-1">
                {(latestReport?.steps ?? []).length > 0 ? (
                  latestReport?.steps.map((st, idx) => (
                    <div key={idx} className="border-b border-01 pb-2 flex items-start justify-between gap-2">
                      <div className="flex flex-col">
                        <span className="text-sm font-semibold text-text-05">
                          {st.code} — {st.specialist}
                        </span>
                        {st.reason && (
                          <span className="text-xs text-text-03">
                            {st.reason}
                          </span>
                        )}
                      </div>
                      <TonStatusTag status={st.status} />
                    </div>
                  ))
                ) : (
                  <div className="flex flex-col gap-2 text-sm text-text-04">
                    <p>1. Ingestão de Lançamentos Contábeis (NG/Keevo)</p>
                    <p>2. Ingestão de Notas Fiscais e Faturamento</p>
                    <p>3. Validação de Unidades e Centros de Custo</p>
                    <p>4. Validação do Plano de Contas e Estrutura DRE</p>
                    <p>5. Conciliação Bancária e Pareamento de Operações</p>
                    <p>6. Apuração de Retenções Tributárias e Competência</p>
                    <p>7. Cruzamento de Orçamento Executivo e Dotações</p>
                    <p>8. Cálculo das Linhas Sintéticas da DRE</p>
                    <p>9. Verificação de Bloqueadores e Prontidão Financeira</p>
                    <p>10. Consolidação dos Achados dos 9 Especialistas</p>
                    <p>11 a 21. Validação de Integridade, Rastreabilidade e Publicação</p>
                  </div>
                )}
              </div>
            </Modal.Body>
            <Modal.Footer>
              <Button prominence="secondary" onClick={() => setShowStepsModal(false)}>
                Fechar
              </Button>
            </Modal.Footer>
          </Modal.Content>
        </Modal>
      )}
    </div>
  );
}
