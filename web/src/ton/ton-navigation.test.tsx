/**
 * TON-FE-004 navigation contract.
 *
 * The app sidebar must read as TON: one central entry point, a specialists
 * destination, the workspace capabilities that exist today, and conversation
 * history kept apart from all three. Every destination must be a real route,
 * and no route may promise a capability TON has not built yet.
 *
 * The sidebar is rendered for real. Only data hooks and the row components of
 * other slices are stubbed, so the assertions below are about the shell's own
 * structure: landmarks, links, accessible names and section boundaries.
 */
import fs from "node:fs";
import path from "node:path";
import { render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { TooltipProvider } from "@radix-ui/react-tooltip";
import { SidebarStateProvider } from "@opal/layouts";
import englishMessages from "@/i18n/messages/en.json";
import portugueseMessages from "@/i18n/messages/pt.json";
import AppSidebar from "@/sections/sidebar/AppSidebar";
import { ADMIN_ROUTES, type FeatureFlags } from "@/lib/admin-routes";
import { buildItems } from "@/lib/admin-sidebar-utils";
import { Permission } from "@/lib/types";
import { Tier } from "@/lib/settings/types";

const WEB_ROOT = path.resolve(__dirname, "../..");
const APP_ROUTER_ROOT = path.join(WEB_ROOT, "src/app");

const LOCALES = ["en", "pt", "es", "fr", "de", "ja", "ko", "zh", "ar"] as const;

/** The TON destinations this slice is allowed to surface. */
const CENTRAL_ROUTE = "/app";
const SPECIALISTS_ROUTE = "/app/agents";

/** Domains later slices own. FE-004 must not link to any of them. */
const DEFERRED_SEGMENTS = ["occurrences", "reports", "sources"] as const;

// ---------------------------------------------------------------------------
// Route reality
// ---------------------------------------------------------------------------

/** Whether an app-router path resolves to a real `page.tsx`. */
function routeExists(href: string): boolean {
  const pathname = href.split("?")[0]!.replace(/^\//, "");
  return fs.existsSync(path.join(APP_ROUTER_ROOT, pathname, "page.tsx"));
}

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

interface ChatSessionFixture {
  id: string;
  name: string;
}

const CHAT_SESSIONS: ChatSessionFixture[] = [
  { id: "chat-1", name: "Consumo de diesel" },
  { id: "chat-2", name: "Contrato 4471" },
];

const PINNED_AGENTS = [{ id: 7, name: "Frota" }];

let chatSessions: ChatSessionFixture[] = CHAT_SESSIONS;
let pinnedAgents: { id: number; name: string }[] = PINNED_AGENTS;
let projects: { id: number; name: string }[] = [{ id: 1, name: "Vale Norte" }];

// ---------------------------------------------------------------------------
// Stubs — data sources and the row components other slices own
// ---------------------------------------------------------------------------

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn(), replace: jest.fn() }),
  usePathname: () => "/app",
  useSearchParams: () => new URLSearchParams(),
}));

jest.mock("@/lib/settings/hooks", () => ({
  useSettings: () => ({
    appName: "TON",
    enterprise: null,
    logoUrl: null,
    version: "0.0.0-dev",
    onyx_craft_enabled: true,
  }),
}));

jest.mock("@/hooks/useChatSessions", () => ({
  __esModule: true,
  default: () => ({
    chatSessions,
    refreshChatSessions: jest.fn(),
    isLoading: false,
    hasMore: false,
    isLoadingMore: false,
    loadMore: jest.fn(),
  }),
}));

jest.mock("@/lib/projects/hooks", () => ({
  useProjects: () => ({
    projects,
    refreshProjects: jest.fn(),
    isLoading: false,
  }),
}));

jest.mock("@/lib/agents/hooks", () => ({
  useAgents: () => ({ isLoading: false }),
  useActiveAgent: () => undefined,
  usePinnedAgents: () => ({
    pinnedAgents,
    updatePinnedAgents: jest.fn(),
    isLoading: false,
  }),
}));

