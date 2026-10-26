import {
  artifactTables,
  artifactVersion,
  formatArtifactValue,
  isNumericCell,
  isTonArtifact,
  markCreate,
  splitCreateMark,
  toCsv,
  type TonArtifact,
} from "@/lib/ton/artifacts";

const BASE: TonArtifact = {
  kind: "ton_artifact",
  artifact_id: "abc123def456",
  artifact_kind: "painel",
  title: "Receita por unidade",
  subtitle: null,
  blocks: [
    {
      type: "barras",
      title: "Receita",
      format: "brl",
      items: [
        {
          label: "Toledo-PR",
          value: 3412880.1,
          display: "R$ 3,41 mi",
          note: null,
          tone: "neutral",
        },
      ],
    },
  ],
  slides: [],
  sources: [],
  created_at: "2026-10-25T15:00:00Z",
};

describe("artifacts", () => {
  it("recognizes the tool payload and nothing else", () => {
    expect(isTonArtifact(BASE)).toBe(true);
    expect(isTonArtifact({ ...BASE, artifact_kind: "planilha" })).toBe(false);
    expect(isTonArtifact({ kind: "agent_action" })).toBe(false);
  });

  it("counts versions by creation time", () => {
    const later = { ...BASE, created_at: "2026-10-25T16:00:00Z" };
    const versions = { [BASE.artifact_id]: [BASE, later] };
    expect(artifactVersion(versions, later)).toBe(2);
  });

  it("formats money short for charts", () => {
    expect(formatArtifactValue(10758398.69, "brl")).toBe("R$ 10,76 mi");
    expect(formatArtifactValue(412000, "brl")).toBe("R$ 412 mil");
    expect(formatArtifactValue(10.4, "percent")).toBe("10,4%");
    expect(formatArtifactValue(-25_000_000, "brl")).toBe("−R$ 25 mi");
  });

  it("aligns Brazilian numbers as numbers", () => {
    expect(isNumericCell("1.540.673,07")).toBe(true);
    expect(isNumericCell("(225.076,44)")).toBe(true);
    expect(isNumericCell("R$ -4.894.841,46")).toBe(true);
    expect(isNumericCell("Toledo-PR")).toBe(false);
  });

  it("writes CSV Excel opens in pt-BR", () => {
    expect(toCsv(["Unidade", "Receita"], [["A; B", 1.5]])).toBe(
      '﻿Unidade;Receita\r\n"A; B";1,50'
    );
    expect(toCsv(["Linha", "Valor"], [["Resultado", "−R$ 1.234,56"]])).toBe(
      "﻿Linha;Valor\r\nResultado;-1234,56"
    );
  });

  it("carries the Criar choice as a mark the chat reads back", () => {
    const message = markCreate("painel", "quero ver os custos");
    expect(splitCreateMark(message)).toEqual({
      kind: "painel",
      text: "quero ver os custos",
    });
    expect(splitCreateMark("[[ton:planilha]] x")).toEqual({
      kind: null,
      text: "[[ton:planilha]] x",
    });
    expect(splitCreateMark("quanto gastamos?").kind).toBeNull();
  });

  it("turns chart blocks into tables for the data tab", () => {
    const [table] = artifactTables(BASE);
    expect(table?.rows).toEqual([["Toledo-PR", "R$ 3.412.880,10", ""]]);
  });
});
