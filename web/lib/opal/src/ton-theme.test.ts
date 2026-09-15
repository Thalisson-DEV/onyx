import primitives from "../../shared/tokens/primitives.json";
import semanticDark from "../../shared/tokens/semantic-dark.json";
import semanticLight from "../../shared/tokens/semantic-light.json";

interface ColorToken {
  value: string;
  type: string;
}

type ColorTokens = Record<string, ColorToken>;
type Rgb = [number, number, number];

const primitiveTokens: ColorTokens = primitives;
const lightTokens: ColorTokens = semanticLight.light;
const darkTokens: ColorTokens = semanticDark.dark;

function resolveColor(tokenName: string, semanticTokens: ColorTokens): string {
  const semanticToken = semanticTokens[tokenName];
  if (!semanticToken) {
    throw new Error(`Unknown semantic token: ${tokenName}`);
  }

  const reference = /^\{(.+)\}$/.exec(semanticToken.value)?.[1];
  if (!reference) return semanticToken.value;

  const primitiveToken = primitiveTokens[reference];
  if (!primitiveToken) {
    throw new Error(`Unknown primitive token: ${reference}`);
  }

  const primitiveReference = /^\{(.+)\}$/.exec(primitiveToken.value)?.[1];
  return primitiveReference
    ? resolvePrimitiveColor(primitiveReference)
    : primitiveToken.value;
}

function resolvePrimitiveColor(tokenName: string): string {
  const token = primitiveTokens[tokenName];
  if (!token) throw new Error(`Unknown primitive token: ${tokenName}`);

  const reference = /^\{(.+)\}$/.exec(token.value)?.[1];
  return reference ? resolvePrimitiveColor(reference) : token.value;
}

function parseHexColor(color: string): { rgb: Rgb; alpha: number } {
  if (!/^#[0-9a-f]{6}([0-9a-f]{2})?$/i.test(color)) {
    throw new Error(`Unsupported color: ${color}`);
  }

  return {
    rgb: [
      Number.parseInt(color.slice(1, 3), 16),
      Number.parseInt(color.slice(3, 5), 16),
      Number.parseInt(color.slice(5, 7), 16),
    ],
    alpha:
      color.length === 9 ? Number.parseInt(color.slice(7, 9), 16) / 255 : 1,
  };
}

function composite(foreground: string, background: string): Rgb {
  const foregroundColor = parseHexColor(foreground);
  const backgroundColor = parseHexColor(background);
  const blendChannel = (index: 0 | 1 | 2): number =>
    Math.round(
      foregroundColor.rgb[index] * foregroundColor.alpha +
        backgroundColor.rgb[index] * (1 - foregroundColor.alpha)
    );

  return [blendChannel(0), blendChannel(1), blendChannel(2)];
}

function relativeLuminance(rgb: Rgb): number {
  const linearChannel = (channel: number): number => {
    const normalized = channel / 255;
    return normalized <= 0.04045
      ? normalized / 12.92
      : ((normalized + 0.055) / 1.055) ** 2.4;
  };
  const red = linearChannel(rgb[0]);
  const green = linearChannel(rgb[1]);
  const blue = linearChannel(rgb[2]);
  return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
}

function contrastRatio(
  foregroundToken: string,
  backgroundToken: string,
  semanticTokens: ColorTokens
): number {
  const background = resolveColor(backgroundToken, semanticTokens);
  const foreground = composite(
    resolveColor(foregroundToken, semanticTokens),
    background
  );
  const backgroundLuminance = relativeLuminance(parseHexColor(background).rgb);
  const foregroundLuminance = relativeLuminance(foreground);

  return (
    (Math.max(backgroundLuminance, foregroundLuminance) + 0.05) /
    (Math.min(backgroundLuminance, foregroundLuminance) + 0.05)
  );
}

function expectContrast(
  foregroundToken: string,
  backgroundToken: string,
  semanticTokens: ColorTokens,
  minimum: number
): void {
  expect(
    contrastRatio(foregroundToken, backgroundToken, semanticTokens)
  ).toBeGreaterThanOrEqual(minimum);
}

