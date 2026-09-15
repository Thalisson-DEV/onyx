/**
 * @jest-environment jsdom
 *
 * TON-FE-003 product-surface contract.
 *
 * A normal Vale Norte user must not meet upstream attribution, upstream links,
 * or plan/billing/trial surfaces. An administrator must keep the operational
 * configuration TON needs, and every underlying capability must stay wired.
 */
import fs from "node:fs";
import path from "node:path";
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import englishMessages from "@/i18n/messages/en.json";
import portugueseMessages from "@/i18n/messages/pt.json";
import { Logo } from "@/lib/app/components";
import { ADMIN_ROUTES, type FeatureFlags } from "@/lib/admin-routes";
import { buildItems } from "@/lib/admin-sidebar-utils";
import { Permission } from "@/lib/types";
import { Tier } from "@/lib/settings/types";
import {
  SHOW_BUILDER_PRODUCT_ENTRY,
  SHOW_COMMERCE_SURFACES,
  SHOW_UPSTREAM_ATTRIBUTION,
  SHOW_UPSTREAM_LINKS,
} from "@/lib/ton/product-surface";

const WEB_ROOT = path.resolve(__dirname, "../..");

function readSource(relativePath: string): string {
  return fs.readFileSync(path.join(WEB_ROOT, relativePath), "utf8");
}

jest.mock("@/lib/settings/hooks", () => ({
  useSettings: () => ({
    appName: "TON",
    enterprise: null,
    logoUrl: null,
    version: "0.0.0-dev",
  }),
}));

/** Paid tier and an active subscription — the most permissive commerce state. */
const PAID_FLAGS: FeatureFlags = {
  vectorDbEnabled: true,
  enableCloud: false,
  tier: Tier.ENTERPRISE,
  customAnalyticsEnabled: false,
  hasSubscription: true,
  hooksEnabled: true,
  opensearchEnabled: true,
  queryHistoryEnabled: true,
  craftAvailable: true,
};

/** No subscription — the state that used to add the "Upgrade Plan" entry. */
const UNPAID_FLAGS: FeatureFlags = {
  ...PAID_FLAGS,
  tier: Tier.COMMUNITY,
  hasSubscription: false,
};

const ADMIN_PERMISSIONS = [Permission.FULL_ADMIN_PANEL_ACCESS];

function adminNavIds(flags: FeatureFlags): string[] {
  return buildItems(ADMIN_PERMISSIONS, flags, null).map((item) => item.nameId);
}

describe("TON product-surface policy", () => {
  it("withholds every upstream and commerce surface", () => {
    expect(SHOW_UPSTREAM_ATTRIBUTION).toBe(false);
    expect(SHOW_UPSTREAM_LINKS).toBe(false);
    expect(SHOW_COMMERCE_SURFACES).toBe(false);
    expect(SHOW_BUILDER_PRODUCT_ENTRY).toBe(false);
  });
});

