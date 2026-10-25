"use client";

import { FilterBar, FilterField } from "@/views/ton/components/kit";
import { SideModal } from "@/views/ton/components/kit";
import { useMemo, useState } from "react";
import type { Route } from "next";
import { Button, InputTextArea, Text } from "@opal/components";
import { SvgAlertTriangle, SvgLock, SvgPlus, SvgUsers } from "@opal/icons";
import { toast } from "@opal/layouts";
import {
  SUPPLIER_KINDS,
  SUPPLIER_STATUS,
  errorText,
  payablesJson,
  pixText,
  usePayablesContext,
  useSuppliers,
  type PayablesContext,
  type Supplier,
} from "@/lib/ton/payables";
import {
  BackLink,
  EmptyState,
  ErrorState,
  LoadingBlock,
  PageContainer,
  StatusPill,
} from "@/views/ton/components/ui";
import { PatternHead, QuickView } from "@/views/ton/components/pattern";
import { Select } from "@/views/ton/PayablesPage/fields";
import SupplierDialog from "@/views/ton/PayablesPage/SupplierDialog";

const ANY = "__any";
const KIND_LABEL: Record<string, string> = Object.fromEntries(
  SUPPLIER_KINDS.map((kind) => [kind.value, kind.label])
);

function paymentText(supplier: Supplier): string {
  if (supplier.pix_key)
    return `PIX ${pixText(supplier.pix_key_type, supplier.pix_key)}`;
  if (supplier.bank_account)
    return `Banco ${supplier.bank_code} · ag. ${supplier.bank_agency} · ${supplier.bank_account}`;
  return "—";
}