describe("Vale Norte theme tokens", () => {
  test("maps brand roles without replacing status colors", () => {
    expect(lightTokens["theme-primary-05"]?.value).toBe(
      "{vale-norte-green-80}"
    );
    expect(lightTokens["theme-amber-05"]?.value).toBe("{vale-norte-gold-60}");
    expect(lightTokens["status-success-05"]?.value).toBe("{green-50}");
    expect(lightTokens["status-warning-05"]?.value).toBe("{orange-50}");
    expect(lightTokens["status-error-05"]?.value).toBe("{red-50}");
    expect(lightTokens["status-info-05"]?.value).toBe("{blue-50}");
  });

  test("keeps light theme text and interactive pairs accessible", () => {
    for (const actionToken of [
      "theme-primary-04",
      "theme-primary-05",
      "theme-primary-06",
      "action-selection-04",
      "action-selection-05",
      "action-selection-06",
    ]) {
      expectContrast("text-light-05", actionToken, lightTokens, 4.5);
    }

    expectContrast(
      "action-text-link-05",
      "background-tint-00",
      lightTokens,
      4.5
    );
    expectContrast(
      "action-text-link-05",
      "background-tint-01",
      lightTokens,
      4.5
    );
    expectContrast("theme-amber-05", "theme-amber-01", lightTokens, 4.5);
  });

  test("keeps dark theme text and interactive pairs accessible", () => {
    for (const primaryToken of [
      "theme-primary-04",
      "theme-primary-05",
      "theme-primary-06",
    ]) {
      expectContrast("text-inverted-05", primaryToken, darkTokens, 4.5);
    }

    for (const actionToken of [
      "action-selection-04",
      "action-selection-05",
      "action-selection-06",
    ]) {
      expectContrast("text-light-05", actionToken, darkTokens, 4.5);
    }

    expectContrast(
      "action-text-link-05",
      "background-tint-00",
      darkTokens,
      4.5
    );
    expectContrast(
      "action-text-link-05",
      "background-tint-01",
      darkTokens,
      4.5
    );
    expectContrast("action-selection-05", "background-tint-00", darkTokens, 3);
    expectContrast("theme-amber-05", "theme-amber-01", darkTokens, 4.5);
  });
});

