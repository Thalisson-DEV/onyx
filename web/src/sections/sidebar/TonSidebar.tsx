"use client";

import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { SidebarLayouts, useSidebarState } from "@opal/layouts";
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

export default function TonSidebar() {
  const t = useTranslations("sidebar");
  const pathname = usePathname();
  const { folded } = useSidebarState();
  const showLogoWhenFolded = useShowLogoWhenFolded();
  const { hasAdminAccess, adminCapabilities } = useUser();

  const navItems = [
    {
      href: "/app",
      label: "Central",
      icon: SvgBubbleText,
      selected: pathname === "/app" || pathname === "/chat",
    },
    {
      href: "/ton/controladoria",
      label: "Controladoria",
      icon: SvgBarChart,
      selected: pathname === "/ton/controladoria",
    },
    {
      href: "/ton/data-sources",
      label: "Fontes de dados",
      icon: SvgUploadCloud,
      selected: pathname.startsWith("/ton/data-sources"),
    },
    {
      href: "/ton/dre",
      label: "DRE",
      icon: SvgClipboard,
      selected: pathname.startsWith("/ton/dre") || pathname.startsWith("/admin/dre"),
    },
    {
      href: "/ton/pendencias",
      label: "Pendências",
      icon: SvgShield,
      selected: pathname.startsWith("/ton/pendencias") || pathname.startsWith("/admin/financial-readiness"),
    },
    {
      href: "/ton/especialistas",
      label: "Especialistas",
      icon: SvgManageAgent,
      selected: pathname.startsWith("/ton/especialistas"),
    },
    {
      href: "/ton/rotinas",
      label: "Rotinas",
      icon: SvgSliders,
      selected: pathname.startsWith("/ton/rotinas"),
    },
    {
      href: "/ton/relatorios",
      label: "Relatórios",
      icon: SvgFileText,
      selected: pathname.startsWith("/ton/relatorios") || pathname.startsWith("/ton/controladoria/reports"),
    },
    {
      href: "/ton/cobertura",
      label: "Cobertura do TON",
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
        <nav aria-label="Navegação do TON" className="flex flex-col gap-0.5">
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
        <div className="flex-1" />
      </SidebarLayouts.Body>

      <div className="p-2 border-t border-01 flex flex-col gap-1">
        {adminRoute && (
          <SidebarTab icon={SvgSettings} href={adminRoute}>
            Painel de administração
          </SidebarTab>
        )}
        <AccountPopover />
      </div>
    </SidebarLayouts.Root>
  );
}
