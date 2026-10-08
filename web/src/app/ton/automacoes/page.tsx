import { Suspense } from "react";
import type { Metadata } from "next";
import AutomationsPage from "@/views/ton/AutomationsPage";

export const metadata: Metadata = { title: "Automações" };

export default function Page() {
  return (
    <Suspense>
      <AutomationsPage />
    </Suspense>
  );
}
