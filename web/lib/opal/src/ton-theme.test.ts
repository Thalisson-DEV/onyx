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
