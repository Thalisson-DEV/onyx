import ReportPage from "@/views/ton/ControladoriaPage/ReportPage";

export default async function ReportRoute({
  params,
}: {
  params: Promise<{ revisionId: string }>;
}) {
  const { revisionId } = await params;
  return <ReportPage revisionId={revisionId} />;
}
