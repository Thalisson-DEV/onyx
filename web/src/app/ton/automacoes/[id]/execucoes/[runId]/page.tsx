import type { Metadata } from "next";
import RunViewer from "@/views/ton/AutomationsPage/RunViewer";

export const metadata: Metadata = { title: "Execução" };

export default async function Page({ params }: { params: Promise<{ id: string; runId: string }> }) {
  const { id, runId } = await params;
  return <RunViewer automationId={id} runId={runId} />;
}
