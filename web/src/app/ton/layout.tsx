import { redirect } from "next/navigation";
import type { Metadata, Route } from "next";
import { requireAuth } from "@/lib/auth/svcSS";
import TonShell from "@/views/ton/shell/TonShell";
import { ProjectsProvider } from "@/lib/projects/providers";
import { VoiceModeProvider } from "@/providers/VoiceModeProvider";

export const metadata: Metadata = {
  title: "TON — Vale Norte",
  description: "Inteligência Operacional e Controladoria com IA",
};

export default async function TonLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const authResult = await requireAuth();

  if (authResult.redirect) {
    return redirect(authResult.redirect as Route);
  }

  return (
    <ProjectsProvider>
      <VoiceModeProvider>
        <TonShell>{children}</TonShell>
      </VoiceModeProvider>
    </ProjectsProvider>
  );
}
