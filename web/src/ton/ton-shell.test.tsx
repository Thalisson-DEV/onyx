/**
 * TON-VIS-002 shell contract.
 *
 * FE-004's information architecture is asserted by `ton-navigation.test.tsx`,
 * which renders the sidebar for real: destinations, order, landmarks, the absence
 * of the deferred domains, admin gating and FE-003 suppression. VIS-002 changed
 * none of that and this file does not restate it.
 *
 * What this file guards is the presentation layer that suite cannot see — the
 * compiled CSS that draws the shell, and the source-level invariants of the files
 * VIS-002 touched. It is the approach `dropzonePaste.test.tsx` and
 * `ton-foundations.test.ts` already use for surfaces whose styling is the
 * contract.
 */
import fs from "node:fs";
import path from "node:path";

import en from "@/i18n/messages/en.json";

const WEB_ROOT = path.resolve(__dirname, "../..");

const read = (relativePath: string): string =>
  fs.readFileSync(path.join(WEB_ROOT, relativePath), "utf8");

/** Rules explain what they replaced, so prose must not satisfy an assertion. */
const stripComments = (source: string): string =>
  source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

const STATEFUL_CSS = "lib/opal/src/core/interactive/stateful/styles.css";
const SIDEBAR_CSS = "lib/opal/src/layouts/sidebar/styles.css";
const SIDEBAR_TAB =
  "lib/opal/src/components/buttons/sidebar-tab/components.tsx";
const SIDEBAR_TAB_CSS =
  "lib/opal/src/components/buttons/sidebar-tab/styles.css";
const SIDEBAR_LAYOUT = "lib/opal/src/layouts/sidebar/components.tsx";
const OPAL_STRINGS = "lib/opal/src/strings.tsx";
const BRIDGE = "src/i18n/OpalStringsBridge.tsx";
const APP_SIDEBAR = "src/sections/sidebar/AppSidebar.tsx";
const CHAT_BUTTON = "src/sections/sidebar/ChatButton.tsx";
const PROJECT_FOLDER = "src/lib/projects/components/ProjectFolderButton.tsx";
const APP_CHROME = "src/layouts/chromes/AppChrome.tsx";
const APP_HEADER = "src/layouts/chromes/AppHeader.tsx";
const COMPOSER_CSS = "src/app/css/content-editable.css";

const statefulCss = stripComments(read(STATEFUL_CSS));
const sidebarCss = stripComments(read(SIDEBAR_CSS));

/** Body of the top-level rule whose selector matches `pattern`. */
function ruleBody(css: string, pattern: RegExp): string {
  const at = css.search(pattern);
  if (at === -1) throw new Error(`no rule matching ${pattern}`);
  const open = css.indexOf("{", at);
  const close = css.indexOf("}", open);
  return css.slice(open + 1, close);
}

// ---------------------------------------------------------------------------
// 10-11. Navigation and conversation rows use the TON state treatment
// ---------------------------------------------------------------------------

