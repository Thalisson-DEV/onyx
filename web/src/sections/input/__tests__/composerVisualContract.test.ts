/**
 * TON-VIS-004 composer contract.
 *
 * The composer is the one control the whole product turns on, and it cannot be
 * rendered in jsdom: it needs the session store, the query controller, the LLM
 * manager, voice, projects and the agent tree. So this suite asserts the two
 * things that are checkable without a browser and that regress silently —
 * the CSS rule that now draws the composer, and the source-level invariants of
 * the four files VIS-004 touched. It is the same approach `dropzonePaste.test.ts`
 * uses for its call sites and `ton-foundations.test.ts` uses for `stateful/styles.css`.
 *
 * Behaviour (Enter, Shift+Enter, send, stop, queue, drafts, slash commands,
 * paste, dropzone) is covered by the Playwright specs under `web/tests/e2e/chat`.
 * What this file guards is that VIS-004 did not quietly delete the code those
 * specs drive.
 */
import fs from "node:fs";
import path from "node:path";

import en from "@/i18n/messages/en.json";

const WEB_ROOT = path.resolve(__dirname, "../../../..");

const read = (relativePath: string): string =>
  fs.readFileSync(path.join(WEB_ROOT, relativePath), "utf8");

/**
 * Comments explain what a rule replaced, so they must not be able to satisfy or
 * break an assertion about the rule itself.
 */
const stripComments = (source: string): string =>
  source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

const COMPOSER_CSS = "src/app/css/content-editable.css";
const APP_INPUT_BAR = "src/sections/input/AppInputBar.tsx";
const BASE_INPUT_BAR = "src/sections/input/BaseInputBar.tsx";
const SHARED_INPUT_BAR = "src/sections/input/SharedAppInputBar.tsx";
const APP_PAGE = "src/views/AppPage.tsx";
const APP_CHROME = "src/layouts/chromes/AppChrome.tsx";

/** Every composer surface VIS-004 re-skinned. */
const COMPOSER_SOURCES = [
  APP_INPUT_BAR,
  BASE_INPUT_BAR,
  SHARED_INPUT_BAR,
] as const;

const composerCss = stripComments(read(COMPOSER_CSS));

/** Body of a top-level CSS rule whose selector is exactly `selector`. */
function ruleBody(css: string, selector: string): string {
  const pattern = new RegExp(
    `(^|\\})\\s*${selector.replace(/[.:()]/g, "\\$&")}\\s*\\{([^}]*)\\}`,
    "m"
  );
  const match = pattern.exec(css);
  if (!match) throw new Error(`no rule for ${selector}`);
  return match[2]!;
}

// ---------------------------------------------------------------------------
// 1-3. The edge is a border, not a shadow, at the TON radius
// ---------------------------------------------------------------------------

