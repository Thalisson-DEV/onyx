import { splitNextSteps } from "@/lib/ton/nextSteps";

describe("splitNextSteps", () => {
  it("turns the closing list into steps and drops it from the text", () => {
    const { body, steps } = splitNextSteps(
      "A receita caiu 2%.\n\n**Próximos passos:**\n- Compare com agosto.\n- **Monte um painel** por unidade\n"
    );
    expect(body).toBe("A receita caiu 2%.");
    expect(steps).toEqual([
      "Compare com agosto",
      "Monte um painel por unidade",
    ]);
  });

  it("hides a heading whose list has not streamed yet", () => {
    expect(splitNextSteps("Texto.\n\nPróximos passos:")).toEqual({
      body: "Texto.",
      steps: [],
    });
  });

  it("keeps the answer when prose follows the heading", () => {
    const text = "Próximos passos:\nRevise a nota 19741 antes de pagar.";
    expect(splitNextSteps(text)).toEqual({ body: text, steps: [] });
  });

  it("leaves answers without the heading alone", () => {
    expect(splitNextSteps("Só isso.")).toEqual({ body: "Só isso.", steps: [] });
  });
});
