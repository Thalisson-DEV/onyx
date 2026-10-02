"use client";

import "@/components/auth/ton-auth.css";
import Link from "next/link";
import { useTranslations } from "next-intl";
import Image from "next/image";
import { Text } from "@opal/components";
import { SvgCheckCircle } from "@opal/icons";
import { COPY } from "@/lib/ton/copy";

/*
  The TON deployment is controlled: accounts are provisioned or invited by an
  administrator. Sign-in therefore offers no self-service "create account"
  path; signup and join pages keep their own route for first-user setup and
  invitations.
*/

function BrandPanel() {
  return (
    <aside className="ton-auth-brand hidden lg:flex flex-col justify-between p-10 xl:p-14">
      <div className="flex items-center gap-4">
        <Image
          src="/ton/vale-norte-logo-reversed.png"
          alt={COPY.auth.brand}
          width={1057}
          height={412}
          priority
          className="h-11 w-auto"
        />
        <span aria-hidden className="ton-auth-divider h-9 border-s" />
        <span className="ton-auth-badge">{COPY.auth.product}</span>
      </div>
      <div className="flex flex-col gap-6 max-w-lg">
        <h2 className="ton-auth-headline">
          {`${COPY.auth.headline} `}
          <span className="ton-auth-accent">{COPY.auth.headlineAccent}</span>
        </h2>
        <ul className="flex flex-col gap-3">
          {COPY.auth.points.map((point) => (
            <li key={point} className="flex items-center gap-3">
              <SvgCheckCircle size={18} className="ton-auth-accent shrink-0" />
              <Text font="main-content-body" color="inherit">
                {point}
              </Text>
            </li>
          ))}
        </ul>
      </div>
      <Text font="secondary-body" color="inherit">
        {COPY.auth.footer}
      </Text>
    </aside>
  );
}

export default function AuthFlowContainer({
  children,
  authState,
  footerContent,
}: {
  children: React.ReactNode;
  authState?: "signup" | "login" | "join";
  footerContent?: React.ReactNode;
}) {
  const t = useTranslations("auth.flowContainer");
  return (
    <div className="ton-auth min-h-screen w-full grid lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
      <BrandPanel />
      <main className="flex flex-col min-h-screen">
        <div className="ton-auth-mobile-bar lg:hidden flex items-center gap-3 px-5 py-4">
          <Image
            src="/ton/vale-norte-logo-reversed.png"
            alt={COPY.auth.brand}
            width={1057}
            height={412}
            priority
            className="h-8 w-auto"
          />
          <span className="ton-auth-badge ton-auth-badge-sm">
            {COPY.auth.product}
          </span>
        </div>
        <div className="flex flex-1 flex-col items-center justify-center p-5 sm:p-10">
          <div className="w-full max-w-md flex flex-col gap-6">
            <div className="w-full">{children}</div>
            {authState === "login" && (
              <div className="ton-auth-note flex flex-col gap-1 p-4 rounded-12">
                {footerContent ?? (
                  <>
                    <Text font="secondary-action" color="text-04">
                      {COPY.auth.restrictedTitle}
                    </Text>
                    <Text font="secondary-body" color="text-03">
                      {COPY.auth.restrictedBody}
                    </Text>
                  </>
                )}
              </div>
            )}
            {authState === "signup" && (
              <div className="text-center w-full">
                <Text font="main-ui-body" color="text-03">
                  {t("signinPrompt.text")}
                </Text>{" "}
                <Link
                  href="/auth/login?autoRedirectToSignup=false"
                  className="text-text-05 mainUiAction underline"
                >
                  {t("signInLink.label")}
                </Link>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