jest.mock("@/lib/projects/providers", () => ({
  useProjectsContext: () => ({
    refreshCurrentProjectDetails: jest.fn(),
    currentProjectId: null,
  }),
}));

jest.mock("@/lib/projects/svc", () => ({
  removeChatSessionFromProject: jest.fn(),
}));

jest.mock("@/lib/sidebar/svc", () => ({ handleMoveOperation: jest.fn() }));

jest.mock("@/hooks/useNotifications", () => ({
  __esModule: true,
  default: () => ({ notifications: [], refresh: jest.fn() }),
}));

jest.mock("@/lib/analytics/hooks", () => ({
  PHFeatureFlag: { CRAFT_ANIMATION_DISABLED: "craft-animation-disabled" },
  usePHFeatureFlag: () => false,
}));

jest.mock("@/lib/analytics/utils", () => ({
  track: jest.fn(),
  AnalyticsEvent: { CLICKED_CRAFT_IN_SIDEBAR: "clicked_craft_in_sidebar" },
}));

jest.mock("@/lib/notifications/api", () => ({
  dismissNotification: jest.fn(),
}));

jest.mock("@/components/context/ModalContext", () => ({
  useModalContext: () => ({ newTenantInfo: null, invitationInfo: null }),
}));

jest.mock("@/providers/QueryControllerProvider", () => ({
  useQueryController: () => ({ setAppMode: jest.fn(), reset: jest.fn() }),
}));

jest.mock("@/app/craft/components/IntroBackground", () => ({
  __esModule: true,
  default: () => null,
}));

jest.mock("@/app/craft/components/IntroContent", () => ({
  __esModule: true,
  default: () => null,
}));

jest.mock("@/lib/agents/components", () => ({
  AgentButton: ({ agent }: { agent: { id: number; name: string } }) => (
    <a href={`/app?agentId=${agent.id}`}>{agent.name}</a>
  ),
  MoveCustomAgentChatModal: () => null,
}));

jest.mock("@/lib/projects/components", () => ({
  ProjectFolderButton: ({ project }: { project: { name: string } }) => (
    <div>{project.name}</div>
  ),
  FoldedProjectsPopover: () => <div data-testid="AppSidebar/projects" />,
  CreateProjectModal: () => null,
}));

jest.mock("@/sections/sidebar/ChatButton", () => ({
  __esModule: true,
  default: ({ chatSession }: { chatSession: ChatSessionFixture }) => (
    <a data-testid="ChatButton" href={`/app?chatId=${chatSession.id}`}>
      {chatSession.name}
    </a>
  ),
}));

jest.mock("@/sections/sidebar/AccountPopover", () => ({
  __esModule: true,
  default: () => <div data-testid="AccountPopover" />,
}));

jest.mock("@/sections/sidebar/ChatSearchCommandMenu", () => ({
  __esModule: true,
  default: ({
    trigger,
  }: {
    trigger: (open: () => void) => React.ReactNode;
  }) => <>{trigger(() => {})}</>,
}));

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

function renderSidebar(locale: "en" | "pt" = "en") {
  return render(
    <NextIntlClientProvider
      locale={locale}
      messages={locale === "pt" ? portugueseMessages : englishMessages}
    >
      <TooltipProvider>
        <SidebarStateProvider>
          <AppSidebar />
        </SidebarStateProvider>
      </TooltipProvider>
    </NextIntlClientProvider>
  );
}

/** The TON product-navigation landmark. */
function productNav(locale: "en" | "pt" = "en") {
  const messages = locale === "pt" ? portugueseMessages : englishMessages;
  return screen.getByRole("navigation", {
    name: messages.sidebar.appSidebar.productNav.ariaLabel,
  });
}

/** The conversation-history landmark. */
function historyNav(locale: "en" | "pt" = "en") {
  const messages = locale === "pt" ? portugueseMessages : englishMessages;
  return screen.getByRole("navigation", {
    name: messages.sidebar.appSidebar.historyNav.ariaLabel,
  });
}

beforeEach(() => {
  chatSessions = CHAT_SESSIONS;
  pinnedAgents = PINNED_AGENTS;
  projects = [{ id: 1, name: "Vale Norte" }];
});

