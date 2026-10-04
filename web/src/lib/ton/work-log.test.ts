import { PacketType } from "@/app/app/services/streamingModels";
import type { Packet } from "@/app/app/services/streamingModels";
import type { TurnGroup } from "@/app/app/message/messageComponents/timeline/transformers";
import { buildWorkLog, querySubject } from "@/lib/ton/work-log";
import { buildDataPreview } from "@/lib/ton/data-preview";

// Synthetic payloads only; real Vale Norte data never enters tests.

function packet(turn: number, tab: number, obj: Packet["obj"]): Packet {
  return { placement: { turn_index: turn, tab_index: tab }, obj };
}

function toolStep(
  turn: number,
  tab: number,
  name: string,
  args: Record<string, unknown>,
  data: unknown,
  ended = true
) {
  const packets: Packet[] = [
    packet(turn, tab, { type: PacketType.CUSTOM_TOOL_START, tool_name: name }),
    packet(turn, tab, {
      type: PacketType.CUSTOM_TOOL_ARGS,
      tool_name: name,
      tool_args: args,
    }),
  ];
  if (ended) {
    packets.push(
      packet(turn, tab, {
        type: PacketType.CUSTOM_TOOL_DELTA,
        tool_name: name,
        response_type: "json",
        data,
      }),
      packet(turn, tab, { type: PacketType.SECTION_END })
    );
  }
  return { key: `${turn}-${tab}`, turnIndex: turn, tabIndex: tab, packets };
}

function reasoningStep(turn: number, ended = true) {
  const packets: Packet[] = [
    packet(turn, 0, { type: PacketType.REASONING_START }),
    packet(turn, 0, {
      type: PacketType.REASONING_DELTA,
      reasoning: "private text with run_id 123",
    }),
  ];
  if (ended) packets.push(packet(turn, 0, { type: PacketType.REASONING_DONE }));
  return { key: `${turn}-0`, turnIndex: turn, tabIndex: 0, packets };
}

const closing = {
  run_id: "00000000-0000-0000-0000-000000000001",
  status: "Concluído",
  output: {
    period: "2026-07-01",
    unit_id: null,
    dre_status: "Pendente",
    blockers: { "Conciliação sem decisão": 2 },
    sources: [
      {
        name: "Fonte sintética",
        status: "Atualizado",
        last_success_at: "2026-07-31T12:00:00Z",
        acquisition: "Importação manual",
      },
    ],
    specialists: [
      {
        key: "CFO",
        name: "TON CFO",
        status: "Operacional",
        reason: "Consultou.",
      },
      {
        key: "COO",
        name: "TON COO",
        status: "Bloqueado",
        reason: "Sem fonte.",
      },
    ],
  },
  steps: [
    { specialist: "CFO", code: "Consulta das fontes", status: "Concluído" },
    {
      specialist: "CFO",
      code: "Quantificação",
      status: "Não executado",
      reason: "Sem impacto calculado.",
    },
  ],
};

const groups: TurnGroup[] = [
  { turnIndex: 0, isParallel: false, steps: [reasoningStep(0)] },
  {
    turnIndex: 1,
    isParallel: true,
    steps: [
      toolStep(
        1,
        0,
        "ton_analyze_closing",
        { period: "2026-07-01" },
        { data: closing }
      ),
      toolStep(1, 1, "ton_list_findings", { limit: 25 }, [
        { id: "x", blocking: true },
        { id: "y", blocking: false },
      ]),
    ],
  },
];

describe("buildWorkLog", () => {
  it("describes each step in business terms without reasoning text", () => {
    const log = buildWorkLog(groups, [], { stopped: true, answering: false });
    expect(log.steps.map((step) => step.kind)).toEqual(["think", "queries"]);
    expect(log.steps[0]).toMatchObject({ kind: "think", phase: "plan" });
    expect(JSON.stringify(log)).not.toContain("private text");

    const [analysis, findings] = log.queries;
    expect(analysis?.subject).toBe("Julho de 2026 · Consolidado");
    expect(analysis?.summary).toBe(
      "DRE pendente · 2 pendências · 1 especialista atuou"
    );
    expect(findings?.summary).toBe("2 achados · 1 bloqueia a publicação");
  });

  it("collects specialists, sources and data origins", () => {
    const log = buildWorkLog(groups, [], { stopped: true, answering: false });
    expect(log.specialists.map((item) => item.key)).toEqual(["CFO", "COO"]);
    expect(log.specialists[0]?.steps).toHaveLength(2);
    expect(log.sources.map((source) => source.label)).toEqual([
      "Análise do fechamento",
      "Achados da revisão",
    ]);
    expect(log.origins).toEqual([
      expect.objectContaining({
        name: "Fonte sintética",
        acquisition: "Importação manual",
      }),
    ]);
  });

  it("reports the running query while TON works", () => {
    const live: TurnGroup[] = [
      groups[0]!,
      {
        turnIndex: 1,
        isParallel: false,
        steps: [toolStep(1, 0, "ton_get_dre_result", {}, null, false)],
      },
    ];
    const log = buildWorkLog(live, [], { stopped: false, answering: false });
    expect(log.running).toBe(true);
    expect(log.current).toBe("Lendo o resultado oficial da DRE");
  });

  it("names the unit instead of its id", () => {
    expect(
      querySubject(
        "ton_get_dre_readiness",
        { period: "2026-07-01", unit_id: "unit-1" },
        undefined,
        (id) => (id === "unit-1" ? "Unidade Sintética" : null)
      )
    ).toBe("Julho de 2026 · Unidade Sintética");
  });
});

describe("buildDataPreview", () => {
  it("hides identifiers and formats money, periods and enums", () => {
    const preview = buildDataPreview([
      {
        id: "00000000-0000-0000-0000-000000000002",
        code: "g1",
        label: "Receita sintética",
        realizado: "1234.5",
        input_digest: "a".repeat(64),
      },
    ]);
    expect(preview?.table?.columns.map((column) => column.label)).toEqual([
      "Linha",
      "Realizado",
    ]);
    expect(preview?.table?.rows[0]?.[0]).toBe("Receita sintética");
    expect(preview?.table?.rows[0]?.[1]).toMatch(/R\$\s?1\.234,50/);
    expect(JSON.stringify(preview)).not.toContain("00000000");
  });

  it("returns labelled fields for an object payload", () => {
    const preview = buildDataPreview({
      status: "Pronta",
      period: "2026-07-01",
      normalization_run_id: "00000000-0000-0000-0000-000000000003",
      reconciliation: { Conciliado: 3 },
    });
    expect(preview?.fields).toEqual([
      { label: "Situação", value: "Pronta" },
      { label: "Período", value: "Julho de 2026" },
      { label: "Conciliação", value: "Conciliado: 3" },
    ]);
  });
});
