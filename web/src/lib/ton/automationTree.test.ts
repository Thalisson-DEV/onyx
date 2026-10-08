import type { Definition, FlowNode } from "@/lib/ton/automations";
import { blankDefinition, insertNode, locate, moveNode, visibleFor } from "@/lib/ton/automationTree";
import { buildLayout } from "@/views/ton/AutomationsPage/designer/layout";

function step(id: string, extra: Partial<FlowNode> = {}): FlowNode {
  return { id, type: "data.compose", label: id, params: {}, ...extra };
}

function sample(): Definition {
  return {
    ...blankDefinition(),
    steps: [
      step("buscar"),
      step("cond", { type: "control.condition", then: [step("sim")], else: [step("nao")] }),
      step("cada", { type: "control.foreach", steps: [step("dentro")] }),
      step("fim"),
    ],
  };
}

describe("automation tree", () => {
  it("moves a node into a branch and keeps order", () => {
    const moved = moveNode(sample(), "buscar", { parentId: "cond", slot: "then", index: 1 });
    expect(moved.steps.map((node) => node.id)).toEqual(["cond", "cada", "fim"]);
    expect(locate(moved, "buscar")).toMatchObject({ ref: { parentId: "cond", slot: "then" }, index: 1 });
  });

  it("ignores a move into the node's own subtree", () => {
    const definition = sample();
    expect(moveNode(definition, "cada", { parentId: "cada", slot: "steps", index: 0 })).toBe(definition);
  });

  it("moves down in the same list", () => {
    const moved = moveNode(sample(), "buscar", { parentId: null, slot: "steps", index: 3 });
    expect(moved.steps.map((node) => node.id)).toEqual(["cond", "cada", "buscar", "fim"]);
  });

  it("sees earlier steps, branch steps, but not loop internals or the other branch", () => {
    const definition = sample();
    expect(visibleFor(definition, "fim").steps).toEqual(["buscar", "cond", "sim", "nao", "cada"]);
    expect(visibleFor(definition, "nao").steps).toEqual(["buscar"]);
    expect(visibleFor(definition, "dentro")).toEqual({ steps: ["buscar", "cond", "sim", "nao"], loops: ["cada"] });
  });

  it("lays out every node with insert targets", () => {
    const definition = insertNode(sample(), { parentId: "cond", slot: "else", index: 0 }, step("extra"));
    const layout = buildLayout(definition, new Set(), { yes: "Sim", no: "Não", otherwise: "Padrão" });
    const ids = layout.nodes.map((node) => node.id);
    for (const id of ["trigger", "buscar", "cond", "sim", "nao", "extra", "cada", "dentro", "fim", "end"]) {
      expect(ids).toContain(id);
    }
    const sim = layout.nodes.find((node) => node.id === "sim")!;
    const nao = layout.nodes.find((node) => node.id === "nao")!;
    expect(sim.position.x).toBeLessThan(nao.position.x);
    expect(layout.targets.length).toBeGreaterThan(8);
  });
});
