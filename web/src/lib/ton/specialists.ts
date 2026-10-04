import {
  SvgActivitySmall,
  SvgBarChartSmall,
  SvgCartSmall,
  SvgFileSmall,
  SvgSearchSmall,
  SvgShieldSmall,
  SvgSlidersSmall,
  SvgTruckSmall,
  SvgUsersSmall,
} from "@opal/icons";
import type { IconFunctionComponent } from "@opal/types";

/**
 * Visual identity of each TON specialist, in the same avatar language Onyx
 * uses for agents: a small stroked glyph with its own color inside a rounded
 * square. The backend owns status and what each one did; this only names and
 * draws them.
 */
export interface SpecialistIdentity {
  /** Short name shown next to the avatar. */
  name: string;
  /** What the specialist looks at, in one line. */
  role: string;
  Icon: IconFunctionComponent;
  /** Stroke token for the glyph. */
  iconClassName: string;
}

export const SPECIALISTS: Record<string, SpecialistIdentity> = {
  CFO: {
    name: "CFO",
    role: "Finanças, prontidão e conciliação",
    Icon: SvgBarChartSmall,
    iconClassName: "stroke-theme-primary-05",
  },
  AUDITOR: {
    name: "Auditor",
    role: "Revisão da base e evidências",
    Icon: SvgSearchSmall,
    iconClassName: "stroke-theme-blue-05",
  },
  CEO: {
    name: "CEO",
    role: "Síntese executiva",
    Icon: SvgActivitySmall,
    iconClassName: "stroke-theme-purple-05",
  },
  COO: {
    name: "COO",
    role: "Operação e produção",
    Icon: SvgSlidersSmall,
    iconClassName: "stroke-theme-orange-04",
  },
  FLEET: {
    name: "Frota",
    role: "Frota e abastecimento",
    Icon: SvgTruckSmall,
    iconClassName: "stroke-theme-amber-04",
  },
  CONTRACTS: {
    name: "Contratos",
    role: "Cadastro mestre e aditivos",
    Icon: SvgFileSmall,
    iconClassName: "stroke-theme-purple-05",
  },
  COMPLIANCE: {
    name: "Compliance",
    role: "Obrigações legais e regulatórias",
    Icon: SvgShieldSmall,
    iconClassName: "stroke-theme-blue-05",
  },
  PROCUREMENT: {
    name: "Compras/Suprimentos",
    role: "Compras e fornecedores",
    Icon: SvgCartSmall,
    iconClassName: "stroke-theme-orange-04",
  },
  HR: {
    name: "RH",
    role: "Folha e pessoal",
    Icon: SvgUsersSmall,
    iconClassName: "stroke-theme-amber-04",
  },
};

/** Specialist keys the backend has used for the same role. */
const ALIASES: Record<string, string> = {
  FROTA: "FLEET",
  CONTRATOS: "CONTRACTS",
  RH: "HR",
};

export function specialistIdentity(
  key: string,
  fallbackName?: string | null
): SpecialistIdentity {
  const upper = key.toUpperCase();
  const known = SPECIALISTS[ALIASES[upper] ?? upper];
  if (known) return known;
  return {
    name: (fallbackName ?? key).replace(/^TON\s+/i, ""),
    role: "",
    Icon: SvgActivitySmall,
    iconClassName: "stroke-text-03",
  };
}
