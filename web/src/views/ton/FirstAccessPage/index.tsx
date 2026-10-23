"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { Button, InputTypeIn, Text } from "@opal/components";
import AuthFlowContainer from "@/components/auth/AuthFlowContainer";

const MIN_LENGTH = 8;

const T = {
  title: "Crie sua senha",
  doneTitle: "Tudo pronto",
  intro:
    "Seu acesso ao TON foi liberado pelo administrador. Escolha uma senha para entrar.",
  password: "Senha",
  confirm: "Repita a senha",
  minLength: `Use ao menos ${MIN_LENGTH} caracteres.`,
  mismatch: "As senhas não são iguais.",
  save: "Criar senha",
  saving: "Salvando…",
  done: "Senha criada. Agora é só entrar com seu e-mail e a senha nova.",
  login: "Entrar no TON",
  missing:
    "Este link está incompleto. Peça um novo link ao administrador do TON.",
  invalid:
    "Este link expirou ou já foi usado. Peça um novo link ao administrador do TON.",
  failed: "Não foi possível criar a senha. Tente novamente.",
};

/** The reason the password rules give, in Portuguese. */
function passwordReason(reason: string): string {
  const length = /at least (\d+) characters/.exec(reason);
  if (length) return `A senha precisa ter ao menos ${length[1]} caracteres.`;
  const maximum = /not exceed (\d+) characters/.exec(reason);
  if (maximum) return `A senha pode ter no máximo ${maximum[1]} caracteres.`;
  if (/uppercase/.test(reason)) return "Inclua ao menos uma letra maiúscula.";
  if (/lowercase/.test(reason)) return "Inclua ao menos uma letra minúscula.";
  if (/number/.test(reason)) return "Inclua ao menos um número.";
  if (/special character/.test(reason))
    return "Inclua ao menos um caractere especial (ex.: ! @ # $).";
  return T.failed;
}

/**
 * First access of a person the TON administrator registered: the link carries
 * a one-time token and the person chooses their own password here.
 */
export default function FirstAccessPage() {
  const token = useSearchParams()?.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(token ? null : T.missing);
  const [done, setDone] = useState(false);

  const tooShort = password.length > 0 && password.length < MIN_LENGTH;
  const mismatch = confirm.length > 0 && confirm !== password;
  const ready =
    !!token && password.length >= MIN_LENGTH && password === confirm;

  async function save() {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch("/api/auth/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password }),
      });
      if (response.ok) {
        setDone(true);
        return;
      }
      const payload: unknown = await response.json().catch(() => null);
      const detail =
        payload && typeof payload === "object" && "detail" in payload
          ? payload.detail
          : null;
      if (
        detail &&
        typeof detail === "object" &&
        "reason" in detail &&
        typeof detail.reason === "string"
      ) {
        setError(passwordReason(detail.reason));
      } else if (detail === "RESET_PASSWORD_BAD_TOKEN") {
        setError(T.invalid);
      } else {
        setError(T.failed);
      }
    } catch {
      setError(T.failed);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthFlowContainer>
      <div className="w-full flex flex-col gap-5">
        <div className="flex flex-col gap-1">
          <Text as="h1" font="heading-h2" color="text-05">
            {done ? T.doneTitle : T.title}
          </Text>
          <Text as="p" font="main-ui-body" color="text-03">
            {done ? T.done : T.intro}
          </Text>
        </div>
        {done ? (
          <Button href="/auth/login" width="full">
            {T.login}
          </Button>
        ) : (
          <form
            className="w-full flex flex-col gap-4"
            onSubmit={(event) => {
              event.preventDefault();
              if (ready && !busy) void save();
            }}
          >
            <label className="w-full flex flex-col gap-1.5">
              <Text font="secondary-action" color="text-04">
                {T.password}
              </Text>
              <InputTypeIn
                type="password"
                autoComplete="new-password"
                value={password}
                aria-label={T.password}
                onChange={(event) => setPassword(event.target.value)}
              />
              <Text font="secondary-body" color="text-03">
                {T.minLength}
              </Text>
            </label>
            <label className="w-full flex flex-col gap-1.5">
              <Text font="secondary-action" color="text-04">
                {T.confirm}
              </Text>
              <InputTypeIn
                type="password"
                autoComplete="new-password"
                value={confirm}
                aria-label={T.confirm}
                onChange={(event) => setConfirm(event.target.value)}
              />
              {mismatch && (
                <Text font="secondary-body" color="text-05">
                  {T.mismatch}
                </Text>
              )}
            </label>
            {error && (
              <Text as="p" font="secondary-body" color="text-05" role="alert">
                {error}
              </Text>
            )}
            <Button
              type="submit"
              width="full"
              disabled={!ready || busy || tooShort}
            >
              {busy ? T.saving : T.save}
            </Button>
          </form>
        )}
      </div>
    </AuthFlowContainer>
  );
}
