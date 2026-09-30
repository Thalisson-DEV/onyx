import AdminSSChrome from "@/layouts/chromes/AdminSSChrome";

export default async function TonLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return await AdminSSChrome({ children });
}