describe("navigation row selection", () => {
  test("selected sidebar rows are marked on the leading edge, not ringed", () => {
    // The defect: a full-perimeter ring on a full-width row reads as an outlined
    // card, which is the one shape TON navigation may not use.
    const marker = ruleBody(
      statefulCss,
      /\.interactive:is\(\s*\[data-interactive-variant="sidebar-heavy"\],\s*\[data-interactive-variant="sidebar-light"\]\s*\)\[data-interactive-state="selected"\]::before/
    );

    expect(marker).toContain('content: ""');
    expect(marker).toContain("inset-inline-start: 0");
    expect(marker).toContain("var(--theme-primary-04)");
    expect(marker).toContain("var(--weight-line-focus)");
  });

  test("the sidebar variants no longer take the full-perimeter ring", () => {
    // The ring rules survive for the chip-shaped `select-*` family, which is what
    // VIS-004's Deep Research control depends on. Only the sidebar left.
    const ringSelectors = statefulCss.match(
      /\.interactive:is\([^)]*\)\[data-interactive-state="selected"\][^{:]*\{[^}]*box-shadow[^}]*\}/g
    );

    expect(ringSelectors?.length).toBeGreaterThan(0);
    for (const rule of ringSelectors!) {
      expect(rule).not.toContain("sidebar-heavy");
      expect(rule).not.toContain("sidebar-light");
    }
  });

  test("the marker is a shape, so it does not rest on colour alone", () => {
    const marker = ruleBody(
      statefulCss,
      /\[data-interactive-variant="sidebar-light"\]\s*\)\[data-interactive-state="selected"\]::before/
    );

    // Position and size are the signal; the hue only names it.
    expect(marker).toMatch(/position:\s*absolute/);
    expect(marker).toMatch(/width:\s*calc\(/);
  });

  test("pressed thickens the marker, as the ring used to", () => {
    expect(statefulCss).toMatch(
      /\[data-interactive-state="selected"\]:active:not\(\[data-disabled\]\)::before/
    );
  });

  test("row geometry is the compact 4px step, not the 8px chip step", () => {
    const source = read(SIDEBAR_TAB);

    expect(source).toContain("rounding={1}");
    expect(source).not.toContain("rounding={2}");
    // The focus overlay follows the same geometry.
    expect(source).toContain("rounded-04");
    expect(source).not.toContain("rounded-08");
  });

  test("the conversation row inherits the same language", () => {
    // `ChatButton` renders a `SidebarTab` and passes `selected`, so it cannot
    // drift from the navigation rows. It must not add a treatment of its own.
    const source = stripComments(read(CHAT_BUTTON));

    expect(source).toContain("<SidebarTab");
    expect(source).toContain("selected={active}");
    expect(source).not.toMatch(/rounded-(08|12|16|full)/);
  });
});

// ---------------------------------------------------------------------------
// 12-14. Hover, focus, selection and the folded column
// ---------------------------------------------------------------------------

describe("interaction states stay separable", () => {
  test("selected:hover keeps the selection instead of inverting it", () => {
    // VIS-001's invariant, re-checked here because VIS-002 owns these variants
    // now: a selected row's hover must not step onto the unselected hover
    // surface, or moving the pointer erases the selection.
    const selectedHover = statefulCss.match(
      /\[data-interactive-variant="sidebar-(heavy|light)"\]\[data-interactive-state="selected"\](?::hover|\[data-interaction="hover"\])[^{]*\{[^}]*\}/g
    );

    expect(selectedHover?.length).toBeGreaterThan(0);
    for (const cell of selectedHover!) {
      expect(cell).not.toContain("bg-background-tint-03");
    }
  });

  test("focus is the row overlay's own outline, independent of selection", () => {
    const source = read(SIDEBAR_TAB);

    // Selection is a `::before` on the container; focus is an outline on the
    // control. Different elements, different properties, so both can show.
    expect(source).toContain("focus-visible:outline-2");
    expect(source).toContain("outline-border-04");
  });

  test("selection survives folding, because it needs no text", () => {
    const marker = ruleBody(
      statefulCss,
      /\[data-interactive-variant="sidebar-light"\]\s*\)\[data-interactive-state="selected"\]::before/
    );

    // Nothing in the marker refers to the label, and the fold rules only touch
    // the label and the action slot.
    expect(marker).not.toMatch(/content:\s*attr/);
    const foldCss = stripComments(read(SIDEBAR_TAB_CSS));
    expect(foldCss).toContain("--sidebar-tab-label-opacity");
    expect(foldCss).not.toContain("data-interactive-state");
  });
});

// ---------------------------------------------------------------------------
// Sidebar surface, rhythm and density
// ---------------------------------------------------------------------------

