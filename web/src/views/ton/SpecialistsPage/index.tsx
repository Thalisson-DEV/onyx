"use client";

import { useState } from "react";
import { Text, Button, Modal } from "@opal/components";
import {
  SvgManageAgent,
  SvgCheckCircle,
  SvgAlertTriangle,
  SvgClock,
  SvgChevronRight,
  SvgSliders,
} from "@opal/icons";
import { TonStatusTag } from "@/views/ton/components/TonStatusTag";

interface Specialist {
  id: string;
  name: string;
  area: string;
  purpose: string;
  status: "Operacional" | "Parcial" | "Aguardando fonte";
  dependency: string;
  role: string;
  availableCapabilities: string[];
  unavailableCapabilities: string[];
  requiredSources: string[];
}

const SPECIALISTS: Specialist[] = [
  {
    id: "financeiro",
    name: "Controladoria & Conciliação",
    area: "Financeiro",
    purpose: "Conciliação bancária, validação de regras determinísticas e apuração da DRE.",
    status: "Operacional",
    dependency: "Lançamentos NG / Keevo e Faturamento",
    role: "Especialista central responsável pela integridade contábil e conformidade do fechamento mensal.",
    availableCapabilities: [
      "Validação de semântica do realizado",
      "Detecção de contas e unidades não vinculadas",
      "Conciliação bancária e pareamento de lançamentos",
      "Geração da demonstração DRE oficial",
    ],
    unavailableCapabilities: [],
    requiredSources: ["Lançamentos NG / Keevo (XLSX)", "Faturamento / Notas fiscais (XLS)"],
  },
  {
    id: "planejamento",
    name: "Planejamento & Orçamento",
    area: "Planejamento",
    purpose: "Acompanhamento do orçamento executivo e comparativo Orçado vs. Realizado.",
    status: "Operacional",
    dependency: "Dotação orçamentária Vale Norte",
    role: "Responsável pelo alinhamento das previsões orçamentárias com a realidade das obras.",
    availableCapabilities: [
      "Vínculo de períodos da dotação",
      "Cálculo de variação nominal e percentual",
      "Histórico de revisões orçamentárias",
    ],
    unavailableCapabilities: ["Ajuste preditivo de contingência"],
    requiredSources: ["Planilha de dotação orçamentária"],
  },
  {
    id: "contratos",
    name: "Gestão de Contratos",
    area: "Contratos",
    purpose: "Supervisão de contratos com clientes, fornecedores e subempreiteiros.",
    status: "Operacional",
    dependency: "Base contratual Vale Norte",
    role: "Garante que desembolsos e receitas estejam amparados por instrumentos contratuais vigentes.",
    availableCapabilities: [
      "Verificação de alçadas e vigências",
      "Cruzamento com medições de serviço",
      "Alerta de desvios contratuais",
    ],
    unavailableCapabilities: [],
    requiredSources: ["Contratos e aditivos contratuais"],
  },
  {
    id: "compliance",
    name: "Compliance & Governança",
    area: "Compliance",
    purpose: "Auditoria contínua de alçadas, trilha de integridade e decisões humanas.",
    status: "Operacional",
    dependency: "Trilha de auditoria TON",
    role: "Assegura que nenhuma aprovação seja automática e registra a rastreabilidade das decisões.",
    availableCapabilities: [
      "Trilha de imutabilidade dos relatórios",
      "Registro de justificativas para exceções",
      "Validação de conformidade regulatória",
    ],
    unavailableCapabilities: [],
    requiredSources: ["Eventos de auditoria TON"],
  },
  {
    id: "frota",
    name: "Frota & Equipamentos",
    area: "Operações",
    purpose: "Monitoramento de consumo de diesel, manutenção e produtividade de máquinas.",
    status: "Parcial",
    dependency: "Integração telemática e abastecimentos NG",
    role: "Otimiza a alocação de pesados e previne fraudes em combustíveis e peças.",
    availableCapabilities: [
      "Análise de consumo por centro de custo",
      "Identificação de desvios em relatórios de diesel",
    ],
    unavailableCapabilities: [
      "Telemetria em tempo real (aguarda conexão IoT)",
      "Ordens de manutenção preventiva automáticas",
    ],
    requiredSources: ["Boletins de abastecimento NG", "Telemetria de campo"],
  },
  {
    id: "suprimentos",
    name: "Suprimentos & Compras",
    area: "Suprimentos",
    purpose: "Gestão de ordens de compra, cotações e entrega de insumos críticos em obra.",
    status: "Parcial",
    dependency: "Módulo de compras NG",
    role: "Evita paralisações de frente de obra por falta de material e audita preços praticados.",
    availableCapabilities: [
      "Conferência de pedidos faturados",
      "Rastreio de insumos de curva A",
    ],
    unavailableCapabilities: ["Cotação automatizada multiportais"],
    requiredSources: ["Ordens de compra NG", "Notas de entrada"],
  },
  {
    id: "fiscal",
    name: "Fiscal & Tributário",
    area: "Fiscal",
    purpose: "Apuração de retenções tributárias (ISS, IR, INSS) e notas fiscais de serviço.",
    status: "Parcial",
    dependency: "Notas fiscais e guias de retenção",
    role: "Audita a conformidade de retenções e evita contingências com prefeituras e receita.",
    availableCapabilities: [
      "Validação de competência tributária",
      "Identificação de retenções ambíguas",
    ],
    unavailableCapabilities: ["Emissão direta de guias tributárias"],
    requiredSources: ["Xmls/Notas fiscais de serviço", "Guias de recolhimento"],
  },
  {
    id: "operacoes",
    name: "Engenharia & Obras",
    area: "Operações",
    purpose: "Acompanhamento do diário de obra e avanço físico das etapas construtivas.",
    status: "Parcial",
    dependency: "Boletins de medição e RDOs",
    role: "Vincula medições de campo ao faturamento e à apropriação de custos.",
    availableCapabilities: [
      "Comparação do avanço físico com desembolso",
    ],
    unavailableCapabilities: ["Sincronização com Zeev (aguarda acesso direto)"],
    requiredSources: ["Relatórios Diários de Obra (RDO)", "Medições aprovadas"],
  },
  {
    id: "rh",
    name: "Gente & Gestão",
    area: "RH / DP",
    purpose: "Conferência de efetivo em obra, alocação de equipes e conformidade de encargos.",
    status: "Aguardando fonte",
    dependency: "Folha de pagamento e cartão de ponto",
    role: "Cruza folha de pagamento com apropriação de mão de obra em cada centro de custo.",
    availableCapabilities: [],
    unavailableCapabilities: [
      "Conferência de apropriação de mão de obra direta",
      "Auditoria de encargos sociais em obras",
    ],
    requiredSources: ["Arquivo de folha de pagamento", "Controle de ponto"],
  },
];