// The dark theme must separate its semantic layers enough that normal content never
// reads as disabled. Each adjacent surface step, every border and the whole text
// ladder is pinned here so a later token edit cannot silently re-compress them.
describe("Vale Norte dark theme hierarchy", () => {
  // Composer/input field, card, app background, sidebar, elevated surface. Each entry
  // must be lighter than the one before it by at least MIN_SURFACE_STEP.
  const SURFACE_LADDER = [
    "background-neutral-00",
    "background-tint-00",
    "background-tint-01",
    "background-tint-02",
    "background-tint-03",
    "background-tint-04",
  ] as const;
  const MIN_SURFACE_STEP = 1.15;

  test("separates every adjacent dark surface layer", () => {
    let previous = relativeLuminance(
      parseHexColor(resolveColor(SURFACE_LADDER[0], darkTokens)).rgb
    );

    for (const token of SURFACE_LADDER.slice(1)) {
      const current = relativeLuminance(
        parseHexColor(resolveColor(token, darkTokens)).rgb
      );
      expect(current).toBeGreaterThan(previous);
      expect((current + 0.05) / (previous + 0.05)).toBeGreaterThanOrEqual(
        MIN_SURFACE_STEP
      );
      previous = current;
    }
  });

  test("keeps no dark surface at pure black", () => {
    for (const token of SURFACE_LADDER) {
      expect(resolveColor(token, darkTokens)).not.toBe("#000000");
    }
  });

  test("makes dark borders visible against the surfaces they sit on", () => {
    expectContrast("border-01", "background-tint-01", darkTokens, 1.5);
    expectContrast("border-01", "background-tint-00", darkTokens, 1.8);
    expectContrast("border-01", "background-neutral-00", darkTokens, 2);
    expectContrast("border-02", "border-01", darkTokens, 1.3);
    expectContrast("border-03", "border-02", darkTokens, 1.3);
  });

  test("keeps dark focus indicators above 3:1", () => {
    // Inputs draw a border-05 edge plus a background-tint-04 inset ring.
    expectContrast("border-05", "background-neutral-00", darkTokens, 3);
    expectContrast(
      "background-tint-04",
      "background-neutral-00",
      darkTokens,
      3
    );
    // The generic focus outline is border-04 over any surface it can land on.
    for (const surface of SURFACE_LADDER) {
      expectContrast("border-04", surface, darkTokens, 3);
    }
  });

  test("keeps the dark text ladder readable and strictly ordered", () => {
    const onBackground = (token: string): number =>
      contrastRatio(token, "background-tint-01", darkTokens);

    expect(onBackground("text-04")).toBeGreaterThanOrEqual(7);
    expect(onBackground("text-03")).toBeGreaterThanOrEqual(4.5);
    expect(onBackground("text-02")).toBeGreaterThanOrEqual(4.5);

    // Every step down the ladder must be a visible drop, so secondary text never
    // reads as primary and disabled text never reads as secondary.
    const ladder = ["text-05", "text-04", "text-03", "text-02", "text-01"];
    for (let index = 1; index < ladder.length; index++) {
      expect(onBackground(ladder[index]!)).toBeLessThan(
        onBackground(ladder[index - 1]!)
      );
    }
    expect(onBackground("text-03") / onBackground("text-01")).toBeGreaterThan(
      2
    );
    expect(onBackground("text-02") / onBackground("text-01")).toBeGreaterThan(
      2
    );
  });

  test("separates dark interactive states from their resting surface", () => {
    // Sidebar item: rest is the sidebar itself, hover lightens, selected recesses.
    expectContrast(
      "background-tint-03",
      "background-tint-02",
      darkTokens,
      1.15
    );
    expectContrast("background-tint-00", "background-tint-02", darkTokens, 1.3);
    // List row: selected is a green wash on the page, hover lightens away from it.
    expectContrast(
      "action-selection-01",
      "background-tint-01",
      darkTokens,
      1.2
    );
    expectContrast(
      "background-tint-02",
      "action-selection-01",
      darkTokens,
      1.4
    );
    // Selected foreground stays legible on the selected wash.
    expectContrast("action-selection-05", "action-selection-01", darkTokens, 3);
    // Filled action button: hover and pressed both move off the resting fill.
    expectContrast(
      "action-selection-04",
      "action-selection-05",
      darkTokens,
      1.1
    );
    expectContrast(
      "action-selection-05",
      "action-selection-06",
      darkTokens,
      1.4
    );
    // Disabled surfaces stay distinct from the field they replace.
    expectContrast(
      "background-neutral-03",
      "background-neutral-00",
      darkTokens,
      1.5
    );
  });
});

// The light theme is approved. Any change to these values is a regression, so the
// exact primitive references are pinned rather than a contrast range.
describe("Vale Norte light theme lock", () => {
  test("keeps approved light surface, border and text references", () => {
    const expected: Record<string, string> = {
      "text-05": "{alpha-grey-100-90}",
      "text-04": "{alpha-grey-100-75}",
      "text-03": "{alpha-grey-100-55}",
      "text-02": "{alpha-grey-100-45}",
      "text-01": "{alpha-grey-100-20}",
      "background-neutral-00": "{grey-00}",
      "background-neutral-01": "{grey-02}",
      "background-neutral-02": "{grey-06}",
      "background-neutral-03": "{grey-10}",
      "background-neutral-04": "{grey-20}",
      "background-tint-00": "{grey-00}",
      "background-tint-01": "{tint-02}",
      "background-tint-02": "{tint-05}",
      "background-tint-03": "{tint-10}",
      "background-tint-04": "{tint-20}",
      "border-01": "{grey-10}",
      "border-02": "{grey-20}",
      "border-03": "{grey-40}",
      "border-04": "{grey-50}",
      "border-05": "{grey-100}",
      "action-selection-01": "{vale-norte-green-05}",
      "action-selection-04": "{vale-norte-green-60}",
      "action-selection-05": "{vale-norte-green-80}",
      "action-selection-06": "{vale-norte-green-85}",
      "background-code-01": "{grey-02}",
      "code-comment": "{alpha-grey-100-35}",
    };

    for (const [token, value] of Object.entries(expected)) {
      expect(lightTokens[token]?.value).toBe(value);
    }
  });
});