describe("normal user", () => {
  it("sees the product name without upstream attribution", () => {
    render(
      <NextIntlClientProvider locale="en" messages={englishMessages}>
        <Logo />
      </NextIntlClientProvider>
    );

    expect(screen.getAllByText("TON")[0]).toBeVisible();
    expect(screen.queryByText(/powered by onyx/i)).toBeNull();
  });

  it("gets a product footer built from the existing version, not a slogan", () => {
    const hooks = readSource("src/lib/app/hooks.ts");

    expect(hooks).not.toContain("APP_SLOGAN");
    expect(hooks).not.toContain("onyx.app");
    expect(hooks).toContain('t("footer.text"');
    // Reuses the settings version; no separate versioning system.
    expect(hooks).toContain("settings.version");
    expect(readSource("src/lib/constants.ts")).not.toContain("APP_SLOGAN");
  });

  it("has no open-source, plan or upstream wording in the footer and login copy", () => {
    for (const messages of [englishMessages, portugueseMessages]) {
      expect(messages.product.footer.text).not.toMatch(/onyx|open source/i);
      expect(messages.product.version.label).not.toMatch(/onyx/i);
      expect(messages.auth.login.welcomeSubtitle.text).not.toMatch(
        /onyx|open source|código aberto/i
      );
    }
  });

  it("is not asked for generic platform setup: only an admin sees provider onboarding", () => {
    const flow = readSource("src/sections/onboarding/OnboardingFlow.tsx");

    // The provider steps hang off the isAdmin branch; a normal user only ever
    // reaches NonAdminStep, which asks for a display name.
    expect(flow).toContain("return isAdmin ? (");
    expect(flow).toContain("<NonAdminStep />");
    expect(englishMessages.onboarding.nameStep.title).not.toMatch(/onyx/i);
    expect(englishMessages.onboarding.llmStep.description).not.toMatch(
      /onyx|self-hosted/i
    );
  });

  it("has no upstream support or community link in the toast appendix", () => {
    const provider = readSource("src/providers/AppProvider.tsx");

    expect(provider).toContain("SHOW_UPSTREAM_LINKS &&");
    expect(provider).not.toMatch(/errorAppendix=\{\s*NEXT_PUBLIC_/);
  });

  it("keeps upstream links out of the account menu and error pages", () => {
    const popover = readSource("src/sections/sidebar/AccountPopover.tsx");
    const errorPage = readSource("src/components/errorPages/ErrorPage.tsx");
    const restricted = readSource(
      "src/components/errorPages/AccessRestrictedPage.tsx"
    );

    for (const source of [popover, errorPage, restricted]) {
      expect(source).toContain("SHOW_UPSTREAM_LINKS");
    }
    // The error page hero uses the configurable product identity.
    expect(
      readSource("src/components/errorPages/ErrorPageLayout.tsx")
    ).toContain("<Logo size={32} />");
  });

  it("shows no plan, billing, trial or upgrade navigation", () => {
    expect(adminNavIds(UNPAID_FLAGS)).not.toContain("upgradePlan");
    expect(adminNavIds(PAID_FLAGS)).not.toContain("upgradePlan");
    expect(adminNavIds(PAID_FLAGS)).not.toContain("plansAndBilling");
    expect(ADMIN_ROUTES.BILLING.visibleWhen?.(PAID_FLAGS)).toBe(false);

    const adminChrome = readSource("src/layouts/chromes/AdminChrome.tsx");
    expect(adminChrome).toContain("SHOW_COMMERCE_SURFACES &&");
  });

  it("does not meet the builder as a product concept in the app sidebar", () => {
    const sidebar = readSource("src/sections/sidebar/AppSidebar.tsx");
    expect(sidebar).toContain("SHOW_BUILDER_PRODUCT_ENTRY &&");
  });
});

describe("administrator", () => {
  it("keeps the configuration TON needs to run", () => {
    const ids = adminNavIds(PAID_FLAGS);

    for (const required of [
      "languageModels",
      "users",
      "groups",
      "agents",
      "existingConnectors",
      "addConnector",
      "documentSets",
      "indexSettings",
      "securityAndHardening",
      "ssoProviders",
      "mcpActions",
      "openapiActions",
      "chatPreferences",
      "webSearch",
    ]) {
      expect(ids).toContain(required);
    }
  });

  it("keeps every admin route reachable, including the ones off the sidebar", () => {
    // Hiding the entry must not delete the route: the permission gate and
    // `matchAdminRoute` still resolve it for an authorised operator.
    expect(ADMIN_ROUTES.BILLING.path).toBe("/admin/billing");
    expect(ADMIN_ROUTES.BILLING.requiredPermission).toBe(
      Permission.FULL_ADMIN_PANEL_ACCESS
    );
    expect(ADMIN_ROUTES.CRAFT_ACCESS.path).toBe("/admin/craft/access");
    expect(ADMIN_ROUTES.CRAFT_PREFERENCES.visibleWhen?.(PAID_FLAGS)).toBe(true);
  });

  it("keeps the tier mechanism intact behind the neutral wording", () => {
    // Runtime capability checks read the tier, so only the upsell copy changed.
    expect(ADMIN_ROUTES.GROUPS.requiredTier).toBe(Tier.BUSINESS);
    expect(ADMIN_ROUTES.SCIM.requiredTier).toBe(Tier.ENTERPRISE);

    const disabled = buildItems(ADMIN_PERMISSIONS, UNPAID_FLAGS, null).filter(
      (item) => item.disabled
    );
    expect(disabled.length).toBeGreaterThan(0);
    expect(disabled.map((item) => item.requiredTier)).toContain(Tier.BUSINESS);

    const sidebar = readSource("src/sections/sidebar/AdminSidebar.tsx");
    expect(sidebar).toContain("capabilityUnavailable");
    expect(
      englishMessages.sidebar.adminSidebar.capabilityUnavailable.tooltip
    ).not.toMatch(/onyx|plan|billing|upgrade/i);
  });
});
