/**
 * TON client-surface policy.
 *
 * TON is one dedicated internal product for Vale Norte. The upstream code base
 * also ships a generic SaaS presentation: upstream attribution, plans, billing,
 * trials, upgrade navigation, community/support links and a separate builder
 * product concept. None of that belongs in the TON client experience.
 *
 * These flags remove that *presentation* only. They never change
 * authorization. Every route keeps its permission, capability and tier gate,
 * and every underlying service stays wired. Hiding a link is not a security
 * control: direct-route enforcement stays the backend's responsibility
 * (Backend Plan 008).
 *
 * The values are product decisions, not deployment toggles. They are plain
 * constants on purpose: a `process.env` read would resolve to `undefined` in
 * the client bundle unless it were `NEXT_PUBLIC_`, which would make the policy
 * differ between server and client render. Flip a flag here to restore the
 * corresponding upstream surface.
 */

/** Upstream product attribution, for example the "Powered by Onyx" tagline. */
export const SHOW_UPSTREAM_ATTRIBUTION = false;

/**
 * Upstream websites: documentation, changelog, community and support links.
 * Operator-facing provider and connector documentation is out of scope here;
 * those links are configuration help, not product marketing.
 */
export const SHOW_UPSTREAM_LINKS = false;

/**
 * Plans, pricing, subscriptions, trials, checkout, payment reminders and
 * upgrade navigation. The tier and license mechanism itself stays intact,
 * because runtime capability checks read it.
 */
export const SHOW_COMMERCE_SURFACES = false;

/**
 * The separate builder product concept in normal-user navigation. The routes,
 * the admin configuration pages and the backend capability all stay in place.
 */
export const SHOW_BUILDER_PRODUCT_ENTRY = false;
