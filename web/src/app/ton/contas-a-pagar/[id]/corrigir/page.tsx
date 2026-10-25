import type { Metadata } from "next";
import TitleEditor from "@/views/ton/PayablesPage/TitleEditor";

export const metadata: Metadata = { title: "Corrigir conta" };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <TitleEditor id={id} />;
}
