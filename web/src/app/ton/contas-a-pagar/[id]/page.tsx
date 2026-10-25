import type { Metadata } from "next";
import TitlePage from "@/views/ton/PayablesPage/TitlePage";

export const metadata: Metadata = { title: "Conferência" };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <TitlePage id={id} />;
}