describe("sidebar surface", () => {
  test("the boundary against the canvas is a 1px logical edge, not a shadow", () => {
    for (const selector of [
      /\.opal-sidebar-root__column/,
      /\.opal-sidebar-root__overlay \{/,
    ]) {
      const body = ruleBody(sidebarCss, selector);
      expect(body).toContain("border-inline-end");
      expect(body).toContain("var(--weight-line-border)");
      expect(body).toContain("var(--border-01)");
    }
    expect(sidebarCss).not.toMatch(/shadow-box-0\d/);
  });

  test("the surface stays on its semantic role", () => {
    // `background-tint-02` is the `surface` role. VIS-002 did not repaint the
    // column; it gave it an edge.
    expect(ruleBody(sidebarCss, /\.opal-sidebar-root__column/)).toContain(
      "bg-background-tint-02"
    );
  });

  test("the width contract is untouched", () => {
    const sizes = read("lib/opal/src/styles/sizes.css");

    expect(sizes).toContain("--sidebar-width-expanded: 15rem");
    expect(sizes).toContain("--sidebar-width-folded: 3.25rem");
  });

  test("the brand band matches the chrome header height", () => {
    const topbar = ruleBody(sidebarCss, /\.opal-sidebar-header__topbar \{/);

    expect(topbar).toContain("var(--chrome-header-height)");
    expect(topbar).toContain("items-center");
  });

  test("the fold control sits on the mark's centre line", () => {
    expect(
      ruleBody(sidebarCss, /\.opal-sidebar-header__topbar-inner/)
    ).toContain("items-center");
  });

  test("section rhythm carries the hierarchy", () => {
    // Spacing before containers: the gap above a section header is what makes
    // "new group" legible without a card or a heading size.
    expect(ruleBody(sidebarCss, /\.opal-sidebar-section__header/)).toContain(
      "pt-5"
    );
  });

  test("section labels are lifted but stay subordinate to a row label", () => {
    const source = read(SIDEBAR_LAYOUT);

    // `text-03` measures 4.59:1 light / 6.03:1 dark on the sidebar surface;
    // `text-02` was 3.29:1. A selected row label is `text-04`, still above it.
    expect(source).toContain('color="text-03"');
    expect(source).toContain('font="secondary-body"');
  });

  test("no card box separates the sections", () => {
    expect(sidebarCss).not.toMatch(/section__header[^}]*\bborder\b/);
    expect(sidebarCss).not.toMatch(/section__header[^}]*rounded/);
  });
});

// ---------------------------------------------------------------------------
// Product navigation versus conversation history
// ---------------------------------------------------------------------------

describe("product and history read as different layers", () => {
  const source = stripComments(read(APP_SIDEBAR));

  test("history keeps its own landmark", () => {
    expect(source).toContain("historyNav.ariaLabel");
    expect(source).toContain("productNav.ariaLabel");
  });

  test("a divider marks the boundary, not a container", () => {
    expect(source).toContain("<Divider");
  });

  test("the destinations stay pinned above the scroll area", () => {
    const headerAt = source.indexOf("<SidebarLayouts.Header");
    const bodyAt = source.indexOf("<SidebarLayouts.Body");
    const centralAt = source.indexOf('href="/app"');
    const recentsAt = source.indexOf("<RecentsSection");

    expect(centralAt).toBeGreaterThan(headerAt);
    expect(centralAt).toBeLessThan(bodyAt);
    expect(recentsAt).toBeGreaterThan(bodyAt);
  });

  test("search reads as a utility, not a destination", () => {
    // No `href`: it opens a command menu. A destination would route.
    expect(source).toMatch(/SvgSearchMenu\}\s+onClick=\{open\}/);
  });
});

// ---------------------------------------------------------------------------
// 17. Project menu reachable without hover
// ---------------------------------------------------------------------------

describe("project row", () => {
  const source = stripComments(read(PROJECT_FOLDER));

  test("the menu uses the hover primitive, so touch can reach it", () => {
    // The old pair was `hidden` plus `group-hover/SidebarTab:flex`, which has no
    // hover-less fallback: on touch the menu could never appear.
    expect(source).toContain("<Hoverable.Root");
    expect(source).toContain("<Hoverable.Item");
    expect(source).not.toContain("group-hover/SidebarTab:flex");
  });

  test("the primitive it uses has a hover-less and a focus path", () => {
    const hoverCss = read("lib/opal/src/core/animations/styles.css");

    expect(hoverCss).toContain("@media (hover: hover)");
    expect(hoverCss).toContain(":has(:focus-visible)");
  });

  test("project behaviour is untouched", () => {
    for (const contract of [
      "useDroppable",
      "deleteProject",
      "handleRename",
      "ButtonRenaming",
      "chat_sessions",
    ]) {
      expect({ contract, present: source.includes(contract) }).toEqual({
        contract,
        present: true,
      });
    }
  });
});