export default function SpecialistsPage() {
  const [selectedSpecialist, setSelectedSpecialist] = useState<Specialist | null>(null);

  const operationalCount = SPECIALISTS.filter((s) => s.status === "Operacional").length;
  const partialCount = SPECIALISTS.filter((s) => s.status === "Parcial").length;
  const awaitingCount = SPECIALISTS.filter((s) => s.status === "Aguardando fonte").length;

  return (
    <div className="flex flex-col gap-6 p-6 max-w-6xl mx-auto w-full">
      {/* Header */}
      <div className="flex flex-col gap-1">
        <Text as="h1" font="heading-h2" color="text-05">
          Especialistas do TON
        </Text>
        <p className="text-sm text-text-03">
          Rede de agentes analíticos dedicados a cada domínio operacional e financeiro da Vale Norte.
        </p>
      </div>

      {/* Summary strip */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="border border-01 rounded-12 p-4 background-neutral-00 flex items-center justify-between">
          <div className="flex flex-col">
            <span className="text-xs text-text-03">Operacionais</span>
            <span className="text-2xl font-bold text-status-success-05">
              {operationalCount}
            </span>
          </div>
          <TonStatusTag status="READY" />
        </div>

        <div className="border border-01 rounded-12 p-4 background-neutral-00 flex items-center justify-between">
          <div className="flex flex-col">
            <span className="text-xs text-text-03">Parciais</span>
            <span className="text-2xl font-bold text-status-warning-05">
              {partialCount}
            </span>
          </div>
          <TonStatusTag status="IN_PROGRESS" />
        </div>

        <div className="border border-01 rounded-12 p-4 background-neutral-00 flex items-center justify-between">
          <div className="flex flex-col">
            <span className="text-xs text-text-03">Aguardando fonte</span>
            <span className="text-2xl font-bold text-action-selection-01">
              {awaitingCount}
            </span>
          </div>
          <TonStatusTag status="PENDING" />
        </div>
      </div>

      {/* Specialists Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {SPECIALISTS.map((spec) => {
          return (
            <div
              key={spec.id}
              className="border border-01 rounded-12 p-5 background-neutral-00 flex flex-col justify-between gap-4 hover:border-02 transition-colors cursor-pointer"
              onClick={() => setSelectedSpecialist(spec)}
            >
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <SvgManageAgent className="w-5 h-5 text-text-04" />
                    <Text font="main-ui-action" color="text-05">
                      {spec.name}
                    </Text>
                  </div>
                  <TonStatusTag status={spec.status} />
                </div>
                <p className="text-xs text-text-04 line-clamp-2">
                  {spec.purpose}
                </p>
              </div>

              <div className="flex flex-col gap-2 pt-3 border-t border-01">
                <div className="flex items-center justify-between text-xs text-text-03">
                  <span>Dependência:</span>
                  <span className="font-medium text-text-04 truncate max-w-[180px]">
                    {spec.dependency}
                  </span>
                </div>
                <div className="flex items-center justify-end text-xs text-action-selection-01 font-medium">
                  <span>Ver detalhes</span>
                  <SvgChevronRight className="w-3.5 h-3.5 ms-1" />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Detail Modal */}
      {selectedSpecialist && (
        <Modal
          open={selectedSpecialist !== null}
          onOpenChange={(open) => {
            if (!open) setSelectedSpecialist(null);
          }}
        >
          <Modal.Content width="md">
            <Modal.Header
              title={selectedSpecialist.name}
              description={`Domínio: ${selectedSpecialist.area}`}
            />
            <Modal.Body>
              <div className="flex flex-col gap-5 pt-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-text-05">Status operacional:</span>
                  <TonStatusTag status={selectedSpecialist.status} />
                </div>

                <div className="flex flex-col gap-1">
                  <Text font="main-ui-action" color="text-05">
                    Papel na Controladoria
                  </Text>
                  <p className="text-sm text-text-03">
                    {selectedSpecialist.role}
                  </p>
                </div>

                <div className="flex flex-col gap-2">
                  <Text font="main-ui-action" color="text-05">
                    Capacidades disponíveis
                  </Text>
                  {selectedSpecialist.availableCapabilities.length === 0 ? (
                    <p className="text-xs text-text-03">
                      Nenhuma capacidade ativa aguardando dados da fonte.
                    </p>
                  ) : (
                    <ul className="flex flex-col gap-1.5 list-disc list-inside text-sm text-text-04">
                      {selectedSpecialist.availableCapabilities.map((cap, idx) => (
                        <li key={idx}>{cap}</li>
                      ))}
                    </ul>
                  )}
                </div>

                {selectedSpecialist.unavailableCapabilities.length > 0 && (
                  <div className="flex flex-col gap-2">
                    <Text font="main-ui-action" color="text-05">
                      Capacidades bloqueadas / pendentes
                    </Text>
                    <ul className="flex flex-col gap-1.5 list-disc list-inside text-sm text-text-03">
                      {selectedSpecialist.unavailableCapabilities.map((cap, idx) => (
                        <li key={idx}>{cap}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="flex flex-col gap-1 pt-3 border-t border-01">
                  <span className="text-xs text-text-03">Fontes necessárias:</span>
                  <p className="text-sm text-text-04">
                    {selectedSpecialist.requiredSources.join(", ")}
                  </p>
                </div>
              </div>
            </Modal.Body>
            <Modal.Footer>
              <Button
                prominence="secondary"
                onClick={() => setSelectedSpecialist(null)}
              >
                Fechar
              </Button>
            </Modal.Footer>
          </Modal.Content>
        </Modal>
      )}
    </div>
  );
}
