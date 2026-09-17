/**
 * TON-VIS-007 Specialist and runtime identity test suite.
 *
 * Tests the 28 required assertions:
 * 1. uploaded image fallback
 * 2. configured icon fallback
 * 3. Latin initial
 * 4. digit fallback
 * 5. emoji fallback
 * 6. CJK fallback
 * 7. empty fallback
 * 8. deterministic fallback
 * 9. idle state
 * 10. running state
 * 11. attention state
 * 12. selected state
 * 13. no state causes layout shift
 * 14. selected state has non-color semantic evidence
 * 15. AgentCard no radial gradient
 * 16. AgentCard no decorative hover shadow
 * 17. card height content-driven
 * 18. no "Onyx" owner fallback
 * 19. translated new-specialist accessible label
 * 20. pinned specialist preserves behavior
 * 21. agent creation preserved
 * 22. start-chat preserved
 * 23. starter message submission preserved
 * 24. editor identity selector preserved
 * 25. no concrete TON personas created
 * 26. no fake runtime state rendered in production
 * 27. CJK/emoji fallback accessible
 * 28. light/dark semantic parity
 */
import fs from "node:fs";
import path from "node:path";
import React from "react";
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";

import SpecialistAvatar from "@/refresh-components/avatars/SpecialistAvatar";
import CustomAgentAvatar from "@/refresh-components/avatars/CustomAgentAvatar";
import AgentAvatar from "@/refresh-components/avatars/AgentAvatar";
import englishMessages from "@/i18n/messages/en.json";
import portugueseMessages from "@/i18n/messages/pt.json";

const WEB_ROOT = path.resolve(__dirname, "../..");

function readSource(relativePath: string): string {
  return fs.readFileSync(path.join(WEB_ROOT, relativePath), "utf8");
}

const stripComments = (source: string): string =>
  source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

function renderWithIntl(ui: React.ReactElement, messages = englishMessages) {
  return render(
    <NextIntlClientProvider locale="en" messages={messages}>
      {ui}
    </NextIntlClientProvider>
  );
}

describe("TON-VIS-007: Fallback Chain", () => {
  // 1. uploaded image fallback
  test("1. uploaded image fallback renders image element with circular container", () => {
    const { container } = renderWithIntl(
      <CustomAgentAvatar src="/test-avatar.png" name="Finance Bot" size={32} />
    );
    const img = container.querySelector("img");
    expect(img).not.toBeNull();
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toContain("rounded-full");
  });

  // 2. configured icon fallback
  test("2. configured icon fallback renders the mapped icon inside SpecialistAvatar", () => {
    const { container } = renderWithIntl(
      <CustomAgentAvatar iconName="Search" size={32} />
    );
    const svg = container.querySelector("svg");
    expect(svg).not.toBeNull();
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toContain("rounded-lg");
    expect(wrapper.className).not.toContain("octagon");
  });

  // 3. Latin initial
  test("3. Latin initial renders uppercase first letter", () => {
    renderWithIntl(<CustomAgentAvatar name="alice" size={32} />);
    expect(screen.getByText("A")).toBeDefined();
  });

  // 4. digit fallback
  test("4. digit fallback renders digit initial without generic fallback", () => {
    renderWithIntl(<CustomAgentAvatar name="360 Audit" size={32} />);
    expect(screen.getByText("3")).toBeDefined();
  });

  // 5. emoji fallback
  test("5. emoji fallback renders emoji initial without generic fallback", () => {
    renderWithIntl(<CustomAgentAvatar name="⚡ Fast Engine" size={32} />);
    expect(screen.getByText("⚡")).toBeDefined();
  });

  // 6. CJK fallback
  test("6. CJK fallback renders first CJK character without generic fallback", () => {
    renderWithIntl(<CustomAgentAvatar name="会計 Audit" size={32} />);
    expect(screen.getByText("会")).toBeDefined();
  });

  // 7. empty fallback
  test("7. empty fallback renders generic SvgTwoLineSmall icon", () => {
    const { container } = renderWithIntl(
      <CustomAgentAvatar name="" size={32} />
    );
    const svg = container.querySelector("svg");
    expect(svg).not.toBeNull();
  });

  // 8. deterministic fallback
  test("8. fallback is deterministic across multiple renders", () => {
    const { container: first } = renderWithIntl(
      <CustomAgentAvatar name="Deterministic" size={32} />
    );
    const { container: second } = renderWithIntl(
      <CustomAgentAvatar name="Deterministic" size={32} />
    );
    expect(first.innerHTML).toEqual(second.innerHTML);
  });
});

