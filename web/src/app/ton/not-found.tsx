import Link from "next/link";
import { COPY } from "@/lib/ton/copy";

export default function TonNotFound() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center">
      <span className="ton-eyebrow">{COPY.notFound.eyebrow}</span>
      <h1 className="ton-title">{COPY.notFound.title}</h1>
      <p className="max-w-md text-text-03">{COPY.notFound.body}</p>
      <Link
        href="/ton"
        className="ton-focusable ton-brand-text rounded-08 px-2 py-1 font-semibold"
      >
        {COPY.notFound.back}
      </Link>
    </div>
  );
}
