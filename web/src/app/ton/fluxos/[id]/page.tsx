import { redirect } from "next/navigation";

/** E-mail flows are automations of type E-mail now. */
export default function Page() {
  redirect("/ton/automacoes");
}
