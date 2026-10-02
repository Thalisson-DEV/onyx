import { notFound } from "next/navigation";

/** Unknown TON addresses render the TON not-found page inside the shell. */
export default function UnknownTonRoute() {
  notFound();
}
