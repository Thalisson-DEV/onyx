import type { Metadata } from "next";
import FlowEditorPage from "@/views/ton/EmailFlowsPage/FlowEditor";

export const metadata: Metadata = { title: "Fluxo de e-mail" };

export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <FlowEditorPage flowId={id} />;
}
