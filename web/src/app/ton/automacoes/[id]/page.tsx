import type { Metadata } from "next";
import DetailPage from "@/views/ton/AutomationsPage/DetailPage";

export const metadata: Metadata = { title: "Automação" };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <DetailPage automationId={id} />;
}
