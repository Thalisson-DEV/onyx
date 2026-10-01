import { redirect } from "next/navigation";
import type { Route } from "next";
import { requireAuth } from "@/lib/auth/svcSS";
import TonChrome from "@/layouts/chromes/TonChrome";
import { ProjectsProvider } from "@/lib/projects/providers";
import { VoiceModeProvider } from "@/providers/VoiceModeProvider";

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
        <TonChrome>{children}</TonChrome>
      </VoiceModeProvider>
    </ProjectsProvider>
  );
}
