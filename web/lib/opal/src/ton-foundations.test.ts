/**
 * TON-VIS-001 — static invariants for the visual foundation.
 *
 * `ton-theme.test.ts` measures colour. This file guards the parts of the
 * foundation that live in CSS and in the Tailwind preset, where a contrast
 * calculation cannot help: the tokenized border width, the motion layer, the
 * reduced-motion floor, the single global border declaration, the radius scale,
 * and the promise that numeric Tailwind spacing was not remapped.
 *
 * These are deliberately coarse. They assert the presence of a mechanism, not
 * the exact characters of a rule.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";

import size from "../../shared/tokens/size.json";
import motion from "../../shared/tokens/motion.json";
import shadow from "../../shared/tokens/shadow.json";
import preset from "../tailwind-preset.cjs";

const repoWeb = join(__dirname, "..", "..", "..");

// Comments are stripped before asserting: these files explain what they replaced,
// and a rule-level invariant must not be satisfied or broken by prose.
const stripComments = (source: string): string =>
  source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const read = (relativePath: string): string =>
  stripComments(readFileSync(join(repoWeb, relativePath), "utf8"));

const globalsCss = read("src/app/globals.css");
const statefulCss = read("lib/opal/src/core/interactive/stateful/styles.css");
const appTailwindConfig = read("tailwind-themes/tailwind.config.js");
const simpleLoader = read("lib/opal/src/icons/simple-loader.tsx");

type DimensionTokens = Record<string, { value: string; type: string }>;
const sizeTokens: DimensionTokens = size;
const motionTokens: DimensionTokens = motion;

interface PresetTheme {
  extend: {
    colors: Record<string, string>;
    borderRadius: Record<string, string>;
    borderWidth: Record<string, string>;
    outlineWidth: Record<string, string>;
    transitionDuration: Record<string, string>;
    transitionTimingFunction: Record<string, string>;
    backdropBlur: Record<string, string>;
  };
}
const theme = (preset as { theme: PresetTheme }).theme;

describe("TON border-width foundation", () => {
  test("defines both structural line weights as tokens", () => {
    expect(sizeTokens["weight-line-border"]?.value).toBe("1");
    expect(sizeTokens["weight-line-focus"]?.value).toBe("2");
  });

  test("wires the line weights into border and outline utilities", () => {
    expect(theme.extend.borderWidth.line).toContain("--weight-line-border");
    expect(theme.extend.borderWidth.focus).toContain("--weight-line-focus");
    expect(theme.extend.outlineWidth.focus).toContain("--weight-line-focus");
  });

  test("keeps Tailwind's own border widths untouched", () => {
    // `border` (1px) and `border-2` (2px) must keep meaning exactly what they
    // meant before; the tokenized widths are additive names.
    expect(theme.extend.borderWidth).not.toHaveProperty("DEFAULT");
    expect(theme.extend.borderWidth).not.toHaveProperty("2");
  });

  test("draws the selection ring and the focus edge from the weight tokens", () => {
    expect(statefulCss).toContain("var(--weight-line-border)");
    expect(statefulCss).toContain("var(--weight-line-focus)");
    expect(globalsCss).toContain("var(--weight-line-focus)");
  });
});

describe("TON global border declaration", () => {
  test("declares the default border colour exactly once", () => {
    const declarations = globalsCss.match(/^\s*border-color:/gm) ?? [];
    expect(declarations).toHaveLength(1);
  });

  test("makes that declaration theme-aware and cover pseudo-elements", () => {
    expect(globalsCss).toMatch(
      /::after,\s*::before,\s*::backdrop,\s*::file-selector-button\s*\{\s*border-color:\s*var\(--border-01\);/
    );
  });

  test("leaves no theme-blind grey behind", () => {
    expect(globalsCss).not.toContain("--color-gray-200");
    expect(globalsCss).not.toContain("#e5e7eb");
    expect(globalsCss).not.toContain("@apply border-border");
  });
});

describe("TON motion foundation", () => {
  test("publishes a duration and easing vocabulary", () => {
    for (const token of [
      "duration-instant",
      "duration-fast",
      "duration-base",
      "duration-slow",
    ]) {
      expect(motionTokens[token]?.value).toMatch(/^\d+ms$/);
    }
    for (const token of ["easing-standard", "easing-out", "easing-in"]) {
      expect(motionTokens[token]?.value).toMatch(/^cubic-bezier\(/);
    }
  });

  test("keeps every duration inside the measured TON band", () => {
    const durations = ["instant", "fast", "base", "slow"].map((name) =>
      Number.parseInt(motionTokens[`duration-${name}`]!.value, 10)
    );
    for (const duration of durations) {
      expect(duration).toBeGreaterThanOrEqual(120);
      expect(duration).toBeLessThanOrEqual(280);
    }
    // Strictly ascending, so "slow" always means slower than "base".
    expect([...durations].sort((a, b) => a - b)).toEqual(durations);
  });

  test("exposes the motion tokens as utilities", () => {
    expect(theme.extend.transitionDuration.base).toBe("var(--duration-base)");
    expect(theme.extend.transitionTimingFunction.standard).toBe(
      "var(--easing-standard)"
    );
  });
});

describe("TON reduced-motion foundation", () => {
  test("collapses decorative motion globally", () => {
    expect(globalsCss).toMatch(
      /@media \(prefers-reduced-motion: reduce\) \{\s*\*,\s*\*::before,\s*\*::after \{/
    );
    expect(globalsCss).toContain("animation-iteration-count: 1 !important");
  });

  test("keeps an escape hatch for operational progress feedback", () => {
    expect(globalsCss).toContain('[data-motion="essential"]');
    expect(globalsCss).toContain("--motion-essential-duration");
  });

  test("gates the most-used spinner on motion-safe", () => {
    expect(simpleLoader).toContain("motion-safe:animate-spin");
    expect(simpleLoader).not.toMatch(/[^:]animate-spin/);
  });
});

describe("TON radius foundation", () => {
  const RADIUS_SCALE: Record<string, string> = {
    "radius-02": "0.125rem",
    "radius-04": "0.25rem",
    "radius-08": "0.5rem",
    "radius-12": "0.75rem",
    "radius-16": "1rem",
    "radius-20": "1.25rem",
    "radius-round": "62.5rem",
  };

  test("keeps the approved radius scale", () => {
    for (const [token, value] of Object.entries(RADIUS_SCALE)) {
      expect(sizeTokens[token]?.value).toBe(value);
    }
  });

  test("re-points Tailwind's radius aliases at the scale without moving geometry", () => {
    // Each alias must resolve to the exact Tailwind v4 default it replaces, so
    // `rounded-sm`/`-lg`/`-xl`/`-2xl` become tokenized without any visual change.
    const aliasToTailwindDefault: Record<string, string> = {
      xs: "0.125rem",
      sm: "0.25rem",
      lg: "0.5rem",
      xl: "0.75rem",
      "2xl": "1rem",
    };
    for (const [alias, tailwindDefault] of Object.entries(
      aliasToTailwindDefault
    )) {
      const mapped = theme.extend.borderRadius[alias];
      expect(mapped).toBeDefined();
      const tokenName = /^var\(--(radius-[\w-]+)\)$/.exec(mapped!)?.[1];
      expect(tokenName).toBeDefined();
      expect(sizeTokens[tokenName!]?.value).toBe(tailwindDefault);
    }
  });
});

describe("TON elevation and blur foundation", () => {
  test("reserves shadow for real elevation", () => {
    // Three levels stay. elevation-0 is the absence of these tokens.
    expect(Object.keys(shadow)).toEqual([
      "shadow-box-00",
      "shadow-box-01",
      "shadow-box-02",
    ]);
    // The old geometry blurred 12px and 24px with a 1px spread, which read as a
    // halo once the dark shadow colour was white. Blur is now bounded and every
    // layer is offset downwards, so it reads as elevation.
    const blurs = Object.values(shadow as Record<string, { value: string }>)
      .flatMap((token) => token.value.match(/(\d+)px/g) ?? [])
      .map((px) => Number.parseInt(px, 10));
    for (const blur of blurs) {
      expect(blur).toBeLessThanOrEqual(16);
    }
  });

  test("makes the backdrop-blur scale monotonic", () => {
    const steps = ["01", "02", "03"].map((step) =>
      Number.parseInt(sizeTokens[`backdrop-blur-${step}`]!.value, 10)
    );
    expect(steps).toEqual([...steps].sort((a, b) => a - b));
    expect(new Set(steps).size).toBe(steps.length);
    expect(theme.extend.backdropBlur["03"]).toBe("var(--backdrop-blur-03)");
  });
});

describe("TON surface and border role aliases", () => {
  test("names every surface role over the numeric tokens", () => {
    expect(theme.extend.colors["surface-canvas"]).toBe(
      "var(--background-tint-01)"
    );
    expect(theme.extend.colors["surface"]).toBe("var(--background-tint-02)");
    expect(theme.extend.colors["surface-raised"]).toBe(
      "var(--background-tint-00)"
    );
    expect(theme.extend.colors["surface-hover"]).toBe(
      "var(--background-tint-03)"
    );
    expect(theme.extend.colors["surface-field"]).toBe(
      "var(--background-neutral-00)"
    );
  });

  test("names every border role", () => {
    for (const role of [
      "border-subtle",
      "border-default",
      "border-interactive",
      "border-selected",
      "border-focus",
      "border-error",
      "border-attention",
    ]) {
      expect(theme.extend.colors[role]).toMatch(/^var\(--[\w-]+\)$/);
    }
    expect(theme.extend.colors["border-selected"]).toBe(
      "var(--theme-primary-04)"
    );
  });

  test("drops the upstream Onyx colour classes from the preset", () => {
    for (const name of Object.keys(theme.extend.colors)) {
      expect(name).not.toMatch(/^onyx-(ink|chrome)-/);
    }
  });
});

describe("TON spacing safety", () => {
  test("never remaps numeric Tailwind spacing utilities", () => {
    // The spacing tokens are px-denominated (`spacing-block-16` = 1rem) while
    // Tailwind's utilities are step-denominated (`p-4` = 1rem). Wiring the token
    // keys into `theme.spacing` would divide every p-/m-/gap-/space- value by
    // four. VIS-001 therefore leaves spacing alone; see
    // plans/ton/frontend/001-visual-foundations.md.
    expect(theme.extend).not.toHaveProperty("spacing");
    expect(theme.extend).not.toHaveProperty("padding");
    expect(theme.extend).not.toHaveProperty("margin");
    expect(theme.extend).not.toHaveProperty("gap");
    expect(sizeTokens["spacing-block-16"]?.value).toBe("1rem");
  });
});

describe("TON reading width", () => {
  test("binds one semantic reading width to the existing layout variable", () => {
    expect(appTailwindConfig).toMatch(
      /reading: "var\(--app-page-main-content-width\)"/
    );
  });
});

describe("TON interaction state foundation", () => {
  test("never lets a selected surface fall back to the unselected hover surface", () => {
    // The audited defect: every `selected:hover` cell reused background-tint-03
    // (sidebar) or background-tint-02 (wash), the exact surfaces unselected rows
    // hover to, so selection vanished under the cursor.
    const selectedHoverCells = statefulCss.match(
      /\[data-interactive-state="selected"\](?::hover|\[data-interaction="hover"\])[^{]*\{[^}]*\}/g
    );
    expect(selectedHoverCells?.length).toBeGreaterThan(0);
    for (const cell of selectedHoverCells!) {
      expect(cell).not.toContain("bg-background-tint-03");
      expect(cell).not.toContain("bg-background-tint-02;");
    }
  });

  test("gives the sidebar variants a pressed cell", () => {
    for (const variant of ["sidebar-heavy", "sidebar-light"]) {
      const pattern = new RegExp(
        `\\[data-interactive-variant="${variant}"\\][^{]*:active`
      );
      expect(statefulCss).toMatch(pattern);
    }
  });

  test("expresses selection with a ring, not colour alone", () => {
    expect(statefulCss).toContain("var(--theme-primary-04)");
    const rings = statefulCss.match(/box-shadow: inset 0 0 0 calc\([^;]+;/g);
    expect(rings?.length).toBeGreaterThanOrEqual(3);
  });
});

describe("TON changed-scope hygiene", () => {
  const changedFiles = {
    "src/app/globals.css": globalsCss,
    "lib/opal/src/core/interactive/stateful/styles.css": statefulCss,
    "tailwind-themes/tailwind.config.js": appTailwindConfig,
    "lib/opal/src/icons/simple-loader.tsx": simpleLoader,
  };

  test("uses no dark: modifier", () => {
    for (const [name, contents] of Object.entries(changedFiles)) {
      expect(`${name}: ${/(^|[\s"'`:])dark:/m.test(contents)}`).toBe(
        `${name}: false`
      );
    }
  });

  test("introduces no raw Tailwind palette colour", () => {
    const palette =
      /(bg|text|border|ring|stroke|fill|from|to|via)-(slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-(50|100|200|300|400|500|600|700|800|900|950)\b/;
    for (const [name, contents] of Object.entries(changedFiles)) {
      expect(`${name}: ${palette.test(contents)}`).toBe(`${name}: false`);
    }
  });

  test("leaves no raw hex colour in the token-owned CSS", () => {
    // `mask-image: linear-gradient(#fff, #fff)` is an opaque-mask idiom, not a
    // colour choice, so mask declarations are excluded.
    for (const name of [
      "src/app/globals.css",
      "lib/opal/src/core/interactive/stateful/styles.css",
    ] as const) {
      const withoutMasks = changedFiles[name]
        .split("\n")
        .filter((line) => !line.includes("mask-image"))
        .join("\n");
      expect(`${name}: ${/#[0-9a-f]{3,8}\b/i.test(withoutMasks)}`).toBe(
        `${name}: false`
      );
    }
  });
});