describe("TON-VIS-007: Runtime States", () => {
  // 9. idle state
  test("9. idle state is neutral with no animation or pulse", () => {
    const { container } = renderWithIntl(
      <SpecialistAvatar state="idle" size={32} initial="T" />
    );
    const el = container.firstChild as HTMLElement;
    expect(el.className).not.toContain("animate-pulse");
    expect(el.getAttribute("aria-selected")).toBeNull();
    expect(el.getAttribute("data-attention")).toBeNull();
  });

  // 10. running state
  test("10. running state displays contained indicator without rotating container", () => {
    const { container } = renderWithIntl(
      <SpecialistAvatar state="running" size={32} initial="T" />
    );
    const el = container.firstChild as HTMLElement;
    expect(el.getAttribute("data-running")).toBe("true");
    const indicator = el.querySelector('[data-testid="running-indicator"]');
    expect(indicator).not.toBeNull();
    // Avatar container itself is not rotating
    expect(el.className).not.toContain("animate-spin");
  });

  // 11. attention state
  test("11. attention state uses semantic border-border-attention", () => {
    const { container } = renderWithIntl(
      <SpecialistAvatar state="attention" size={32} initial="T" />
    );
    const el = container.firstChild as HTMLElement;
    expect(el.className).toContain("border-border-attention");
    expect(el.getAttribute("data-attention")).toBe("true");
  });

  // 12. selected state
  test("12. selected state uses semantic border-border-selected", () => {
    const { container } = renderWithIntl(
      <SpecialistAvatar state="selected" size={32} initial="T" />
    );
    const el = container.firstChild as HTMLElement;
    expect(el.className).toContain("border-border-selected");
  });

  // 13. no state causes layout shift
  test("13. no state causes layout shift (width and height remain invariant)", () => {
    const states = ["idle", "running", "attention", "selected"] as const;
    const sizes = states.map((state) => {
      const { container } = renderWithIntl(
        <SpecialistAvatar state={state} size={40} initial="X" />
      );
      const el = container.firstChild as HTMLElement;
      return {
        width: el.style.width,
        height: el.style.height,
      };
    });
    for (const s of sizes) {
      expect(s).toEqual({ width: "40px", height: "40px" });
    }
  });

  // 14. selected state has non-color semantic evidence
  test("14. selected state has non-color semantic evidence via aria-selected", () => {
    const { container } = renderWithIntl(
      <SpecialistAvatar state="selected" size={32} initial="S" />
    );
    const el = container.firstChild as HTMLElement;
    expect(el.getAttribute("aria-selected")).toBe("true");
  });
});

describe("TON-VIS-007: AgentCard Visual Contract", () => {
  const cardSource = stripComments(
    readSource("src/sections/agents/AgentCard.tsx")
  );

  // 15. AgentCard no radial gradient
  test("15. AgentCard source has zero radial-00 usage", () => {
    expect(cardSource).not.toContain("radial-00");
  });

  // 16. AgentCard no decorative hover shadow
  test("16. AgentCard source has zero hover:shadow-box-00 usage", () => {
    expect(cardSource).not.toContain("hover:shadow-box-00");
  });

  // 17. card height content-driven
  test("17. card header height is content-driven (no fixed h-24 constraint)", () => {
    expect(cardSource).not.toContain("flex self-stretch h-24");
    expect(cardSource).toContain("flex self-stretch");
  });

  // 18. no "Onyx" owner fallback
  test("18. no 'Onyx' fallback string exists in AgentCard or AgentViewerModal", () => {
    expect(cardSource).not.toContain('"Onyx"');
    expect(cardSource).not.toContain("'Onyx'");
    const viewerSource = stripComments(
      readSource("src/lib/agents/components/AgentViewerModal.tsx")
    );
    expect(viewerSource).not.toContain('"Onyx"');
    expect(viewerSource).not.toContain("'Onyx'");
  });
});

