"use client";

import useSWR from "swr";
import { Text } from "@opal/components";
import { brDate, brl, maskTaxId } from "@/lib/ton/payables";
import { LoadingBlock } from "@/views/ton/components/ui";

/** NF-e and NFS-e (ABRASF) tags, read by local name. */
interface Invoice {
  kind: "NF-e" | "NFS-e";
  number: string | null;
  issued: string | null;
  issuerName: string | null;
  issuerTaxId: string | null;
  buyerName: string | null;
  buyerTaxId: string | null;
  total: string | null;
  items: { description: string; amount: string | null }[];
  installments: { number: string; due: string; amount: string }[];
}

function first(root: Element | Document, ...names: string[]): Element | null {
  for (const name of names) {
    const found = root.getElementsByTagNameNS("*", name)[0];
    if (found) return found;
  }
  return null;
}

function text(
  root: Element | Document | null,
  ...names: string[]
): string | null {
  if (!root) return null;
  const value = first(root, ...names)?.textContent?.trim();
  return value || null;
}

function parse(xml: string): Invoice | null {
  const doc = new DOMParser().parseFromString(xml, "application/xml");
  if (doc.getElementsByTagName("parsererror").length) return null;
  const nfe = first(doc, "infNFe");
  if (nfe) {
    const issuer = first(nfe, "emit");
    const buyer = first(nfe, "dest");
    return {
      kind: "NF-e",
      number: text(nfe, "nNF"),
      issued: text(nfe, "dhEmi", "dEmi"),
      issuerName: text(issuer, "xNome"),
      issuerTaxId: text(issuer, "CNPJ", "CPF"),
      buyerName: text(buyer, "xNome"),
      buyerTaxId: text(buyer, "CNPJ", "CPF"),
      total: text(nfe, "vNF"),
      items: Array.from(nfe.getElementsByTagNameNS("*", "prod")).map(
        (product) => ({
          description: text(product, "xProd") ?? "",
          amount: text(product, "vProd"),
        })
      ),
      installments: Array.from(nfe.getElementsByTagNameNS("*", "dup")).map(
        (dup) => ({
          number: text(dup, "nDup") ?? "",
          due: text(dup, "dVenc") ?? "",
          amount: text(dup, "vDup") ?? "",
        })
      ),
    };
  }
  const issuer = first(doc, "PrestadorServico", "Prestador", "prest");
  const buyer = first(doc, "TomadorServico", "Tomador", "toma");
  const description = text(doc, "Discriminacao", "xDescServ");
  return {
    kind: "NFS-e",
    number: text(doc, "Numero", "nNFSe"),
    issued: text(doc, "DataEmissao", "dhEmi", "dhProc"),
    issuerName: text(issuer, "RazaoSocial", "xNome"),
    issuerTaxId: text(issuer, "Cnpj", "CNPJ", "Cpf", "CPF"),
    buyerName: text(buyer, "RazaoSocial", "xNome"),
    buyerTaxId: text(buyer, "Cnpj", "CNPJ", "Cpf", "CPF"),
    total: text(doc, "ValorLiquidoNfse", "ValorServicos", "vLiq", "vServ"),
    items: description ? [{ description, amount: null }] : [],
    installments: [],
  };
}

async function fetchText(url: string): Promise<string> {
  const response = await fetch(url);
  if (!response.ok) throw new Error(String(response.status));
  return response.text();
}

function Pair({
  label,
  value,
  mark,
}: {
  label: string;
  value: string | null;
  mark?: boolean;
}) {
  return (
    <div className="flex flex-col gap-0.5 min-w-0">
      <span className="tp-paper-label">{label}</span>
      <span className={mark ? "tp-paper-mark" : undefined}>{value ?? "—"}</span>
    </div>
  );
}

/** A DANFE-like page built from the invoice XML, marking what the TON compared. */
export default function InvoicePreview({ url }: { url: string }) {
  const file = useSWR(url, fetchText);
  if (file.isLoading)
    return (
      <div className="p-6">
        <LoadingBlock label="Carregando a nota…" lines={6} />
      </div>
    );
  const invoice = file.data ? parse(file.data) : null;
  if (!invoice)
    return (
      <div className="tp-viewer-empty">
        <Text font="main-ui-action" color="text-05">
          Não foi possível ler este XML
        </Text>
        <Text font="secondary-body" color="text-03">
          Abra o arquivo para conferir manualmente.
        </Text>
      </div>
    );
  return (
    <div className="tp-paper">
      <div className="tp-paper-title">{`${invoice.kind} · documento montado a partir do XML`}</div>
      <div className="tp-paper-grid">
        <Pair label="Emitente" value={invoice.issuerName} />
        <Pair
          label="CNPJ/CPF do emitente"
          value={invoice.issuerTaxId ? maskTaxId(invoice.issuerTaxId) : null}
          mark
        />
        <Pair label="Número" value={invoice.number} mark />
        <Pair
          label="Emissão"
          value={invoice.issued ? brDate(invoice.issued.slice(0, 10)) : null}
        />
        <Pair label="Destinatário" value={invoice.buyerName} />
        <Pair
          label="CNPJ/CPF do destinatário"
          value={invoice.buyerTaxId ? maskTaxId(invoice.buyerTaxId) : null}
        />
      </div>
      {invoice.items.length > 0 && (
        <div className="flex flex-col gap-1">
          <span className="tp-paper-label">
            {invoice.kind === "NF-e" ? "Produtos" : "Serviço"}
          </span>
          {invoice.items.slice(0, 12).map((item, index) => (
            <div key={index} className="tp-paper-row">
              <span>{item.description}</span>
              {item.amount && <span>{brl(item.amount)}</span>}
            </div>
          ))}
          {invoice.items.length > 12 && (
            <span className="tp-paper-label">{`+ ${invoice.items.length - 12} itens`}</span>
          )}
        </div>
      )}
      {invoice.installments.length > 0 && (
        <div className="flex flex-col gap-1">
          <span className="tp-paper-label">Duplicatas</span>
          {invoice.installments.map((item) => (
            <div key={`${item.number}-${item.due}`} className="tp-paper-row">
              <span>{`${item.number} · vence ${brDate(item.due)}`}</span>
              <span>{brl(item.amount)}</span>
            </div>
          ))}
        </div>
      )}
      <div className="tp-paper-row tp-paper-total">
        <span>Valor total</span>
        <span className="tp-paper-mark">{brl(invoice.total)}</span>
      </div>
    </div>
  );
}