// ---------------------------------------------------------------------------
// The TON destinations
// ---------------------------------------------------------------------------

describe("TON navigation destinations", () => {
  it("offers Central as the main entry point", () => {
    renderSidebar();

    const central = within(productNav()).getByRole("link", {
      name: "Central",
    });
    expect(central).toHaveAttribute("href", CENTRAL_ROUTE);
  });

  it("offers Especialistas as a destination of its own", () => {
    renderSidebar("pt");

    const specialists = within(productNav("pt")).getByRole("link", {
      name: "Especialistas",
    });
    expect(specialists).toHaveAttribute("href", SPECIALISTS_ROUTE);
  });

  it("puts Central and Especialistas in the same landmark, in that order", () => {
    renderSidebar();

    const links = within(productNav()).getAllByRole("link");
    expect(links.map((link) => link.getAttribute("href"))).toEqual([
      CENTRAL_ROUTE,
      SPECIALISTS_ROUTE,
    ]);
  });

  it("reaches the specialists destination with nothing pinned", () => {
    pinnedAgents = [];
    renderSidebar();

    expect(
      within(productNav()).getByRole("link", { name: "Specialists" })
    ).toHaveAttribute("href", SPECIALISTS_ROUTE);
    // A heading with no rows under it is not a section.
    expect(screen.queryByText("Pinned Specialists")).toBeNull();
  });

  it("keeps the pinned specialists as a shortcut, not as the destination", () => {
    renderSidebar();

    expect(screen.getByText("Pinned Specialists")).toBeVisible();
    expect(screen.getByRole("link", { name: "Frota" })).toHaveAttribute(
      "href",
      "/app?agentId=7"
    );
  });

  it("keeps the workspace capability that exists today", () => {
    renderSidebar("pt");

    expect(screen.getByText("Projetos")).toBeVisible();
    expect(screen.getByText("Vale Norte")).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Every destination is a real route
// ---------------------------------------------------------------------------

describe("route reality", () => {
  it("links only to routes that exist", () => {
    renderSidebar();

    const hrefs = screen
      .getAllByRole("link")
      .map((link) => link.getAttribute("href"))
      .filter((href): href is string => href !== null && href.startsWith("/"));

    expect(hrefs.length).toBeGreaterThan(0);
    for (const href of hrefs) {
      expect({ href, exists: routeExists(href) }).toEqual({
        href,
        exists: true,
      });
    }
  });

  it("resolves Central and Especialistas on direct entry", () => {
    // Both are plain app-router pages, so a typed URL renders them without any
    // in-app state transition.
    expect(routeExists(CENTRAL_ROUTE)).toBe(true);
    expect(routeExists(SPECIALISTS_ROUTE)).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Deferred domains
// ---------------------------------------------------------------------------

describe("deferred TON domains", () => {
  it("has no route for occurrences, reports or sources", () => {
    for (const segment of DEFERRED_SEGMENTS) {
      expect(routeExists(`/app/${segment}`)).toBe(false);
    }
  });

  it("shows no navigation entry for them, disabled or otherwise", () => {
    renderSidebar("pt");

    for (const href of screen
      .getAllByRole("link")
      .map((link) => link.getAttribute("href") ?? "")) {
      for (const segment of DEFERRED_SEGMENTS) {
        expect(href).not.toContain(segment);
      }
    }

    for (const label of [
      /ocorrênc/i,
      /occurrence/i,
      /relatório/i,
      /report/i,
      /em breve/i,
      /coming soon/i,
    ]) {
      expect(screen.queryByText(label)).toBeNull();
    }
  });

  it("names no deferred domain in the sidebar catalog", () => {
    for (const locale of LOCALES) {
      const catalog = JSON.stringify(
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        require(`@/i18n/messages/${locale}.json`).sidebar.appSidebar
      );
      for (const segment of DEFERRED_SEGMENTS) {
        expect(catalog).not.toContain(segment);
      }
    }
  });
});

// ---------------------------------------------------------------------------
// Conversation history
// ---------------------------------------------------------------------------

describe("conversation history", () => {
  it("stays usable, in a landmark of its own", () => {
    renderSidebar("pt");

    const history = historyNav("pt");
    expect(within(history).getByText("Conversas")).toBeVisible();

    const rows = within(history).getAllByTestId("ChatButton");
    expect(rows).toHaveLength(CHAT_SESSIONS.length);
    expect(rows[0]).toHaveAttribute("href", "/app?chatId=chat-1");
  });

  it("is not the product navigation", () => {
    renderSidebar();

    // No chat row may sit inside the product-navigation landmark.
    expect(within(productNav()).queryAllByTestId("ChatButton")).toHaveLength(0);
    // And Central must not live inside the history landmark.
    expect(
      within(historyNav()).queryByRole("link", { name: "Central" })
    ).toBeNull();
  });

  it("keeps its own empty state without inviting generic chatter", () => {
    chatSessions = [];
    renderSidebar("pt");

    const history = historyNav("pt");
    expect(within(history).queryAllByTestId("ChatButton")).toHaveLength(0);
    expect(
      within(history).getByText("Suas conversas aparecerão aqui.")
    ).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Reachability
// ---------------------------------------------------------------------------

describe("reachability", () => {
  it("pins the TON destinations outside the scrolling history area", () => {
    const { container } = renderSidebar();

    const header = container.querySelector(".opal-sidebar-header");
    const body = container.querySelector(".opal-sidebar-body");
    expect(header).not.toBeNull();
    expect(body).not.toBeNull();

    // History scrolls; the destinations do not scroll away with it.
    expect(header!.contains(productNav())).toBe(true);
    expect(body!.contains(historyNav())).toBe(true);
  });

  it("keeps both destinations reachable on a small viewport", () => {
    const originalWidth = window.innerWidth;
    try {
      Object.defineProperty(window, "innerWidth", {
        configurable: true,
        writable: true,
        value: 375,
      });
      renderSidebar();

      const links = within(productNav()).getAllByRole("link");
      expect(links.map((link) => link.getAttribute("href"))).toEqual([
        CENTRAL_ROUTE,
        SPECIALISTS_ROUTE,
      ]);
    } finally {
      Object.defineProperty(window, "innerWidth", {
        configurable: true,
        writable: true,
        value: originalWidth,
      });
    }
  });

  it("names every destination for assistive technology", () => {
    renderSidebar("pt");

    // Accessible names, not colour, carry the destination and the grouping.
    expect(productNav("pt")).toHaveAttribute("aria-label", "Navegação do TON");
    expect(historyNav("pt")).toHaveAttribute(
      "aria-label",
      "Histórico de conversas"
    );
    for (const name of ["Central", "Especialistas"]) {
      expect(
        within(productNav("pt")).getByRole("link", { name })
      ).toBeInTheDocument();
    }
  });
});

// ---------------------------------------------------------------------------
// FE-003 product surface stays sanitized
// ---------------------------------------------------------------------------

describe("FE-003 preservation", () => {
  it("keeps the builder product entry out, even when the flag is on", () => {
    // `useSettings` above reports `onyx_craft_enabled: true`; the TON policy
    // constant is what withholds the entry.
    renderSidebar();

    expect(screen.queryByTestId("AppSidebar/build")).toBeNull();
  });

  it("shows no commerce or upstream wording in the sidebar", () => {
    renderSidebar("pt");

    for (const phrase of [
      /powered by onyx/i,
      /upgrade/i,
      /billing/i,
      /plans? & billing/i,
      /trial/i,
      /discord/i,
      /docs\.onyx\.app/i,
    ]) {
      expect(screen.queryByText(phrase)).toBeNull();
    }
  });

  it("links to no upstream address", () => {
    renderSidebar();

    for (const link of screen.getAllByRole("link")) {
      const href = link.getAttribute("href") ?? "";
      expect(href).not.toMatch(/onyx\.app|discord\.gg/i);
    }
  });
});

// ---------------------------------------------------------------------------
// Permissions
// ---------------------------------------------------------------------------

describe("permissions", () => {
  it("hides the admin entry from a user without admin access", () => {
    // The mocked UserProvider reports `hasAdminAccess: false`.
    renderSidebar();

    expect(screen.queryByText("Admin Panel")).toBeNull();
  });

  it("keeps every admin route gated by its permission", () => {
    for (const route of Object.values(ADMIN_ROUTES)) {
      expect(route.requiredPermission).toBeDefined();
    }
    expect(ADMIN_ROUTES.GROUPS.requiredPermission).toBe(
      Permission.MANAGE_USER_GROUPS
    );
  });
});

// ---------------------------------------------------------------------------
// Plan 008a follow-up
// ---------------------------------------------------------------------------

describe("Groups navigation after Backend Plan 008a", () => {
  /** A no-license TON deployment: community tier, no subscription. */
  const COMMUNITY_FLAGS: FeatureFlags = {
    vectorDbEnabled: true,
    enableCloud: false,
    tier: Tier.COMMUNITY,
    customAnalyticsEnabled: false,
    hasSubscription: false,
    hooksEnabled: true,
    opensearchEnabled: true,
    queryHistoryEnabled: true,
    craftAvailable: true,
  };

  function groupsItem() {
    return buildItems(
      [Permission.FULL_ADMIN_PANEL_ACCESS],
      COMMUNITY_FLAGS,
      null
    ).find((item) => item.nameId === "groups");
  }

  it("stops mirroring the removed commercial gate", () => {
    expect(ADMIN_ROUTES.GROUPS.requiredTier).toBeNull();
    expect(groupsItem()?.disabled).toBe(false);
  });

  it("keeps the permission that actually decides access", () => {
    expect(ADMIN_ROUTES.GROUPS.requiredPermission).toBe(
      Permission.MANAGE_USER_GROUPS
    );
    expect(
      buildItems([], COMMUNITY_FLAGS, null).some(
        (item) => item.nameId === "groups"
      )
    ).toBe(false);
  });

  it("does not widen any other tier-gated admin entry", () => {
    const stillGated = buildItems(
      [Permission.FULL_ADMIN_PANEL_ACCESS],
      COMMUNITY_FLAGS,
      null
    ).filter((item) => item.disabled);

    expect(stillGated.length).toBeGreaterThan(0);
    expect(stillGated.map((item) => item.nameId)).not.toContain("groups");
    expect(ADMIN_ROUTES.API_KEYS.requiredTier).toBe(Tier.BUSINESS);
    expect(ADMIN_ROUTES.SCIM.requiredTier).toBe(Tier.ENTERPRISE);
  });
});

// ---------------------------------------------------------------------------
// Catalog contract
// ---------------------------------------------------------------------------

describe("navigation catalog", () => {
  it("names the TON destinations in every locale", () => {
    for (const locale of LOCALES) {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const sidebar = require(`@/i18n/messages/${locale}.json`).sidebar;

      expect(sidebar.appSidebar.newSession.label).toBe("Central");
      expect(sidebar.appSidebar.specialists.label).toBeTruthy();
      expect(sidebar.appSidebar.recents.title).toBeTruthy();
      expect(sidebar.appSidebar.productNav.ariaLabel).toBeTruthy();
      expect(sidebar.appSidebar.historyNav.ariaLabel).toBeTruthy();
      // The same destination is named once, in the sidebar and in the palette.
      expect(sidebar.chatSearch.newSession.label).toBe("Central");
    }
  });

  it("retires the agent-overflow wording it replaced", () => {
    for (const locale of LOCALES) {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const appSidebar = require(`@/i18n/messages/${locale}.json`).sidebar
        .appSidebar;

      expect(appSidebar.moreAgents).toBeUndefined();
      expect(appSidebar.exploreAgents).toBeUndefined();
    }
  });

  it("keeps the Portuguese product vocabulary", () => {
    const appSidebar = portugueseMessages.sidebar.appSidebar;

    expect(appSidebar.specialists.label).toBe("Especialistas");
    expect(appSidebar.recents.title).toBe("Conversas");
    expect(appSidebar.projects.title).toBe("Projetos");
  });
});