describe("composer edge", () => {
  test("is drawn by a tokenized 1px border over the field surface", () => {
    const base = ruleBody(composerCss, ".ton-composer");

    expect(base).toContain("var(--weight-line-border)");
    expect(base).toMatch(
      /border:\s*calc\(var\(--weight-line-border\)[^;]*solid/
    );
    expect(base).toContain("var(--border-01)");
    expect(base).toContain("background-color: var(--background-neutral-00)");
  });

  test("uses the approved composer radius", () => {
    expect(ruleBody(composerCss, ".ton-composer")).toContain(
      "border-radius: var(--radius-12)"
    );
  });

  test("is elevation-0: the chrome carries no shadow but the focus ring", () => {
    // Across the three `.ton-composer*` rules there is exactly one `box-shadow`,
    // the inset focus ring. Anything else would be elevation, which the composer
    // is not entitled to. (`.rich-input-tile-selected` has its own inset ring;
    // that predates VIS-004 and belongs to the tile, not the composer edge.)
    const chromeRules = [
      ruleBody(composerCss, ".ton-composer"),
      ruleBody(composerCss, ".ton-composer-interactive:hover"),
      ruleBody(composerCss, ".ton-composer-interactive:focus-within"),
    ].join(";");

    // One `box-shadow` declaration, and it is the inset ring. The base rule only
    // names `box-shadow` inside `transition`, so match on declarations.
    expect(chromeRules.match(/(^|;)\s*box-shadow:/g) ?? []).toHaveLength(1);
    expect(chromeRules).toContain("box-shadow: inset");
    expect(composerCss).not.toMatch(/shadow-box-0\d/);
    expect(ruleBody(composerCss, ".ton-composer")).not.toMatch(
      /(^|;)\s*box-shadow:/
    );
  });

  test.each(COMPOSER_SOURCES)(
    "%s stops using shadow-box-01 as its edge and adopts the shared rule",
    (file) => {
      const source = stripComments(read(file));

      expect(source).not.toContain("shadow-box-01");
      // The old 16px card geometry is gone with it.
      expect(source).not.toMatch(/rounded-(t-)?16/);
      expect(source).toContain("ton-composer");
    }
  );

  test("no composer source hardcodes a colour or a raw radius", () => {
    for (const file of [...COMPOSER_SOURCES, COMPOSER_CSS]) {
      const source = stripComments(read(file));
      expect({ file, hex: /#[0-9a-fA-F]{3,8}\b/.test(source) }).toEqual({
        file,
        hex: false,
      });
      // The `dark:` modifier is banned repo-wide: tokens carry both themes.
      expect({ file, dark: /(^|[\s"'`:])dark:/m.test(source) }).toEqual({
        file,
        dark: false,
      });
    }
  });
});

// ---------------------------------------------------------------------------
// 4-5. Focus is explicit, and free
// ---------------------------------------------------------------------------

describe("composer focus", () => {
  test("focus-within raises a focus edge plus an inner ring, from tokens", () => {
    const focus = ruleBody(
      composerCss,
      ".ton-composer-interactive:focus-within"
    );

    expect(focus).toContain("border-color: var(--border-05)");
    expect(focus).toMatch(
      /box-shadow:\s*inset 0 0 0 calc\(var\(--weight-line-focus\)\s*\*\s*1px\)\s*var\(--background-tint-04\)/
    );
  });

  test("focus cannot move the layout", () => {
    const focus = ruleBody(
      composerCss,
      ".ton-composer-interactive:focus-within"
    );

    // The proof is that the rule touches only two non-layout properties. An
    // inset box-shadow paints inside the existing box, and border-color cannot
    // change the border box because the width is not restated here.
    const properties = focus
      .split(";")
      .map((declaration) => declaration.split(":")[0]!.trim())
      .filter(Boolean);
    expect(properties.sort()).toEqual(["border-color", "box-shadow"]);
  });

  test("hover is declared before focus, so a focused composer keeps its edge", () => {
    const hoverAt = composerCss.indexOf(".ton-composer-interactive:hover");
    const focusAt = composerCss.indexOf(
      ".ton-composer-interactive:focus-within"
    );

    expect(hoverAt).toBeGreaterThan(-1);
    expect(focusAt).toBeGreaterThan(hoverAt);
    expect(ruleBody(composerCss, ".ton-composer-interactive:hover")).toContain(
      "border-color: var(--border-02)"
    );
  });

  test("the focus edge lives on the container, not on the editable", () => {
    // `outline-hidden` has to stay on the editable: its wrapper is
    // `overflow-hidden` for autosize, which clips the global `:focus-visible`
    // outline and its offset. `focus-within` on the container is what replaces it.
    for (const file of [APP_INPUT_BAR, BASE_INPUT_BAR]) {
      const source = stripComments(read(file));
      expect({ file, hidden: source.includes("outline-hidden") }).toEqual({
        file,
        hidden: true,
      });
      expect({
        file,
        interactive: source.includes("ton-composer-interactive"),
      }).toEqual({ file, interactive: true });
    }
  });

  test("the shared-chat composer is inert, so it takes no interactive states", () => {
    const source = stripComments(read(SHARED_INPUT_BAR));

    expect(source).toContain("ton-composer");
    expect(source).not.toContain("ton-composer-interactive");
  });
});

// ---------------------------------------------------------------------------
// 6-7. The shadow workaround is gone
// ---------------------------------------------------------------------------

describe("the 14px shadow compensation", () => {
  test("AppPage no longer carries the composer shadow spacers", () => {
    const source = read(APP_PAGE);

    expect(source).not.toContain("h-[14px]");
    // The note that explained them, and its two siblings, are gone as well.
    expect(source).not.toContain("shadow-box-01");
  });

  test("the AppChrome footer padding is unconditional again", () => {
    const source = read(APP_CHROME);

    expect(source).toContain("py-2");
    expect(source).not.toContain("shadow-box-01");
    // The compensation was the only reason the footer read the route.
    expect(source).not.toMatch(/isChat\(\)\s*\?\s*"pb-2"/);
  });

  test("no file still explains the workaround", () => {
    for (const file of [APP_INPUT_BAR, APP_PAGE, APP_CHROME]) {
      const source = read(file);
      expect({ file, mentions: source.includes("14px") }).toEqual({
        file,
        mentions: false,
      });
    }
  });
});

// ---------------------------------------------------------------------------
// 8-9. One id per control
// ---------------------------------------------------------------------------

describe("composer element ids", () => {
  test("the send button id exists exactly once in the codebase", () => {
    // The defect VIS-000 recorded: `chatControls` stays mounted while search
    // mode collapses it, so the search row's second copy of this id put two
    // nodes with the same id in the DOM at the same time.
    const source = read(APP_INPUT_BAR);
    const occurrences = source.match(/id="onyx-chat-input-send-button"/g) ?? [];

    expect(occurrences).toHaveLength(1);
  });

  test("the search action has its own id", () => {
    const source = read(APP_INPUT_BAR);

    expect(source).toContain('id="onyx-chat-input-search-button"');
    expect(
      source.match(/id="onyx-chat-input-search-button"/g) ?? []
    ).toHaveLength(1);
  });

  test("no composer id is declared twice", () => {
    const source = read(APP_INPUT_BAR);
    const ids = (source.match(/id="([^"]+)"/g) ?? []).map((match) =>
      match.slice(4, -1)
    );

    expect(ids.sort()).toEqual([...new Set(ids)].sort());
  });

  test("the ids the app and the e2e page object address are preserved", () => {
    const source = read(APP_INPUT_BAR);

    // `AppChrome` restores focus by looking the textbox up by id, and
    // `tests/e2e/chat/InputBar.ts` locates all three.
    expect(source).toContain('id="onyx-chat-input"');
    expect(source).toContain('id="onyx-chat-input-textbox"');
    expect(read(APP_CHROME)).toContain('"onyx-chat-input-textbox"');
  });
});

// ---------------------------------------------------------------------------
// 10. Send, stop and the search row are reachable by name
// ---------------------------------------------------------------------------

describe("composer accessible names", () => {
  const catalog = en.chat.input.appInputBar;

  test("send, queue and stop each name their action", () => {
    expect(catalog.sendButton.ariaLabel).toBeTruthy();
    expect(catalog.sendButton.queueAriaLabel).toBeTruthy();
    expect(catalog.stopButton.ariaLabel).toBeTruthy();
  });

  test("the search row names both of its icon-only buttons", () => {
    expect(catalog.clearButton.ariaLabel).toBeTruthy();
    expect(catalog.searchButton.ariaLabel).toBeTruthy();
  });

  test("the send button's name follows the action it will perform", () => {
    const source = read(APP_INPUT_BAR);

    expect(source).toContain("aria-label={sendButtonAriaLabel}");
    expect(source).toContain("appInputBar.sendButton.queueAriaLabel");
    expect(source).toContain("appInputBar.stopButton.ariaLabel");
  });

  test("no user-facing string is hardcoded in the composer", () => {
    for (const file of COMPOSER_SOURCES) {
      const source = read(file);
      // `SharedAppInputBar` keeps one opted-out literal, the placeholder model
      // name, which VIS-007 owns along with the rest of the upstream branding.
      const optOuts = (source.match(/i18n\/no-raw-jsx-text/g) ?? []).length;
      expect({ file, optOuts }).toEqual({
        file,
        optOuts: file === SHARED_INPUT_BAR ? 1 : 0,
      });
    }
  });
});

// ---------------------------------------------------------------------------
// 11. Toolbar priority and the 375px guarantee
// ---------------------------------------------------------------------------

describe("composer toolbar", () => {
  const source = stripComments(read(APP_INPUT_BAR));

  test("the secondary group absorbs narrow screens by scrolling, not hiding", () => {
    expect(source).toContain(
      "flex flex-row items-center min-w-0 flex-1 overflow-x-auto no-scrollbar -my-1 py-1"
    );
  });

  test("send and stop never shrink", () => {
    expect(source).toContain("flex flex-row items-center gap-1 shrink-0");
  });

  test("no composer control is hidden by a breakpoint", () => {
    // `display: none` at a breakpoint is the failure mode VIS-004 forbids:
    // a control with no alternate access path would simply vanish on mobile.
    expect(source).not.toMatch(/\b(sm|md|lg|xl):hidden\b/);
    expect(source).not.toMatch(/\bhidden\s+(sm|md|lg):(flex|block|inline)/);
  });

  test("the toolbar transition is tokenized", () => {
    expect(source).toContain("transition-all duration-fast");
  });
});

// ---------------------------------------------------------------------------
// 12. Deep Research reads as a state, not as decoration
// ---------------------------------------------------------------------------

describe("Deep Research control", () => {
  const source = stripComments(read(APP_INPUT_BAR));

  test("active shifts the surface, inactive stays transparent", () => {
    expect(source).toContain(
      'deepResearchEnabled ? "select-heavy" : "select-light"'
    );
    // The selection ring and the fold state come from the same flag, so three
    // signals move together and none of them is colour alone.
    expect(source).toContain(
      'state={deepResearchEnabled ? "selected" : "empty"}'
    );
    expect(source).toContain("foldable={!deepResearchEnabled}");
  });

  test("the active state uses no glow, gradient or sparkle", () => {
    expect(source).not.toMatch(/\b(shadow-box|blur|glow|radial|sparkle)/i);
  });

  test("its behaviour is untouched", () => {
    expect(source).toContain("onClick={toggleDeepResearch}");
    expect(source).toContain("showDeepResearch &&");
  });
});

// ---------------------------------------------------------------------------
// 13. One model-selector placement
// ---------------------------------------------------------------------------

describe("model selector placement", () => {
  const source = stripComments(read(APP_PAGE));

  test("renders from exactly one call site", () => {
    expect(source.match(/<MultiModelSelector/g) ?? []).toHaveLength(1);
  });

  test("that call site sits in the composer block", () => {
    const selectorAt = source.indexOf("<MultiModelSelector");
    // Anchored on the element, not the name: `AppInputBarHandle` appears far
    // earlier as the type argument of the composer's ref.
    const composerAt = source.search(/<AppInputBar$/m);
    const welcomeAt = source.indexOf("<WelcomeMessage");

    // Integrated into the composer toolbar, and no longer inside the greeting row.
    expect(selectorAt).toBeGreaterThan(welcomeAt);
    expect(selectorAt).toBeGreaterThan(composerAt);
  });

  test("the composer toolbar renders the model selector slot", () => {
    const composer = stripComments(read(APP_INPUT_BAR));
    expect(composer).toContain("{modelSelector}");
  });

  test("the gate is the union of the two it replaced", () => {
    expect(source).toContain("modelSelectorVisible");
    // Chat kept its unconditional access; the new-session row still waits for a
    // provider and still stays out of search mode.
    expect(source).toMatch(/appPosition\.isChat\(\)\s*\|\|/);
    expect(source).toContain("llmManager.hasAnyProvider");
    expect(source).toContain('state.appMode === "search"');
  });

  test("the selector itself is unchanged", () => {
    const selector = read("src/sections/model-selector/MultiModelSelector.tsx");

    expect(selector).toContain('data-testid="model-selector"');
    expect(selector).toContain("MAX_MODELS");
  });
});

// ---------------------------------------------------------------------------
// 14. The disabled composer states itself instead of blurring
// ---------------------------------------------------------------------------

describe("disabled composer", () => {
  test("the shared-chat composer drops the decorative backdrop blur", () => {
    const source = read(SHARED_INPUT_BAR);

    expect(source).not.toContain("backdrop-blur");
    expect(source).not.toMatch(/bg-background-neutral-00\/\d+/);
  });

  test("it uses the repository's disabled treatment, which announces itself", () => {
    const source = stripComments(read(SHARED_INPUT_BAR));

    // `Disabled` sets `aria-disabled` and the shared disabled visuals, so the
    // state is not carried by an opacity literal at the call site.
    expect(source).toContain("<Disabled disabled>");
    expect(source).not.toMatch(/\bopacity-\d+/);
  });

  test("the app composer keeps its own disabled wrapper", () => {
    expect(stripComments(read(APP_INPUT_BAR))).toContain(
      "<Disabled disabled={disabled} allowClick>"
    );
  });
});

// ---------------------------------------------------------------------------
// 15. Nothing mature was replaced
// ---------------------------------------------------------------------------

describe("preserved editor and composer contracts", () => {
  test("no editor library was introduced", () => {
    const packageJson = read("package.json");

    for (const library of [
      "@tiptap",
      "lexical",
      "prosemirror",
      "slate",
      "quill",
    ]) {
      expect({ library, present: packageJson.includes(library) }).toEqual({
        library,
        present: false,
      });
    }
  });

  test.each(COMPOSER_SOURCES.slice(0, 2))(
    "%s still drives the repository's own contentEditable",
    (file) => {
      const source = read(file);

      expect(source).toContain("useContentEditable");
      expect(source).toContain("handleCompositionStart");
      expect(source).toContain("handleCompositionEnd");
      expect(source).toContain("handleCopy");
      expect(source).toContain("handleCut");
      expect(source).toContain("firstStrongTextDir");
      expect(source).toContain("data-placeholder");
    }
  );

  test("the app composer keeps drafts, the queue, slash commands and paste", () => {
    const source = read(APP_INPUT_BAR);

    expect(source).toContain("useDraft");
    expect(source).toContain("clearChatDraft");
    expect(source).toContain("enqueueCurrentMessage");
    expect(source).toContain("MAX_QUEUED_MESSAGES");
    expect(source).toContain("handleInputNavKeys");
    expect(source).toContain("handleKeyDownForPromptShortcuts");
    expect(source).toContain("getPastedFilesIfNoText");
    expect(source).toContain("handleFileUpload");
  });

  test("Enter submits and Shift+Enter still falls through to a newline", () => {
    const source = read(APP_INPUT_BAR);

    expect(source).toMatch(/event\.key === "Enter"/);
    expect(source).toContain("!event.shiftKey");
    expect(source).toContain("!event.nativeEvent.isComposing");
  });

  test("send and stop keep their existing semantics", () => {
    const source = read(APP_INPUT_BAR);

    expect(source).toContain("stopGenerating()");
    expect(source).toContain("submitMessage(message)");
    expect(source).toContain("stopTTS({ manual: true })");
  });

  test("the attachment strip keeps its measured height", () => {
    const source = read(APP_INPUT_BAR);

    expect(source).toContain("const PADDING = 8");
    expect(source).toContain("filesWrapperRef");
    expect(source).toContain("<FileCard");
  });

  test("voice controls are still mounted", () => {
    const source = read(APP_INPUT_BAR);

    expect(source).toContain("<MicrophoneButton");
    expect(source).toContain("<Waveform");
    expect(source).toContain("useVoiceMode");
  });

  test("the placeholder stays a data attribute, so VIS-003 can change the copy", () => {
    expect(read(APP_INPUT_BAR)).toContain(
      "data-placeholder={activePlaceholder}"
    );
    expect(composerCss).toContain("content: attr(data-placeholder)");
  });
});
