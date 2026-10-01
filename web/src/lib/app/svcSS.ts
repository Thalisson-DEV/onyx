import type { Metadata } from "next";
import { SERVER_SIDE_ONLY__PAID_ENTERPRISE_FEATURES_ENABLED } from "@/lib/constants";
import { fetchEnterpriseSettingsSS } from "@/lib/settings/svcSS";

async function fetchAppName(): Promise<string> {
  if (SERVER_SIDE_ONLY__PAID_ENTERPRISE_FEATURES_ENABLED) {
    const enterprise = await fetchEnterpriseSettingsSS();
    if (enterprise?.application_name?.trim()) {
      return enterprise.application_name.trim();
    }
  }
  return "Onyx";
}

export async function generateFaviconMetadata(): Promise<Metadata["icons"]> {
  // TON product mark (Vale Norte); a custom enterprise logo still wins.
  let iconSrc = "/ton/favicon.png";

  if (SERVER_SIDE_ONLY__PAID_ENTERPRISE_FEATURES_ENABLED) {
    const enterprise = await fetchEnterpriseSettingsSS();
    if (enterprise?.use_custom_logo) {
      iconSrc = "/api/enterprise-settings/logo";
    }
  }

  return { icon: iconSrc, apple: "/ton/apple-touch-icon.png" };
}

export async function generateAdminTitleMetadata(): Promise<Metadata["title"]> {
  return `Admin — ${await fetchAppName()}`;
}