describe("TON-VIS-007: Specialist Product Surfaces", () => {
  // 19. translated new-specialist accessible label
  test("19. new-specialist accessible label is translated, not test identifier", () => {
    const pageSource = readSource("src/views/AgentsNavigationPage.tsx");
    expect(pageSource).not.toContain(
      'NEW_AGENT_BUTTON_ARIA_LABEL = "AgentsPage/new-agent-button"'
    );
    expect(pageSource).toContain(
      'aria-label={t("navigation.newAgent.ariaLabel")}'
    );
    expect(portugueseMessages.agents.navigation.newAgent.ariaLabel).toBe(
      "Novo especialista"
    );
    expect(englishMessages.agents.navigation.newAgent.ariaLabel).toBe(
      "New specialist"
    );
  });

  // 20. pinned specialist preserves behavior
  test("20. pinned specialist in sidebar preserves usePinnedAgents and togglePinnedAgent", () => {
    const buttonSource = readSource(
      "src/lib/agents/components/AgentButton.tsx"
    );
    expect(buttonSource).toContain("usePinnedAgents");
    expect(buttonSource).toContain("togglePinnedAgent");
    expect(buttonSource).toContain("isActuallyPinned");
  });

  // 21. agent creation preserved
  test("21. agent creation routing and permission gating preserved", () => {
    const pageSource = readSource("src/views/AgentsNavigationPage.tsx");
    expect(pageSource).toContain("canCreateAgent");
    expect(pageSource).toContain("/app/agents/create");
  });

  // 22. start-chat preserved
  test("22. start-chat action preserved in AgentCard", () => {
    const cardSource = readSource("src/sections/agents/AgentCard.tsx");
    expect(cardSource).toContain("handleStartChat");
    expect(cardSource).toContain("appPosition.openAgent");
  });

  // 23. starter message submission preserved
  test("23. starter message submission preserved in Suggestions and AgentViewerModal", () => {
    const suggestionsSource = readSource("src/sections/Suggestions.tsx");
    expect(suggestionsSource).toContain("onSubmit");
    expect(suggestionsSource).toContain("handleSuggestionClick");
    const viewerSource = readSource(
      "src/lib/agents/components/AgentViewerModal.tsx"
    );
    expect(viewerSource).toContain("handleStartChat(starter.message)");
  });

  // 24. editor identity selector preserved
  test("24. editor identity selector preserved with CustomAgentAvatar", () => {
    const editorSource = readSource("src/views/AgentEditorPage.tsx");
    expect(editorSource).toContain("<CustomAgentAvatar");
    expect(editorSource).toContain("handleIconClick");
    expect(editorSource).toContain("handleImageUpload");
  });

  // 25. no concrete TON personas created
  test("25. no concrete TON personas (CFO, Frota, Auditor, etc.) fabricated in code", () => {
    const agentFiles = [
      "src/refresh-components/avatars/SpecialistAvatar.tsx",
      "src/refresh-components/avatars/CustomAgentAvatar.tsx",
      "src/refresh-components/avatars/AgentAvatar.tsx",
      "src/sections/agents/AgentCard.tsx",
      "src/views/AgentsNavigationPage.tsx",
    ];
    for (const rel of agentFiles) {
      const src = readSource(rel);
      expect(src).not.toMatch(/\b(CFO|Frota|Contratos|Auditor|RH|CEO)\b/);
    }
  });

  // 26. no fake runtime state rendered in production
  test("26. no fake running or attention state rendered in production pages", () => {
    const navPage = readSource("src/views/AgentsNavigationPage.tsx");
    expect(navPage).not.toContain('state="running"');
    expect(navPage).not.toContain('state="attention"');
    const cardSrc = readSource("src/sections/agents/AgentCard.tsx");
    expect(cardSrc).not.toContain('state="running"');
    expect(cardSrc).not.toContain('state="attention"');
  });

  // 27. CJK/emoji fallback accessible
  test("27. CJK and emoji fallbacks render safely with aria-hidden on decorative glyph", () => {
    const { container: emojiContainer } = renderWithIntl(
      <CustomAgentAvatar name="🚀 Rocket" size={32} />
    );
    const emojiSpan = emojiContainer.querySelector("span");
    expect(emojiSpan?.getAttribute("aria-hidden")).toBe("true");

    const { container: cjkContainer } = renderWithIntl(
      <CustomAgentAvatar name="分析 Specialist" size={32} />
    );
    const cjkSpan = cjkContainer.querySelector("span");
    expect(cjkSpan?.getAttribute("aria-hidden")).toBe("true");
  });

  // 28. light/dark semantic parity
  test("28. specialist identity uses semantic tokens without dark: overrides", () => {
    const specialistSrc = readSource(
      "src/refresh-components/avatars/SpecialistAvatar.tsx"
    );
    expect(specialistSrc).not.toContain("dark:");
    expect(specialistSrc).toContain("bg-background-tint-00");
    expect(specialistSrc).toContain("border-border-default");
    expect(specialistSrc).toContain("border-border-selected");
    expect(specialistSrc).toContain("border-border-attention");
  });
});
