"use client";

import useSWR from "swr";
import { errorHandlingFetcher } from "@/lib/fetcher";

export const TREATMENTS_API = "/api/ton/closing-treatments";

export type TreatmentStatus = "ACTIVE" | "BLOCKED" | "REVOKED";
export type TreatmentEffect = "EXCLUDE" | "RECLASSIFY" | "REPLACE_BY_SOURCE";

export interface TreatmentView {
  id: string;
  number: number;
  treatment_key: string;
  version: number;
  title: string;
  status: TreatmentStatus;
  effect: TreatmentEffect;
  account_id: string | null;
  account_label: string | null;
  unit_id: string | null;
  unit_name: string | null;
  period_from: string | null;
  period_to: string | null;
  target_account_id: string | null;
  target_account_label: string | null;
  required_source: string | null;
  justification: string;
  evidence: string;
  created_by_email: string | null;
  created_at: string;
  applied_fact_count: number | null;
}

export interface TreatmentOption {
  id: string;
  label: string;
}

export interface TreatmentTable {
  treatments: TreatmentView[];
  accounts: TreatmentOption[];
  units: TreatmentOption[];
  normalization_run_id: string | null;
  changes_since_calculation: number;
}

export interface TreatmentCreate {
  treatment_key: string;
  title: string;
  status: TreatmentStatus;
  effect: TreatmentEffect;
  account_id: string | null;
  unit_id: string | null;
  period_from: string | null;
  period_to: string | null;
  target_account_id: string | null;
  required_source: string | null;
  justification: string;
  evidence: string;
}

export function useTreatmentTable(enabled: boolean) {
  return useSWR<TreatmentTable>(
    enabled ? TREATMENTS_API : null,
    errorHandlingFetcher
  );
}

export function useTreatmentHistory(key: string | null) {
  return useSWR<TreatmentView[]>(
    key ? `${TREATMENTS_API}/${encodeURIComponent(key)}/history` : null,
    errorHandlingFetcher
  );
}

/** "Parcelamentos: só a parcela paga" -> "parcelamentos-so-a-parcela-paga". */
export function treatmentKey(title: string): string {
  return title
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 100);
}

/** "2026-04-01" -> "04/2026". */
export function monthLabel(value: string): string {
  const [year, month] = value.split("-");
  return `${month}/${year}`;
}

export function periodLabel(treatment: TreatmentView): string {
  const { period_from: from, period_to: to } = treatment;
  if (from && to)
    return from === to
      ? monthLabel(from)
      : `${monthLabel(from)} a ${monthLabel(to)}`;
  if (from) return `a partir de ${monthLabel(from)}`;
  if (to) return `até ${monthLabel(to)}`;
  return "todos os meses";
}

export function asRequest(
  treatment: TreatmentView,
  changes: Partial<TreatmentCreate>
): TreatmentCreate {
  return {
    treatment_key: treatment.treatment_key,
    title: treatment.title,
    status: treatment.status,
    effect: treatment.effect,
    account_id: treatment.account_id,
    unit_id: treatment.unit_id,
    period_from: treatment.period_from,
    period_to: treatment.period_to,
    target_account_id: treatment.target_account_id,
    required_source: treatment.required_source,
    justification: treatment.justification,
    evidence: treatment.evidence,
    ...changes,
  };
}

export const TREATMENTS_COPY = {
  adminEntry: {
    title: "Tratamentos de fechamento",
    description:
      "Regras da Controladoria que mudam a DRE, com justificativa e versão.",
    status: (active: number, blocked: number) =>
      blocked
        ? `${active} aplicados · ${blocked} aguardando fonte`
        : `${active} aplicados`,
  },
  back: "Administração",
  eyebrow: "Administração",
  title: "Tratamentos de fechamento",
  description:
    "Regras decididas pela Controladoria que mudam a DRE. Cada mudança vira uma versão nova, com justificativa e evidência, e o valor do NG continua visível.",
  create: "Novo tratamento",
  loading: "Carregando tratamentos…",
  empty:
    "Nenhum tratamento registrado. A DRE usa os valores como lançados no NG.",
  noAccessTitle: "Acesso restrito",
  noAccessDescription:
    "Tratamentos de fechamento são registrados pela Controladoria (administradores do TON).",
  columns: {
    title: "Tratamento",
    nature: "Natureza",
    effect: "Efeito",
    status: "Situação",
    applied: "Lançamentos",
    version: "Versão",
  },
  effect: {
    EXCLUDE: "Fora do resultado",
    RECLASSIFY: "Mover para outra natureza",
    REPLACE_BY_SOURCE: "Substituir por outra fonte",
  } satisfies Record<TreatmentEffect, string>,
  effectHelp: {
    EXCLUDE:
      "Os lançamentos continuam na base, mas entram com valor zero na DRE.",
    RECLASSIFY: "Os lançamentos passam a somar na natureza de destino.",
    REPLACE_BY_SOURCE:
      "O valor virá de outra fonte (por exemplo, a data de pagamento das parcelas). Fica aguardando até a fonte existir.",
  } satisfies Record<TreatmentEffect, string>,
  status: {
    ACTIVE: "Aplicado",
    BLOCKED: (source: string | null) =>
      source ? `Aguardando: ${source}` : "Aguardando fonte",
    REVOKED: "Revogado",
  },
  notInBase: "Ainda não recalculado",
  detail: {
    justification: "Justificativa",
    evidence: "Evidência da decisão",
    scope: "Escopo",
    allUnits: "todas as unidades",
    author: (who: string | null, when: string) =>
      `Registrado por ${who ?? "—"} em ${when}`,
    history: "Histórico",
    newVersion: "Nova versão",
    revoke: "Revogar",
    revokeReason: "Por que revogar",
    confirmRevoke: "Confirmar revogação",
  },
  dialog: {
    createTitle: "Novo tratamento",
    versionTitle: (title: string) => `Nova versão · ${title}`,
    intro:
      "O tratamento só muda a DRE depois que a base for atualizada. Nada é apagado: a versão anterior continua no histórico.",
    title: "Título",
    titlePlaceholder: "Ex.: Mútuos fora do resultado",
    nature: "Natureza afetada",
    effect: "Efeito",
    target: "Natureza de destino",
    unit: "Unidade/filial (opcional)",
    period: "Período (opcional)",
    from: "De",
    to: "Até",
    apply: "Quando aplicar",
    applyNow: "Aplicar na próxima atualização da base",
    applyBlocked: "Aguardar uma fonte que ainda não existe",
    requiredSource: "Fonte que falta",
    requiredSourcePlaceholder: "Ex.: data de pagamento das parcelas no NG",
    justification: "Justificativa",
    evidence: "Evidência da decisão",
    evidencePlaceholder: "Ex.: ata da reunião de 06/10/2026, item D2",
    any: "Todas",
    save: "Registrar",
    cancel: "Cancelar",
    saving: "Salvando…",
    failed: "Não foi possível registrar. Confira os campos e tente novamente.",
  },
  saved: (title: string) =>
    `Tratamento "${title}" registrado. Atualize a base para aplicar.`,
  revoked: (title: string) => `Tratamento "${title}" revogado.`,
  recompute: {
    text: (count: number) =>
      count === 1
        ? "1 mudança ainda não está na DRE."
        : `${count} mudanças ainda não estão na DRE.`,
    action: "Atualizar a base",
    running: "Atualizando…",
    done: "Base atualizada; recalcule a DRE.",
    failed: "Não foi possível atualizar a base.",
  },
};
