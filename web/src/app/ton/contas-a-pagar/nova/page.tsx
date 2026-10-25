import type { Metadata } from "next";
import TitleEditor from "@/views/ton/PayablesPage/TitleEditor";

export const metadata: Metadata = { title: "Enviar conta" };

export default function Page() {
  return <TitleEditor />;
}