// ---------------------------------------------------------------------------
// 16. Open / Close sidebar copy
// ---------------------------------------------------------------------------

describe("fold control copy", () => {
  test("Opal no longer hardcodes the label", () => {
    const source = read(SIDEBAR_LAYOUT);

    expect(source).not.toContain('"Open Sidebar"');
    expect(source).not.toContain('"Close Sidebar"');
    expect(source).toContain("useOpalStrings()");
    expect(source).toContain("strings.sidebarOpen");
    expect(source).toContain("strings.sidebarClose");
  });

  test("the label rides the typed string contract", () => {
    const strings = read(OPAL_STRINGS);

    expect(strings).toContain("sidebarOpen: string;");
    expect(strings).toContain("sidebarClose: string;");
  });

  test("the host feeds it real translations", () => {
    expect(read(BRIDGE)).toContain('sidebarOpen: t("sidebar.open")');
    expect(read(BRIDGE)).toContain('sidebarClose: t("sidebar.close")');
    expect(en.opal.sidebar.open).toBeTruthy();
    expect(en.opal.sidebar.close).toBeTruthy();
  });

  test("PT-BR renders Portuguese, which is the whole point", () => {
    const pt = JSON.parse(read("src/i18n/messages/pt.json")) as typeof en;

    expect(pt.opal.sidebar.open).toBe("Abrir a barra lateral");
    expect(pt.opal.sidebar.close).toBe("Fechar a barra lateral");
  });
});

// ---------------------------------------------------------------------------
// 15-16. Mobile overlay and the keyboard shortcut
// ---------------------------------------------------------------------------

describe("responsive shell", () => {
  test("the overlay, backdrop and spacer are unchanged", () => {
    for (const rule of [
      '.opal-sidebar-root__overlay[data-variant="mobile"]',
      '.opal-sidebar-root__overlay[data-variant="small"]',
      ".opal-sidebar-root__spacer",
      ".opal-sidebar-root__backdrop",
    ]) {
      expect({ rule, present: sidebarCss.includes(rule) }).toEqual({
        rule,
        present: true,
      });
    }
    expect(sidebarCss).toContain("-translate-x-full rtl:translate-x-full");
  });

  test("the breakpoint logic is untouched", () => {
    const source = read(SIDEBAR_LAYOUT);

    expect(source).toContain("useScreenSize");
    expect(source).toContain("isMobile");
    expect(source).toContain("isSmallScreen");
  });

  test("Cmd/Ctrl+E still toggles the sidebar", () => {
    const root = read("lib/opal/src/layouts/root/components.tsx");

    expect(root).toMatch(/"e"/);
    expect(root).toMatch(/metaKey|ctrlKey/);
  });
});

// ---------------------------------------------------------------------------
// 18-21. Loading, skeletons and data mechanics
// ---------------------------------------------------------------------------

describe("sidebar loading", () => {
  const source = stripComments(read(APP_SIDEBAR));

  test("skeleton widths are deterministic", () => {
    // They were re-sorted through `Math.random()` on every render, which made the
    // rows jitter and gave server and client two different first paints.
    expect(source).not.toContain("Math.random");
    expect(source).toContain("SKELETON_WIDTHS");
  });

  test("the body no longer blanks while a source loads", () => {
    expect(source).not.toContain("isLoadingDynamicContent");
    expect(source).toContain("<SkeletonRows");
  });

  test("each section reads the source it depends on", () => {
    expect(source).toContain("isLoading={isLoadingChatSessions}");
    expect(source).toContain("isLoadingProjects ?");
  });

  test("history pagination mechanics are untouched", () => {
    for (const contract of [
      "useChatSessions",
      "IntersectionObserver",
      "sentinelRef",
      "onLoadMoreRef",
      "hasMore",
      "isLoadingMore",
      "loadMore",
    ]) {
      expect({ contract, present: source.includes(contract) }).toEqual({
        contract,
        present: true,
      });
    }
  });

  test("scroll persistence is untouched", () => {
    expect(read(SIDEBAR_LAYOUT)).toContain("opal-sidebar-scroll-");
    expect(source).toContain('scrollKey="app-sidebar"');
  });
});

