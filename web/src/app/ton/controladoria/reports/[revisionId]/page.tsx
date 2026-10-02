import type { Metadata } from "next";

import ReportViewer from "@/views/ton/ReportViewer";

export default async function ReportRoute({
  params,
}: {
  params: Promise<{ revisionId: string }>;
}) {
  const { revisionId } = await params;
  return <ReportViewer revisionId={revisionId} />;
}

export const metadata: Metadata = { title: "Relatório" };
