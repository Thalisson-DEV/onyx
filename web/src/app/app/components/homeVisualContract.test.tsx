/**
 * TON-VIS-003 home and new-conversation contract.
 *
 * AppPage cannot be rendered in isolation because it owns the session, query,
 * project, voice, and upload integrations. These checks protect the layout and
 * identity invariants that can silently regress without replacing those systems.
 */
import fs from "node:fs";
import path from "node:path";

import pt from "@/i18n/messages/pt.json";

const WEB_ROOT = path.resolve(__dirname, "../../../..");

function read(relativePath: string): string {
  return fs
    .readFileSync(path.join(WEB_ROOT, relativePath), "utf8")
    .replace(/\r\n/g, "\n");
}

function stripComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
}

const WELCOME = "src/app/app/components/WelcomeMessage.tsx";
const SUGGESTIONS = "src/sections/Suggestions.tsx";
const APP_PAGE = "src/views/AppPage.tsx";
const APP_INPUT_BAR = "src/sections/input/AppInputBar.tsx";
const ONBOARDING = "src/sections/onboarding/OnboardingFlow.tsx";
const NRF_PAGE = "src/app/nrf/NRFPage.tsx";

describe("deterministic TON home", () => {
  test("uses the approved PT-BR heading and support copy", () => {
    expect(pt.chat.welcome.home).toEqual({
      description:
        "Envie arquivos ou descreva a situação que deseja investigar.",
      inputPlaceholder: "Descreva o que deseja investigar...",
      title: "O que precisa ser analisado?",
    });

    const welcome = stripComments(read(WELCOME));
    expect(welcome).toContain('t("home.title")');
    expect(welcome).toContain('t("home.description")');
    expect(welcome).toContain('as="h1"');
  });

  test("has no random or time-based render path", () => {
    const welcome = stripComments(read(WELCOME));

    expect(welcome).not.toContain("Math.random");
    expect(welcome).not.toContain("useEffect");
    expect(welcome).not.toMatch(/Date\.|new Date|custom_greeting_message/);
  });

  test("removes the nested decorative hero surface", () => {
    const welcome = stripComments(read(WELCOME));

    expect(welcome).not.toContain("<Logo");
    expect(welcome).not.toContain("FrostedDiv");
    expect(welcome).not.toMatch(/shadow-|gradient|backdrop-blur/);
    expect(welcome).toContain('data-testid="central-home-intro"');
    expect(welcome).toContain('alignItems="start"');
    expect(welcome).not.toContain('data-testid="onyx-logo"');
  });

  test("keeps custom-agent identity separate from the default copy", () => {
    const welcome = stripComments(read(WELCOME));

    expect(welcome).toContain("else if (isDefaultAgent)");
    expect(welcome).toContain("else if (agent)");
    expect(welcome).toContain("{agent.name}");
    expect(welcome).toContain("<AgentAvatar");
  });
});

