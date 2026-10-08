import type { Metadata } from "next";
import DesignerPage from "@/views/ton/AutomationsPage/designer/Designer";

export const metadata: Metadata = { title: "Editar automação" };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <DesignerPage automationId={id} />;
}
