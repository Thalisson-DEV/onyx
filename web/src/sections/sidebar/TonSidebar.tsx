"use client";

import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { SidebarLayouts } from "@opal/layouts";
import { SidebarTab } from "@opal/components";
import {
  SvgBubbleText,
  SvgBarChart,
  SvgUploadCloud,
  SvgClipboard,
  SvgShield,
  SvgManageAgent,
  SvgSliders,
  SvgFileText,
  SvgBookOpen,
  SvgSettings,
} from "@opal/icons";
import { useUser } from "@/providers/UserProvider";
import { getFirstPermittedAdminRoute } from "@/lib/permissions";
import AccountPopover from "@/sections/sidebar/AccountPopover";
import { renderSidebarLogo } from "@/lib/sidebar/utils";
import { useShowLogoWhenFolded } from "@/lib/sidebar/hooks";
import useChatSessions from "@/hooks/useChatSessions";
import ChatButton from "@/sections/sidebar/ChatButton";

export default function TonSidebar() {
  const t = useTranslations("tonNavigation");
  const pathname = usePathname();
  const { chatSessions } = useChatSessions();
  const showLogoWhenFolded = useShowLogoWhenFolded();
  const { hasAdminAccess, adminCapabilities } = useUser();

  const navItems = [
    {
      href: "/ton/controladoria",
      label: t("central"),
      icon: SvgBarChart,
      selected: pathname === "/ton/controladoria",
    },
    {
      href: "/ton/chat",
      label: t("chat"),
      icon: SvgBubbleText,
      selected: pathname.startsWith("/ton/chat"),
    },
    {
      href: "/ton/data-sources",
      label: t("sources"),
      icon: SvgUploadCloud,
      selected: pathname.startsWith("/ton/data-sources"),
    },
    {
      href: "/ton/dre",
      label: t("dre"),
      icon: SvgClipboard,
      selected:
        pathname.startsWith("/ton/dre") || pathname.startsWith("/admin/dre"),
    },
    {
      href: "/ton/pendencias",
      label: t("readiness"),
      icon: SvgShield,
      selected:
        pathname.startsWith("/ton/pendencias") ||
        pathname.startsWith("/admin/financial-readiness"),
    },
    {
      href: "/ton/especialistas",
      label: t("specialists"),
      icon: SvgManageAgent,
      selected: pathname.startsWith("/ton/especialistas"),
    },
    {
      href: "/ton/rotinas",
      label: t("routines"),
      icon: SvgSliders,
      selected: pathname.startsWith("/ton/rotinas"),
    },
    {
      href: "/ton/relatorios",
      label: t("reports"),
      icon: SvgFileText,
      selected:
        pathname.startsWith("/ton/relatorios") ||
        pathname.startsWith("/ton/controladoria/reports"),
    },
    {
      href: "/ton/cobertura",
      label: t("coverage"),
      icon: SvgBookOpen,
      selected: pathname.startsWith("/ton/cobertura"),
    },
  ];

  const adminRoute = hasAdminAccess
    ? getFirstPermittedAdminRoute(adminCapabilities) || "/admin/language-models"
    : null;

  return (
    <SidebarLayouts.Root foldable>
      <SidebarLayouts.Header
        showLogoWhenFolded={showLogoWhenFolded}
        renderAppLogo={renderSidebarLogo}
      >
        <nav aria-label={t("navigation")} className="flex flex-col gap-0.5">
          {navItems.map((item) => (
            <SidebarTab
              key={item.href}
              icon={item.icon}
              href={item.href}
              selected={item.selected}
            >
              {item.label}
            </SidebarTab>
          ))}
        </nav>
      </SidebarLayouts.Header>

      <SidebarLayouts.Body scrollKey="ton-sidebar">
        {pathname.startsWith("/ton/chat") && (
          <SidebarLayouts.Section title={t("history")}>
            {chatSessions.map((session) => (
              <ChatButton key={session.id} chatSession={session} />
            ))}
          </SidebarLayouts.Section>
        )}
      </SidebarLayouts.Body>

      <div className="p-2 border-t border-01 flex flex-col gap-1">
        {adminRoute && (
          <SidebarTab icon={SvgSettings} href={adminRoute}>
            {t("admin")}
          </SidebarTab>
        )}
        <AccountPopover />
      </div>
    </SidebarLayouts.Root>
  );
}