describe("quick actions", () => {
  test("have a stable, approved order", () => {
    const suggestions = stripComments(read(SUGGESTIONS));
    const actionKeys = [
      "analyzeFile",
      "reviewContract",
      "investigateDifference",
      "analyzeResult",
    ];
    const positions = actionKeys.map((key) =>
      suggestions.indexOf(`${key}.label`)
    );

    expect(positions.every((position) => position >= 0)).toBe(true);
    expect(positions).toEqual([...positions].sort((a, b) => a - b));
    expect(pt.chat.welcome.quickActions.analyzeFile.label).toBe(
      "Analisar arquivo"
    );
    expect(pt.chat.welcome.quickActions.reviewContract.label).toBe(
      "Revisar contrato"
    );
    expect(pt.chat.welcome.quickActions.investigateDifference.label).toBe(
      "Investigar divergência"
    );
    expect(pt.chat.welcome.quickActions.analyzeResult.label).toBe(
      "Analisar resultado"
    );
  });

  test("submit through the existing chat contract", () => {
    const suggestions = stripComments(read(SUGGESTIONS));

    expect(suggestions).toContain("onSubmit({");
    expect(suggestions).toContain("message: suggestion");
    expect(suggestions).toContain("currentMessageFiles = []");
    expect(suggestions).toContain("currentMessageFiles,");
    expect(suggestions).toContain("deepResearch: false");
    expect(suggestions).not.toMatch(/fetch\(|axios|\/api\//);
  });

  test("use compact commands for the default Central context", () => {
    const suggestions = stripComments(read(SUGGESTIONS));

    expect(suggestions).toContain("<Button");
    expect(suggestions).toContain('t("contextLabel")');
    expect(suggestions).toContain("icon={SvgArrowUpRight}");
    expect(suggestions).toContain('prominence="tertiary"');
    expect(suggestions).toContain('size="sm"');
    expect(suggestions).toContain("flex-wrap");
    expect(suggestions).not.toMatch(/Card|shadow-|gradient|overflow-x-auto/);
  });

  test("keeps custom-agent starter message presentation separate", () => {
    const suggestions = stripComments(read(SUGGESTIONS));

    expect(suggestions).toContain("if (!isDefaultAgent)");
    expect(suggestions).toContain('prominence="secondary"');
    expect(suggestions).toContain('width="full"');
  });
});

describe("continuous home to conversation transition", () => {
  const appPage = stripComments(read(APP_PAGE));

  test("keeps one composer instance outside the fading home rows", () => {
    expect(appPage.match(/<AppInputBar$/gm) ?? []).toHaveLength(1);
    expect(appPage).not.toMatch(/<AppInputBar[^>]*\bkey=/);

    const welcomeAt = appPage.indexOf("<WelcomeMessage");
    const composerAt = appPage.search(/<AppInputBar$/m);
    const suggestionsAt = appPage.indexOf("<Suggestions");
    expect(composerAt).toBeGreaterThan(welcomeAt);
    expect(suggestionsAt).toBeGreaterThan(composerAt);
  });

  test("preserves the existing grid transition and restrained fade", () => {
    expect(appPage).toContain(
      'appPosition.isChat()\n          ? "1fr auto 0fr"'
    );
    expect(appPage).toContain('"minmax(0, 4fr) auto minmax(0, 5fr)"');
    expect(appPage).toContain("transition-[grid-template-rows]");
    expect(appPage).toContain("transition={{ duration: 0.15 }}");
    expect(appPage).not.toMatch(/scale:|spring|bounce/);
  });

  test("retains draft, model, and attachment state across the transition", () => {
    const composer = stripComments(read(APP_INPUT_BAR));

    expect(composer).toContain("useDraft");
    expect(composer).toContain("placeholder ??");
    expect(appPage).toContain('centralHomeT("inputPlaceholder")');
    expect(appPage).toContain("selectedModels={multiModel.selectedModels}");
    expect(appPage).toContain("currentMessageFiles");
    expect(appPage).toContain("setCurrentMessageFiles");
  });

  test("lets zero, one, or many attachments expand without a fixed home height", () => {
    expect(appPage).toContain("overflow-y-auto overflow-x-hidden");
    expect(appPage).not.toMatch(/max-h-\[[^\]]+\][\s\S]{0,500}<AppInputBar/);
    expect(appPage).toContain("hasHomeSuggestions");
  });
});

describe("sibling and accessibility alignment", () => {
  test("keeps the NRF home on the same welcome and action components", () => {
    const nrf = stripComments(read(NRF_PAGE));

    expect(nrf).toContain("<WelcomeMessage isDefaultAgent />");
    expect(nrf).toContain("currentMessageFiles={currentMessageFiles}");
    expect(nrf.match(/<AppInputBar$/gm) ?? []).toHaveLength(1);
  });

  test("translates the onboarding label and shortens its motion", () => {
    const onboarding = stripComments(read(ONBOARDING));

    expect(onboarding).toContain('aria-label={t("flow.ariaLabel")}');
    expect(onboarding).toContain("motion-safe:animate-in");
    expect(onboarding).toContain("duration-fast");
    expect(onboarding).not.toContain("duration-500");
  });
});

describe("static safety", () => {
  const changedProductionFiles = [
    WELCOME,
    "src/app/app/components/AgentDescription.tsx",
    SUGGESTIONS,
    ONBOARDING,
    APP_PAGE,
    NRF_PAGE,
  ];

  test.each(changedProductionFiles)("%s uses only theme tokens", (file) => {
    const source = stripComments(read(file));
    expect(source).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
    expect(source).not.toMatch(/\bdark:/);
    expect(source).not.toMatch(
      /\b(bg|text|border)-(gray|slate|zinc|red|green|blue|amber|yellow)-\d{2,3}\b/
    );
  });

  test("introduces no dashboard or fabricated metric language", () => {
    const source = changedProductionFiles.map(read).join("\n");

    expect(source).not.toMatch(
      /\b(?:KPI|ROI|SLA)\b|health score|coverage percentage|risk counter/i
    );
    expect(source).not.toMatch(
      /findings count|occurrences count|report count/i
    );
  });
});