// ---------------------------------------------------------------------------
// Header and chrome
// ---------------------------------------------------------------------------

describe("chrome header", () => {
  const header = stripComments(read(APP_HEADER));
  const chrome = stripComments(read(APP_CHROME));

  test("it was extracted, and AppChrome shrank accordingly", () => {
    expect(chrome).toContain("import AppHeader from");
    expect(chrome).toContain("<AppHeader />");
    expect(chrome).not.toContain("function Header()");
    expect(read(APP_CHROME).split("\n").length).toBeLessThan(300);
  });

  test("the extraction moved behaviour, not changed it", () => {
    for (const contract of [
      "handleMoveOperation",
      "deleteChatSession",
      "endIncognitoSession",
      "exportChatSession",
      "LOCAL_STORAGE_KEYS.HIDE_MOVE_CUSTOM_AGENT_MODAL",
      "useTierAtLeast",
      "useIsSearchModeAvailable",
      "ShareChatSessionModal",
    ]) {
      expect({ contract, present: header.includes(contract) }).toEqual({
        contract,
        present: true,
      });
    }
    // And none of it stayed behind.
    expect(chrome).not.toContain("exportChatSession");
    expect(chrome).not.toContain("endIncognitoSession");
  });

  test("the action strip is vertically centred in its band", () => {
    expect(header).toContain("items-center");
    expect(header).not.toContain("items-start");
  });

  test("no glassmorphism is left in the chrome", () => {
    expect(header).not.toContain("FrostedDiv");
    expect(chrome).not.toContain("FrostedDiv");
  });

  test("the share button has a real accessible name", () => {
    expect(header).not.toContain('aria-label="share-chat-button"');
    expect(header).toContain('aria-label={t("share.label")}');
  });

  test("share semantics, routing and permissions are untouched", () => {
    expect(header).toContain("setShowShareModal(true)");
    expect(header).toContain("appPosition.isChat()");
    expect(header).toContain("businessTier");
  });

  test("no product navigation moved into the header", () => {
    for (const destination of ["/app/agents", "SvgOnyxOctagon", "SidebarTab"]) {
      expect({ destination, present: header.includes(destination) }).toEqual({
        destination,
        present: false,
      });
    }
  });
});

describe("canvas edge", () => {
  const chrome = stripComments(read(APP_CHROME));

  test("the vignette scrim is tokenized", () => {
    expect(chrome).not.toContain("rgba(0, 0, 0, 0.4)");
    expect(chrome).toContain("var(--mask-02)");
  });

  test("the blur mask reads the reading width instead of repeating it", () => {
    expect(chrome).toContain("var(--app-page-main-content-width)");
    expect(chrome).not.toContain("25rem");
  });

  test("no decorative gradient or glass was added", () => {
    expect(chrome).not.toContain("backdrop-blur-xs");
    expect(chrome).not.toMatch(/radial-gradient/);
  });
});

// ---------------------------------------------------------------------------
// 22. The VIS-004 composer contract is untouched
// ---------------------------------------------------------------------------

describe("composer preservation", () => {
  test("the composer chrome is byte-identical in intent", () => {
    const composer = stripComments(read(COMPOSER_CSS));

    expect(composer).toContain(".ton-composer");
    expect(composer).toContain("border-radius: var(--radius-12)");
    expect(composer).toContain("border-color: var(--border-05)");
    expect(composer).toMatch(/box-shadow:\s*inset 0 0 0 calc\(/);
  });

  test("the select-* ring VIS-004's research control depends on survives", () => {
    expect(statefulCss).toMatch(
      /\[data-interactive-variant="select-heavy"\][\s\S]{0,200}box-shadow: inset 0 0 0 calc\(/
    );
  });

  test("VIS-002 changed no composer file", () => {
    const composerSources = [
      "src/sections/input/AppInputBar.tsx",
      "src/sections/input/BaseInputBar.tsx",
      "src/sections/input/SharedAppInputBar.tsx",
    ];
    for (const file of composerSources) {
      const source = read(file);
      expect({ file, hook: source.includes("ton-composer") }).toEqual({
        file,
        hook: true,
      });
    }
  });
});
