"use client";

import useSWR from "swr";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { TonApiError } from "@/lib/ton/decisions";

export const TEAM_API = "/api/ton/team";

export type TeamProfile = "ADMIN" | "MANAGER";

export interface TeamMember {
  id: string;
  email: string;
  name: string | null;
  /** null: an account with no TON access yet. */
  profile: TeamProfile | null;
  unit_ids: string[];
  active: boolean;
  /** No password chosen yet: the first-access link was not used. */
  pending_first_access: boolean;
  is_you: boolean;
}

export interface TeamAccessLink {
  member: TeamMember;
  link: string;
  expires_at: string;
}

export interface TeamUnit {
  id: string;
  code: string;
  name?: string;
  kind?: string;
}

export const TEAM_COPY = {
  adminEntry: {
    title: "Usuários e acessos",
    description:
      "Cadastre quem usa o TON, defina se é administrador ou gestor de unidade e gere o link de primeiro acesso.",
    status: (count: number) =>
      count === 1 ? "1 usuário ativo" : `${count} usuários ativos`,
  },
  eyebrow: "Administração",
  title: "Usuários e acessos",
  description:
    "Quem usa o TON e o que cada pessoa vê. A senha é sempre criada pela própria pessoa, pelo link de primeiro acesso.",
  create: "Novo usuário",
  empty: "Nenhum usuário cadastrado.",
  failedLoad: "Não foi possível carregar os usuários.",
  columns: {
    person: "Pessoa",
    profile: "Perfil",
    units: "Unidades",
    status: "Situação",
    actions: "Ações",
  },
  profile: {
    ADMIN: "Administrador",
    MANAGER: "Gestor de unidade",
    none: "Sem acesso ao TON",
  } as const,
  profileHint: {
    ADMIN:
      "Vê todas as unidades e o consolidado, fecha a DRE, importa fontes e gerencia usuários.",
    MANAGER:
      "Consulta a DRE, os lançamentos e o assistente das unidades escolhidas e envia as contas a pagar delas.",
  } as const,
  allUnits: "Todas",
  unitsCount: (count: number) =>
    count === 1 ? "1 unidade" : `${count} unidades`,
  status: {
    active: "Ativo",
    pending: "Aguardando primeiro acesso",
    inactive: "Desativado",
  },
  you: "você",
  actions: {
    edit: "Alterar acesso",
    link: "Gerar link de acesso",
    deactivate: "Desativar",
    reactivate: "Reativar",
  },
  dialog: {
    createTitle: "Novo usuário",
    editTitle: (who: string) => `Acesso de ${who}`,
    intro:
      "Ao salvar, o TON gera um link para a pessoa criar a própria senha. Envie o link a ela.",
    name: "Nome",
    namePlaceholder: "Nome e sobrenome",
    email: "E-mail",
    emailPlaceholder: "nome@empresa.com.br",
    profile: "Perfil",
    units: "Unidades que a pessoa vê",
    operational: (count: number) => `Operacionais ativas (${count})`,
    clear: "Limpar",
    unitsNeeded: "Escolha ao menos uma unidade.",
    cancel: "Cancelar",
    save: "Salvar",
    createSave: "Criar e gerar link",
    saving: "Salvando…",
    failed: "Não foi possível salvar. Tente novamente.",
  },
  linkDialog: {
    title: (who: string) => `Link de acesso de ${who}`,
    intro:
      "Envie este link para a pessoa. Ao abrir, ela cria a própria senha e entra no TON.",
    expires: (date: string) =>
      `Vale até ${date}. Depois que a senha for criada, o link deixa de funcionar.`,
    copyLink: "Copiar link",
    copyMessage: "Copiar mensagem",
    copied: "Copiado",
    message: (name: string, link: string) =>
      `Olá${name ? `, ${name}` : ""}! Seu acesso ao TON está liberado. Abra o link abaixo para criar sua senha:\n${link}`,
    close: "Fechar",
  },
  confirmDeactivate: (who: string) =>
    `Desativar ${who}? A pessoa deixa de entrar no TON; o histórico fica guardado.`,
  confirm: "Confirmar",
  cancel: "Cancelar",
  actionFailed: "Não foi possível concluir. Tente novamente.",
  noAccessTitle: "Área do administrador",
  noAccessDescription: "Somente administradores do TON gerenciam usuários.",
};

/** The person as the table names them: name, else e-mail. */
export function memberName(member: TeamMember): string {
  return member.name?.trim() || member.email;
}

export function useTeam(enabled: boolean) {
  return useSWR<TeamMember[]>(enabled ? TEAM_API : null, errorHandlingFetcher);
}

export function useTeamUnits(enabled: boolean) {
  return useSWR<TeamUnit[]>(
    enabled
      ? "/api/ton/financial-domain/units?limit=100&active_only=true"
      : null,
    errorHandlingFetcher
  );
}

export async function sendTeamJson<T>(
  method: "POST" | "PUT",
  path: string,
  body: Record<string, unknown>
): Promise<T> {
  const response = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    const detail =
      payload && typeof payload === "object" && "detail" in payload
        ? payload.detail
        : null;
    throw new TonApiError(
      response.status,
      typeof detail === "string" ? detail : null
    );
  }
  // SAFETY: TON endpoints return the declared Pydantic view on 2xx.
  return (await response.json()) as T;
}