function normalize(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

interface ReviewDialogProps {
  supplier: Supplier;
  onClose: () => void;
  onEdit: () => void;
  onDone: () => void;
}

/** Finance approves or refuses a supplier a unit proposed. */
function ReviewDialog({
  supplier,
  onClose,
  onEdit,
  onDone,
}: ReviewDialogProps) {
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  async function review(approve: boolean) {
    setBusy(true);
    try {
      await payablesJson("POST", `/suppliers/${supplier.id}/review`, {
        approve,
        note: note.trim() || null,
      });
      toast.success(
        approve
          ? "Fornecedor aprovado. As contas dele seguem para conferência."
          : "Cadastro recusado."
      );
      onDone();
    } catch (error) {
      toast.error(errorText(error, "Não foi possível concluir."));
    } finally {
      setBusy(false);
    }
  }

  const warnings = [
    ...supplier.similar.map(
      (other) =>
        `Nome parecido com ${other.name} (${other.tax_id}). Confira se não é o mesmo fornecedor com outro CNPJ.`
    ),
    ...supplier.shared_account.map(
      (other) =>
        `A mesma chave PIX ou conta está no cadastro de ${other.name} (${other.tax_id}).`
    ),
  ];
  const facts: [string, string][] = [
    ["CPF ou CNPJ", supplier.tax_id_display],
    ["Tipo", KIND_LABEL[supplier.kind] ?? supplier.kind],
    ["Razão social", supplier.legal_name],
    ["Pagamento", paymentText(supplier)],
    ["Contas esperando", String(supplier.open_titles)],
  ];

  return (
    <SideModal open onOpenChange={(open) => !open && !busy && onClose()}>
      <SideModal.Content width="md">
        <SideModal.Header
          title={supplier.trade_name || supplier.legal_name}
          description="Cadastro enviado por uma unidade. As contas deste fornecedor esperam esta aprovação."
          onClose={() => !busy && onClose()}
        />
        <SideModal.Body>
          <div className="w-full flex flex-col gap-4">
            <div className="tp-facts">
              {facts.map(([label, value]) => (
                <div key={label} className="flex flex-col gap-0.5">
                  <Text font="secondary-body" color="text-03">
                    {label}
                  </Text>
                  <Text font="main-ui-body" color="text-05">
                    {value}
                  </Text>
                </div>
              ))}
            </div>
            {warnings.map((warning) => (
              <div key={warning} className="tp-alert" data-tone="warning">
                <SvgAlertTriangle
                  size={16}
                  className="text-status-warning-05 shrink-0"
                />
                <Text font="secondary-body" color="text-04">
                  {warning}
                </Text>
              </div>
            ))}
            <InputTextArea
              value={note}
              rows={2}
              maxLength={500}
              aria-label="Observação"
              placeholder="Observação (obrigatória para recusar)"
              onChange={(event) => setNote(event.target.value)}
            />
          </div>
        </SideModal.Body>
        <SideModal.Footer justifyContent="between">
          <Button prominence="tertiary" disabled={busy} onClick={onEdit}>
            Corrigir dados
          </Button>
          <span className="tp-actions">
            <Button
              prominence="secondary"
              variant="danger"
              disabled={busy || !note.trim()}
              onClick={() => void review(false)}
            >
              Recusar
            </Button>
            <Button disabled={busy} onClick={() => void review(true)}>
              Aprovar
            </Button>
          </span>
        </SideModal.Footer>
      </SideModal.Content>
    </SideModal>
  );
}

const VIEWS: {
  key: string;
  label: string;
  tone?: "warning" | "danger";
  test: (supplier: Supplier) => boolean;
}[] = [
  {
    key: "pending",
    label: "Em aprovação",
    tone: "warning",
    test: (s) => s.status === "PENDING",
  },
  {
    key: "shared",
    label: "Conta compartilhada",
    tone: "danger",
    test: (s) => s.shared_account.length > 0,
  },
  { key: "active", label: "Aprovados", test: (s) => s.status === "ACTIVE" },
  { key: "rejected", label: "Recusados", test: (s) => s.status === "REJECTED" },
  { key: "all", label: "Todos", test: () => true },
];

function Registry({ context }: { context: PayablesContext }) {
  const suppliers = useSuppliers();
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState(ANY);
  const [pay, setPay] = useState(ANY);
  const [view, setView] = useState<string | null>(null);
  const [editing, setEditing] = useState<Supplier | "new" | null>(null);
  const [reviewing, setReviewing] = useState<Supplier | null>(null);

  const all = suppliers.data ?? [];
  const filtered = useMemo(() => {
    const needle = normalize(query.trim());
    const digits = query.replace(/\D/g, "");
    return all.filter((supplier) => {
      if (kind !== ANY && supplier.kind !== kind) return false;
      if (pay === "PIX" && !supplier.pix_key) return false;
      if (pay === "BANK" && !supplier.bank_account) return false;
      return (
        !needle ||
        normalize(
          `${supplier.legal_name} ${supplier.trade_name ?? ""}`
        ).includes(needle) ||
        (digits.length >= 3 && supplier.tax_id.includes(digits))
      );
    });
  }, [all, query, kind, pay]);
  const pending = all.filter(
    (supplier) => supplier.status === "PENDING"
  ).length;
  const currentKey =
    view ?? (context.is_finance && pending ? "pending" : "all");
  const current =
    VIEWS.find((item) => item.key === currentKey) ?? VIEWS[VIEWS.length - 1];
  const rows = current ? filtered.filter(current.test) : filtered;

  function open(supplier: Supplier) {
    if (context.is_finance && supplier.status === "PENDING")
      setReviewing(supplier);
    else if (context.is_finance || supplier.status === "PENDING")
      setEditing(supplier);
  }

  return (
    <PageContainer>
      <BackLink href={"/ton/contas-a-pagar" as Route} label="Contas a pagar" />
      <PatternHead
        eyebrow="Contas a pagar"
        title="Fornecedores"
        description="Um cadastro por CPF ou CNPJ, com o pagamento sempre no nome do próprio favorecido. Cadastros das unidades passam pela aprovação do financeiro."
        actions={
          <Button icon={SvgPlus} onClick={() => setEditing("new")}>
            Novo fornecedor
          </Button>
        }
      />
      {suppliers.isLoading && <LoadingBlock label="Carregando…" lines={6} />}
      {suppliers.error && (
        <ErrorState
          message="Não foi possível carregar os fornecedores."
          onRetry={() => suppliers.mutate()}
        />
      )}
      {suppliers.data && all.length === 0 && (
        <div className="ton-card">
          <EmptyState
            icon={SvgUsers}
            tone="brand"
            title="Nenhum fornecedor cadastrado"
            description="Ao enviar uma conta, o TON encontra o fornecedor pelo CNPJ da nota e pede o cadastro quando ele ainda não existe."
          />
        </div>
      )}
      {all.length > 0 && (
        <>
          <div className="tp-chips" role="group" aria-label="Visões rápidas">
            {VIEWS.map((item) => (
              <QuickView
                key={item.key}
                label={item.label}
                tone={item.tone}
                count={String(filtered.filter(item.test).length)}
                active={currentKey === item.key}
                onSelect={() => setView(item.key)}
              />
            ))}
          </div>
          <section className="tn-card" aria-label="Fornecedores">
            <FilterBar
              search={{
                value: query,
                onChange: setQuery,
                placeholder: "Nome ou CPF/CNPJ",
              }}
              tokens={[
                ...(kind !== ANY
                  ? [
                      {
                        key: "kind",
                        label: "Tipo",
                        value:
                          SUPPLIER_KINDS.find((item) => item.value === kind)
                            ?.label ?? kind,
                        onRemove: () => setKind(ANY),
                      },
                    ]
                  : []),
                ...(pay !== ANY
                  ? [
                      {
                        key: "pay",
                        label: "Pagamento",
                        value: pay === "PIX" ? "Só PIX" : "Só conta bancária",
                        onRemove: () => setPay(ANY),
                      },
                    ]
                  : []),
              ]}
              onClear={() => {
                setKind(ANY);
                setPay(ANY);
              }}
              panel={
                <>
                  <FilterField label="Tipo" span={2}>
                    <Select
                      value={kind}
                      label="Tipo"
                      placeholder="Todos os tipos"
                      searchAbove={99}
                      options={[
                        { value: ANY, label: "Todos os tipos" },
                        ...SUPPLIER_KINDS,
                      ]}
                      onChange={setKind}
                    />
                  </FilterField>
                  <FilterField label="Pagamento" span={2}>
                    <Select
                      value={pay}
                      label="Pagamento"
                      placeholder="PIX ou conta"
                      searchAbove={99}
                      options={[
                        { value: ANY, label: "PIX ou conta" },
                        { value: "PIX", label: "Só PIX" },
                        { value: "BANK", label: "Só conta bancária" },
                      ]}
                      onChange={setPay}
                    />
                  </FilterField>
                </>
              }
            />
            {rows.length === 0 ? (
              <div className="border-t border-01">
                <EmptyState
                  icon={SvgUsers}
                  title="Nenhum fornecedor nesta visão"
                />
              </div>
            ) : (
              <div className="overflow-x-auto border-t border-01">
                <table className="tp-table">
                  <thead>
                    <tr>
                      <th scope="col">Fornecedor</th>
                      <th scope="col">CPF/CNPJ</th>
                      <th scope="col">Tipo</th>
                      <th scope="col">Pagamento</th>
                      <th scope="col">Situação</th>
                      <th scope="col" className="tp-end">
                        Contas em aberto
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((supplier) => {
                      const clickable =
                        context.is_finance || supplier.status === "PENDING";
                      return (
                        <tr
                          key={supplier.id}
                          className={clickable ? "tp-row" : undefined}
                          tabIndex={clickable ? 0 : undefined}
                          onClick={() => clickable && open(supplier)}
                          onKeyDown={(event) => {
                            if (clickable && event.key === "Enter")
                              open(supplier);
                          }}
                        >
                          <td className="tp-wrap">
                            <span className="flex flex-col">
                              <span className="tp-strong">
                                {supplier.trade_name || supplier.legal_name}
                              </span>
                              {supplier.trade_name && (
                                <span className="tp-muted">
                                  {supplier.legal_name}
                                </span>
                              )}
                            </span>
                          </td>
                          <td>{supplier.tax_id_display}</td>
                          <td>{KIND_LABEL[supplier.kind] ?? supplier.kind}</td>
                          <td>
                            <span className="flex items-center gap-1.5">
                              {supplier.shared_account.length > 0 && (
                                <SvgAlertTriangle
                                  size={13}
                                  className="text-status-warning-05 shrink-0"
                                  aria-label="Conta usada por outro cadastro"
                                />
                              )}
                              {paymentText(supplier)}
                            </span>
                          </td>
                          <td>
                            <StatusPill
                              tone={SUPPLIER_STATUS[supplier.status].tone}
                            >
                              {SUPPLIER_STATUS[supplier.status].label}
                            </StatusPill>
                          </td>
                          <td className="tp-end">{supplier.open_titles}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
      {editing && (
        <SupplierDialog
          supplier={editing === "new" ? null : editing}
          context={context}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            toast.success("Fornecedor salvo.");
            void suppliers.mutate();
          }}
        />
      )}
      {reviewing && (
        <ReviewDialog
          supplier={reviewing}
          onClose={() => setReviewing(null)}
          onEdit={() => {
            setEditing(reviewing);
            setReviewing(null);
          }}
          onDone={() => {
            setReviewing(null);
            void suppliers.mutate();
          }}
        />
      )}
    </PageContainer>
  );
}

export default function SuppliersPage() {
  const context = usePayablesContext();
  if (context.error)
    return (
      <PageContainer>
        <EmptyState
          icon={SvgLock}
          title="Sem acesso aos fornecedores"
          description="Peça ao administrador do TON para liberar sua unidade."
        />
      </PageContainer>
    );
  if (!context.data)
    return (
      <PageContainer>
        <LoadingBlock label="Carregando…" lines={6} />
      </PageContainer>
    );
  return <Registry context={context.data} />;
}
