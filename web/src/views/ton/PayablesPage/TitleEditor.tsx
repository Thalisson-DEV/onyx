"use client";

import {
  useEffect,
  useRef,
  useState,
  type DragEvent,
  type KeyboardEvent,
} from "react";
import { useRouter } from "next/navigation";
import type { Route } from "next";
import { Button, InputTextArea, InputTypeIn, Text } from "@opal/components";
import {
  SvgAlertTriangle,
  SvgFileText,
  SvgPlus,
  SvgUploadCloud,
  SvgX,
} from "@opal/icons";
import { toast } from "@opal/layouts";
import {
  DESTINATIONS,
  DOCUMENT_TYPES,
  ROLES,
  brDate,
  brl,
  competenceOptions,
  errorText,
  fileSize,
  formatPlate,
  guessRole,
  monthLabel,
  moneyInput,
  normalizePlate,
  parseMoney,
  payablesJson,
  readDocument,
  todayIso,
  uploadAttachment,
  usePayablesContext,
  useSuppliers,
  useTitle,
  useTitles,
  type AttachmentRole,
  type DestinationKind,
  type DocumentRead,
  type DocumentType,
  type PayablesContext,
  type Supplier,
  type TitleDetail,
  type TitleInput,
  type TitleKind,
} from "@/lib/ton/payables";
import {
  BackLink,
  ErrorState,
  LoadingBlock,
  PageContainer,
} from "@/views/ton/components/ui";
import {
  FormSection,
  PatternField,
  PatternHead,
} from "@/views/ton/components/pattern";
import { Segmented, Select } from "@/views/ton/PayablesPage/fields";
import SupplierDialog from "@/views/ton/PayablesPage/SupplierDialog";

const MAX_BYTES = 10 * 1024 * 1024;
const ACCEPT = ".pdf,.xml,.jpg,.jpeg,.png";

type FieldKey =
  | "supplier"
  | "documentType"
  | "documentNumber"
  | "issueDate"
  | "competence"
  | "dueDate"
  | "installment"
  | "amount"
  | "purchaseTotal"
  | "account";

interface PendingFile {
  key: string;
  file: File;
  role: AttachmentRole;
  reading: DocumentRead | null;
  reading_failed: boolean;
}

function businessDaysUntil(iso: string): number {
  const [year = 0, month = 1, day = 1] = iso.split("-").map(Number);
  const due = new Date(year, month - 1, day);
  const now = new Date();
  const cursor = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  if (due < cursor) return -1;
  let count = 0;
  while (cursor < due) {
    cursor.setDate(cursor.getDate() + 1);
    if (cursor.getDay() !== 0 && cursor.getDay() !== 6) count++;
  }
  return count;
}

function supplierLabel(supplier: Supplier): string {
  return supplier.trade_name || supplier.legal_name;
}

function readingText(reading: DocumentRead | null, failed: boolean): string {
  if (failed) return "Não foi possível ler este arquivo agora.";
  if (!reading) return "Lendo…";
  if (reading.kind === "XML")
    return `Lido: ${[
      reading.tax_id_display,
      reading.document_number ? `nº ${reading.document_number}` : null,
      reading.issue_date ? `emissão ${brDate(reading.issue_date)}` : null,
      reading.amount ? brl(reading.amount) : null,
      reading.installments.length > 1
        ? `${reading.installments.length} parcelas`
        : null,
    ]
      .filter(Boolean)
      .join(", ")}`;
  if (reading.kind === "BOLETO")
    return `Lido: ${[
      reading.amount ? brl(reading.amount) : null,
      reading.due_date ? `vence ${brDate(reading.due_date)}` : null,
    ]
      .filter(Boolean)
      .join(", ")}`;
  if (reading.kind === "PDF")
    return "CNPJ encontrado; valor e vencimento ficam com você.";
  return "Sem leitura automática: preencha ao lado.";
}

function Editor({
  context,
  title,
}: {
  context: PayablesContext;
  title: TitleDetail | null;
}) {
  const router = useRouter();
  const suppliers = useSuppliers();
  const titles = useTitles();
  const editing = title !== null;
  const singleUnit = context.units.length === 1 ? context.units[0] : undefined;

  const [kind, setKind] = useState<TitleKind>(title?.kind ?? "REAL");
  const [unitId, setUnitId] = useState(title?.unit_id ?? singleUnit?.id ?? "");
  const [supplierId, setSupplierId] = useState(title?.supplier_id ?? "");
  const [accountId, setAccountId] = useState(title?.account_id ?? "");
  const [documentType, setDocumentType] = useState<DocumentType | "">(
    title?.document_type ?? ""
  );
  const [documentNumber, setDocumentNumber] = useState(
    title?.document_number ?? ""
  );
  const [issueDate, setIssueDate] = useState(title?.issue_date ?? "");
  const [competence, setCompetence] = useState(title?.competence ?? "");
  const [dueDate, setDueDate] = useState(title?.due_date ?? "");
  const [installment, setInstallment] = useState(
    String(title?.installment_number ?? 1)
  );
  const [installments, setInstallments] = useState(
    String(title?.installment_count ?? 1)
  );
  const [amount, setAmount] = useState(
    title ? moneyInput(Number(title.amount)) : ""
  );
  const [purchaseTotal, setPurchaseTotal] = useState(
    title ? moneyInput(Number(title.purchase_total)) : ""
  );
  const [destination, setDestination] = useState<DestinationKind>(
    title?.destination_kind ?? "VEHICLE"
  );
  const [plates, setPlates] = useState<string[]>(title?.vehicle_plates ?? []);
  const [plateDraft, setPlateDraft] = useState("");
  const [plateError, setPlateError] = useState<string | null>(null);
  const [destinationNote, setDestinationNote] = useState(
    title?.destination_note ?? ""
  );
  const [description, setDescription] = useState(title?.description ?? "");
  const [zeev, setZeev] = useState(title?.zeev_request ?? "");
  const [estimateUntil, setEstimateUntil] = useState(
    title?.estimate_until ?? ""
  );
  const [replaces, setReplaces] = useState(title?.replaces_estimate_id ?? "");
  const [files, setFiles] = useState<PendingFile[]>([]);
  // The invoice's duplicatas, read from its XML; each one becomes a title.
  const [parcels, setParcels] = useState<DocumentRead["installments"]>([]);
  const [sendAll, setSendAll] = useState(true);
  const [filled, setFilled] = useState<Set<FieldKey>>(new Set());
  const [touched, setTouched] = useState<Set<FieldKey>>(
    new Set(
      editing ? ["supplier", "account", "competence", "amount", "dueDate"] : []
    )
  );
  const [unknownSupplier, setUnknownSupplier] = useState<DocumentRead | null>(
    null
  );
  const [newSupplier, setNewSupplier] = useState<{
    taxId: string;
    name: string;
  } | null>(null);
  const [dragging, setDragging] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const real = kind === "REAL";
  const count = Math.max(1, Number.parseInt(installments, 10) || 1);
  const number = Math.max(1, Number.parseInt(installment, 10) || 1);
  const amountValue = parseMoney(amount);
  const totalValue = count === 1 ? amountValue : parseMoney(purchaseTotal);
  const supplierList = (suppliers.data ?? []).filter(
    (item) => item.status === "ACTIVE" || item.status === "PENDING"
  );
  const supplier = supplierList.find((item) => item.id === supplierId);
  const openEstimates = (titles.data ?? []).filter(
    (row) =>
      row.status === "ESTIMATE_OPEN" &&
      row.unit_id === unitId &&
      row.supplier_id === supplierId
  );
  const today = todayIso();
  const months = competenceOptions();
  if (competence && !months.includes(competence)) months.push(competence);
  const unitName = context.units.find((unit) => unit.id === unitId)?.name;

  /** A value the TON read; it never overwrites what the person typed. */
  function offer(key: FieldKey, apply: () => void) {
    if (touched.has(key)) return;
    apply();
    setFilled((current) => new Set(current).add(key));
  }

  function touch(key: FieldKey) {
    setTouched((current) => new Set(current).add(key));
    setFilled((current) => {
      const next = new Set(current);
      next.delete(key);
      return next;
    });
  }

  function chooseSupplier(id: string, list: Supplier[] = supplierList) {
    setSupplierId(id);
    setUnknownSupplier(null);
    const chosen = list.find((item) => item.id === id);
    if (chosen?.default_account_id && !touched.has("account")) {
      setAccountId(chosen.default_account_id);
      setFilled((current) => new Set(current).add("account"));
    }
    setReplaces("");
  }

  function applyReading(reading: DocumentRead) {
    if (reading.supplier) {
      offer("supplier", () => chooseSupplier(reading.supplier?.id ?? ""));
    } else if (reading.tax_id && !supplierId) {
      setUnknownSupplier(reading);
    }
    if (reading.kind === "XML") {
      if (reading.document_type)
        offer("documentType", () =>
          setDocumentType(reading.document_type ?? "")
        );
      if (reading.document_number)
        offer("documentNumber", () =>
          setDocumentNumber(reading.document_number ?? "")
        );
      if (reading.issue_date) {
        offer("issueDate", () => setIssueDate(reading.issue_date ?? ""));
        offer("competence", () =>
          setCompetence(`${(reading.issue_date ?? "").slice(0, 7)}-01`)
        );
      }
      if (reading.amount)
        offer("purchaseTotal", () =>
          setPurchaseTotal(moneyInput(Number(reading.amount)))
        );
      const parcels = reading.installments;
      if (parcels.length > 1 && !editing) setParcels(parcels);
      if (parcels.length > 1) {
        offer("installment", () => {
          setInstallments(String(parcels.length));
          const due = dueDate
            ? parcels.find((item) => item.due_date === dueDate)
            : undefined;
          const pick = due ?? parcels[0];
          if (pick) {
            setInstallment(String(parcels.indexOf(pick) + 1));
            offer("amount", () => setAmount(moneyInput(Number(pick.amount))));
            offer("dueDate", () => setDueDate(pick.due_date));
          }
        });
      } else {
        if (reading.amount)
          offer("amount", () => setAmount(moneyInput(Number(reading.amount))));
        if (parcels[0])
          offer("dueDate", () => setDueDate(parcels[0]?.due_date ?? ""));
      }
    }
    if (reading.kind === "BOLETO") {
      if (reading.amount)
        offer("amount", () => setAmount(moneyInput(Number(reading.amount))));
      if (reading.due_date)
        offer("dueDate", () => setDueDate(reading.due_date ?? ""));
    }
  }

  async function takeFiles(list: FileList | null) {
    if (!list) return;
    const refused: string[] = [];
    const accepted: PendingFile[] = [];
    for (const file of Array.from(list)) {
      if (
        !/\.(pdf|xml|jpe?g|png)$/i.test(file.name) ||
        file.size > MAX_BYTES ||
        file.size === 0
      ) {
        refused.push(file.name);
        continue;
      }
      const key = `${file.name}-${file.size}-${file.lastModified}`;
      if (files.some((item) => item.key === key)) continue;
      accepted.push({
        key,
        file,
        role: guessRole(file.name),
        reading: null,
        reading_failed: false,
      });
    }
    setFileError(
      refused.length
        ? `Não foi possível anexar ${refused.join(", ")}: use PDF, XML ou foto de até 10 MB.`
        : null
    );
    setFiles((current) => [...current, ...accepted]);
    for (const item of accepted) {
      try {
        const reading = await readDocument(item.file);
        const role: AttachmentRole =
          reading.kind === "XML"
            ? "INVOICE"
            : reading.kind === "BOLETO"
              ? "BOLETO"
              : item.role;
        setFiles((current) =>
          current.map((entry) =>
            entry.key === item.key ? { ...entry, reading, role } : entry
          )
        );
        applyReading(reading);
      } catch {
        setFiles((current) =>
          current.map((entry) =>
            entry.key === item.key ? { ...entry, reading_failed: true } : entry
          )
        );
      }
    }
  }

  function addPlate(raw: string) {
    const parts = raw.split(/[\s,;/]+/).filter(Boolean);
    const invalid: string[] = [];
    const next = [...plates];
    for (const part of parts) {
      const value = normalizePlate(part);
      if (!value) invalid.push(part.toUpperCase());
      else if (!next.includes(value)) next.push(value);
    }
    setPlates(next);
    setPlateDraft(invalid.join(" "));
    setPlateError(
      invalid.length
        ? `Placa inválida: ${invalid.join(", ")}. Use o formato ABC1D23.`
        : null
    );
  }

  function onPlateKey(event: KeyboardEvent<HTMLInputElement>) {
    if (["Enter", ",", " "].includes(event.key) && plateDraft.trim()) {
      event.preventDefault();
      addPlate(plateDraft);
    } else if (event.key === "Backspace" && !plateDraft && plates.length) {
      setPlates(plates.slice(0, -1));
    }
  }

  const errors: Record<string, string | null> = {
    unit: !unitId ? "Escolha a unidade." : null,
    supplier: !supplierId ? "Escolha ou cadastre o fornecedor." : null,
    documentType: real && !documentType ? "Escolha o tipo." : null,
    documentNumber: real && !documentNumber.trim() ? "Informe o número." : null,
    issueDate: real
      ? !issueDate
        ? "Informe a emissão."
        : issueDate > today
          ? "A emissão não pode ser no futuro."
          : null
      : null,
    competence: !competence ? "Escolha o mês." : null,
    dueDate: !dueDate
      ? "Informe o vencimento."
      : issueDate && dueDate < issueDate
        ? "Vence antes da emissão."
        : null,
    installment: number > count ? `A parcela vai até ${count}.` : null,
    amount: !amountValue ? "Informe o valor." : null,
    purchaseTotal:
      count > 1 && !totalValue
        ? "Informe o total da compra."
        : count > 1 && amountValue && totalValue && amountValue > totalValue
          ? "A parcela é maior que a compra."
          : null,
    account: !accountId ? "Escolha a natureza." : null,
    plates:
      destination === "VEHICLE" && plates.length === 0
        ? "Informe ao menos uma placa."
        : null,
    destinationNote:
      destination === "SITE" && !destinationNote.trim()
        ? "Informe a obra ou o local."
        : null,
    description:
      description.trim().length < 3 ? "Descreva o que foi comprado." : null,
    estimateUntil:
      !real && !estimateUntil ? "Até quando vale a estimativa?" : null,
  };
  const error = (key: string) => (submitted ? (errors[key] ?? null) : null);
  const valid = Object.values(errors).every((value) => !value);
  const daysToDue = dueDate ? businessDaysUntil(dueDate) : null;
  const lateNotice =
    real && daysToDue !== null && daysToDue < context.notice_business_days;

  function note(
    key: FieldKey,
    fallback?: string
  ): { text: string | null; tone?: "filled" | "error" } {
    const message = error(key);
    if (message) return { text: message, tone: "error" };
    if (filled.has(key))
      return {
        text:
          key === "account"
            ? "Natureza padrão do fornecedor"
            : key === "supplier"
              ? "Encontrado pelo CNPJ da nota"
              : "Lido do documento",
        tone: "filled",
      };
    return { text: fallback ?? null };
  }

  async function submit() {
    setSubmitted(true);
    if (plateDraft.trim()) addPlate(plateDraft);
    if (!valid || !amountValue || !totalValue) {
      toast.error("Confira os campos marcados.");
      return;
    }
    setBusy(true);
    setFailure(null);
    const body: TitleInput = {
      unit_id: unitId,
      kind,
      supplier_id: supplierId,
      account_id: accountId,
      document_type: documentType || null,
      document_number: documentNumber.trim() || null,
      issue_date: issueDate || null,
      competence,
      due_date: dueDate,
      installment_number: number,
      installment_count: count,
      purchase_total: totalValue.toFixed(2),
      amount: amountValue.toFixed(2),
      destination_kind: destination,
      vehicle_plates: destination === "VEHICLE" ? plates : [],
      destination_note: destinationNote.trim() || null,
      description: description.trim(),
      zeev_request: zeev.trim() || null,
      estimate_until: real ? null : estimateUntil || null,
      replaces_estimate_id: real ? replaces || null : null,
    };
    // One title per installment of the invoice, when the person asked for all.
    const batch =
      sendAll && !editing && real && parcels.length > 1
        ? parcels.map((parcel, position) => ({
            ...body,
            installment_number: position + 1,
            installment_count: parcels.length,
            amount: Number(parcel.amount).toFixed(2),
            due_date: parcel.due_date,
          }))
        : [body];
    const created: TitleDetail[] = [];
    const failed: string[] = [];
    try {
      for (const item of batch) {
        created.push(
          title
            ? await payablesJson<TitleDetail>(
                "PUT",
                `/titles/${title.id}`,
                item
              )
            : await payablesJson<TitleDetail>("POST", "/titles", item)
        );
      }
    } catch (caught) {
      setFailure(
        errorText(caught, "Não foi possível enviar. Tente novamente.") +
          (created.length
            ? ` ${created.length} parcela(s) já foram enviadas.`
            : "")
      );
      setBusy(false);
      if (!created.length) return;
    }
    for (const saved of created) {
      for (const item of files) {
        // A boleto belongs to the installment whose due date it carries.
        const boletoDue =
          item.role === "BOLETO" ? item.reading?.due_date : null;
        if (created.length > 1 && boletoDue && boletoDue !== saved.due_date)
          continue;
        try {
          await uploadAttachment(saved.id, item.file, item.role);
        } catch {
          failed.push(item.file.name);
        }
      }
    }
    setBusy(false);
    if (failed.length)
      toast.error(
        `A conta foi salva, mas estes anexos falharam: ${failed.join(", ")}. Anexe de novo na conferência.`
      );
    else
      toast.success(
        editing
          ? "Alterações salvas."
          : !real
            ? "Estimativa registrada."
            : created.length > 1
              ? `${created.length} parcelas enviadas ao financeiro.`
              : "Conta enviada ao financeiro."
      );
    await titles.mutate();
    const first = created[0];
    if (first) router.push(`/ton/contas-a-pagar/${first.id}` as Route);
  }

  return (
    <>
      <BackLink
        href={
          (title
            ? `/ton/contas-a-pagar/${title.id}`
            : "/ton/contas-a-pagar") as Route
        }
        label={title ? "Voltar ao título" : "Contas a pagar"}
      />
      <PatternHead
        eyebrow={`Contas a pagar${unitName ? ` · ${unitName}` : ""}`}
        title={editing ? "Corrigir conta" : "Enviar conta"}
        description={
          editing
            ? "As alterações ficam no histórico do título."
            : "Comece pelos documentos. O TON lê a nota e o boleto e preenche o que puder; você confere e completa."
        }
      />
      <div className="tp-editor">
        <div className="tp-stack">
          {!editing && (
            <div className="ton-card tp-section">
              <Text font="main-ui-action" color="text-05">
                O que você está enviando
              </Text>
              <Segmented
                label="Tipo de envio"
                value={kind}
                options={[
                  { value: "REAL", label: "Conta com nota" },
                  { value: "ESTIMATE", label: "Estimativa" },
                ]}
                onChange={setKind}
              />
              <Text font="secondary-body" color="text-03">
                {real
                  ? "Nota, fatura ou recibo que precisa ser pago."
                  : "Previsão sem nota, como o combustível da quinzena. Não entra como conta; a nota real a substitui depois."}
              </Text>
            </div>
          )}
          <div
            className="tp-dropzone"
            data-dragging={dragging ? "true" : undefined}
            onDragOver={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event: DragEvent<HTMLDivElement>) => {
              event.preventDefault();
              setDragging(false);
              void takeFiles(event.dataTransfer.files);
            }}
          >
            <SvgUploadCloud size={22} className="text-text-03" />
            <Text font="main-ui-action" color="text-05">
              {real
                ? "Arraste a nota e o boleto"
                : "Anexe a cotação ou o pedido, se houver"}
            </Text>
            <Text font="secondary-body" color="text-03">
              XML ou PDF da nota, PDF do boleto ou foto. Até 10 MB cada.
            </Text>
            <Button
              prominence="secondary"
              size="sm"
              onClick={() => fileInput.current?.click()}
            >
              Escolher arquivos
            </Button>
            <input
              ref={fileInput}
              type="file"
              multiple
              accept={ACCEPT}
              className="hidden"
              onChange={(event) => {
                void takeFiles(event.target.files);
                event.target.value = "";
              }}
            />
          </div>
          {fileError && (
            <Text as="p" font="secondary-body" color="status-error-05">
              {fileError}
            </Text>
          )}
          {(files.length > 0 || (title && title.attachments.length > 0)) && (
            <div className="ton-card">
              {title?.attachments.map((attachment) => (
                <div key={attachment.id} className="tp-file">
                  <SvgFileText size={16} className="text-text-03" />
                  <span className="flex flex-col min-w-0">
                    <Text font="main-ui-body" color="text-05" maxLines={1}>
                      {attachment.stored_name}
                    </Text>
                    <Text font="secondary-body" color="text-03">
                      Já anexado
                    </Text>
                  </span>
                  <span />
                  <span />
                </div>
              ))}
              {files.map((item) => (
                <div key={item.key} className="tp-file">
                  <SvgFileText size={16} className="text-text-03" />
                  <span className="flex flex-col min-w-0">
                    <Text font="main-ui-body" color="text-05" maxLines={1}>
                      {item.file.name}
                    </Text>
                    <Text
                      font="secondary-body"
                      color={
                        item.reading?.kind ? "status-success-05" : "text-03"
                      }
                    >
                      {`${fileSize(item.file.size)} · ${readingText(item.reading, item.reading_failed)}`}
                    </Text>
                  </span>
                  <div className="w-36">
                    <Select
                      value={item.role}
                      label="Tipo do anexo"
                      placeholder="Tipo"
                      options={ROLES}
                      onChange={(role) =>
                        setFiles(
                          files.map((entry) =>
                            entry.key === item.key
                              ? { ...entry, role: role as AttachmentRole }
                              : entry
                          )
                        )
                      }
                    />
                  </div>
                  <Button
                    prominence="tertiary"
                    size="sm"
                    icon={SvgX}
                    aria-label={`Remover ${item.file.name}`}
                    onClick={() => {
                      setFiles(files.filter((entry) => entry.key !== item.key));
                      if (item.reading?.installments.length) setParcels([]);
                    }}
                  />
                </div>
              ))}
            </div>
          )}
          {parcels.length > 1 && real && (
            <div className="ton-card tp-section">
              <Text font="main-ui-action" color="text-05">
                {`A nota tem ${parcels.length} parcelas`}
              </Text>
              <div className="flex flex-col">
                {parcels.map((parcel, position) => (
                  <div
                    key={`${parcel.number}-${parcel.due_date}`}
                    className="tp-paper-row"
                    style={{
                      borderBottomStyle: "solid",
                      borderBottomColor: "var(--border-01)",
                    }}
                  >
                    <Text font="main-ui-body" color="text-04">
                      {`${position + 1} de ${parcels.length} · vence ${brDate(parcel.due_date)}`}
                    </Text>
                    <Text font="main-ui-action" color="text-05">
                      {brl(parcel.amount)}
                    </Text>
                  </div>
                ))}
              </div>
              <Segmented
                label="Parcelas a enviar"
                value={sendAll ? "ALL" : "ONE"}
                options={[
                  { value: "ALL", label: `Enviar as ${parcels.length} agora` },
                  { value: "ONE", label: "Só a parcela ao lado" },
                ]}
                onChange={(value) => setSendAll(value === "ALL")}
              />
              <Text font="secondary-body" color="text-03">
                {sendAll
                  ? "O TON cria uma conta por parcela, cada uma com seu vencimento e valor. A nota vai anexada em todas; o boleto, só na parcela que ele paga."
                  : "Só a parcela escolhida no formulário é enviada agora."}
              </Text>
            </div>
          )}
          {unknownSupplier && !supplierId && (
            <div className="tp-alert" data-tone="warning">
              <SvgAlertTriangle
                size={18}
                className="text-status-warning-05 shrink-0"
              />
              <div className="flex flex-col gap-2">
                <div className="flex flex-col gap-0.5">
                  <Text font="main-ui-action" color="text-05">
                    Fornecedor ainda não cadastrado
                  </Text>
                  <Text font="secondary-body" color="text-04">
                    {`${unknownSupplier.issuer_name ?? "Emitente"} · ${unknownSupplier.tax_id_display ?? ""}. Cadastre agora; o financeiro aprova antes do pagamento.`}
                  </Text>
                </div>
                <span>
                  <Button
                    size="sm"
                    icon={SvgPlus}
                    onClick={() =>
                      setNewSupplier({
                        taxId: unknownSupplier.tax_id ?? "",
                        name: unknownSupplier.issuer_name ?? "",
                      })
                    }
                  >
                    Cadastrar fornecedor
                  </Button>
                </span>
              </div>
            </div>
          )}
          {lateNotice && (
            <div className="tp-alert" data-tone="warning">
              <SvgAlertTriangle
                size={18}
                className="text-status-warning-05 shrink-0"
              />
              <div className="flex flex-col gap-0.5">
                <Text font="main-ui-action" color="text-05">
                  {daysToDue !== null && daysToDue < 0
                    ? "Esta conta já venceu"
                    : `Vence em ${daysToDue} ${daysToDue === 1 ? "dia útil" : "dias úteis"}`}
                </Text>
                <Text font="secondary-body" color="text-04">
                  {`O financeiro pede ${context.notice_business_days} dias úteis. Envie assim que a nota chegar.`}
                </Text>
              </div>
            </div>
          )}
        </div>

        <div className="ton-card">
          <div className="tp-form">
            <FormSection title="Quem e qual documento">
              <PatternField
                label="Fornecedor"
                span={singleUnit ? 12 : 8}
                filled={filled.has("supplier")}
                note={note("supplier").text}
                noteTone={note("supplier").tone}
              >
                <div className="flex gap-2">
                  <div className="flex-1 min-w-0">
                    <Select
                      value={supplierId}
                      label="Fornecedor"
                      placeholder={
                        suppliers.isLoading
                          ? "Carregando…"
                          : "Busque pelo nome ou CNPJ"
                      }
                      searchAbove={0}
                      options={supplierList.map((item) => ({
                        value: item.id,
                        label:
                          item.status === "PENDING"
                            ? `${supplierLabel(item)} (em aprovação)`
                            : supplierLabel(item),
                        description: item.tax_id_display,
                      }))}
                      error={Boolean(error("supplier"))}
                      onChange={(id) => {
                        touch("supplier");
                        chooseSupplier(id);
                      }}
                    />
                  </div>
                  <Button
                    prominence="secondary"
                    icon={SvgPlus}
                    onClick={() => setNewSupplier({ taxId: "", name: "" })}
                  >
                    Novo
                  </Button>
                </div>
              </PatternField>
              {!singleUnit && (
                <PatternField
                  label="Unidade"
                  span={4}
                  note={error("unit")}
                  noteTone="error"
                >
                  <Select
                    value={unitId}
                    label="Unidade"
                    placeholder="Escolha a unidade"
                    options={context.units.map((unit) => ({
                      value: unit.id,
                      label: unit.name,
                    }))}
                    error={Boolean(error("unit"))}
                    onChange={setUnitId}
                  />
                </PatternField>
              )}
              <PatternField
                label={real ? "Documento" : "Documento (opcional)"}
                span={4}
                filled={filled.has("documentType")}
                note={note("documentType").text}
                noteTone={note("documentType").tone}
              >
                <Select
                  value={documentType}
                  label="Tipo do documento"
                  placeholder="Tipo"
                  searchAbove={99}
                  options={DOCUMENT_TYPES}
                  error={Boolean(error("documentType"))}
                  onChange={(value) => {
                    touch("documentType");
                    setDocumentType(value as DocumentType);
                  }}
                />
              </PatternField>
              <PatternField
                label="Número"
                span={4}
                filled={filled.has("documentNumber")}
                note={note("documentNumber").text}
                noteTone={note("documentNumber").tone}
              >
                <InputTypeIn
                  value={documentNumber}
                  maxLength={60}
                  aria-label="Número do documento"
                  placeholder="Ex.: 38371"
                  variant={error("documentNumber") ? "error" : "primary"}
                  onChange={(event) => {
                    touch("documentNumber");
                    setDocumentNumber(event.target.value);
                  }}
                />
              </PatternField>
              <PatternField
                label="Emissão"
                span={4}
                filled={filled.has("issueDate")}
                note={note("issueDate").text}
                noteTone={note("issueDate").tone}
              >
                <InputTypeIn
                  type="date"
                  value={issueDate}
                  max={today}
                  aria-label="Data de emissão"
                  variant={error("issueDate") ? "error" : "primary"}
                  onChange={(event) => {
                    touch("issueDate");
                    setIssueDate(event.target.value);
                    if (!touched.has("competence") && event.target.value)
                      setCompetence(`${event.target.value.slice(0, 7)}-01`);
                  }}
                />
              </PatternField>
              {real && openEstimates.length > 0 && (
                <PatternField
                  label="Substitui a estimativa"
                  note="Escolha a previsão que esta nota confirma."
                >
                  <Select
                    value={replaces}
                    label="Estimativa"
                    placeholder="Nenhuma"
                    options={openEstimates.map((row) => ({
                      value: row.id,
                      label: `${brl(row.amount)} · ${monthLabel(row.competence)}`,
                      description: row.description,
                    }))}
                    onChange={setReplaces}
                  />
                </PatternField>
              )}
            </FormSection>

            <FormSection title="Valor e prazo">
              <PatternField
                label={count > 1 ? "Valor desta parcela" : "Valor"}
                span={4}
                filled={filled.has("amount")}
                note={note("amount").text}
                noteTone={note("amount").tone}
              >
                <InputTypeIn
                  value={amount}
                  inputMode="decimal"
                  prefixText="R$"
                  aria-label="Valor do título"
                  placeholder="0,00"
                  variant={error("amount") ? "error" : "primary"}
                  onChange={(event) => {
                    touch("amount");
                    setAmount(event.target.value);
                  }}
                  onBlur={() => {
                    const value = parseMoney(amount);
                    if (value) setAmount(moneyInput(value));
                  }}
                />
              </PatternField>
              <PatternField
                label="Parcela"
                span={4}
                filled={filled.has("installment")}
                note={note("installment", "Cada parcela é uma conta").text}
                noteTone={note("installment").tone}
              >
                <div className="flex items-center gap-2">
                  <InputTypeIn
                    value={installment}
                    inputMode="numeric"
                    aria-label="Número da parcela"
                    onChange={(event) => {
                      touch("installment");
                      setInstallment(
                        event.target.value.replace(/\D/g, "").slice(0, 3)
                      );
                    }}
                  />
                  <Text font="main-ui-body" color="text-03">
                    de
                  </Text>
                  <InputTypeIn
                    value={installments}
                    inputMode="numeric"
                    aria-label="Total de parcelas"
                    onChange={(event) => {
                      touch("installment");
                      setInstallments(
                        event.target.value.replace(/\D/g, "").slice(0, 3)
                      );
                    }}
                  />
                </div>
              </PatternField>
              <PatternField
                label="Total da compra"
                span={4}
                filled={count > 1 && filled.has("purchaseTotal")}
                note={
                  count > 1
                    ? note("purchaseTotal", "Valor da nota inteira").text
                    : "Igual ao valor em parcela única"
                }
                noteTone={count > 1 ? note("purchaseTotal").tone : undefined}
              >
                <InputTypeIn
                  value={count > 1 ? purchaseTotal : amount}
                  inputMode="decimal"
                  prefixText="R$"
                  aria-label="Total da compra"
                  placeholder="0,00"
                  variant={
                    count > 1
                      ? error("purchaseTotal")
                        ? "error"
                        : "primary"
                      : "readOnly"
                  }
                  onChange={(event) => {
                    touch("purchaseTotal");
                    setPurchaseTotal(event.target.value);
                  }}
                />
              </PatternField>
              <PatternField
                label="Vencimento"
                span={4}
                filled={filled.has("dueDate")}
                note={note("dueDate").text}
                noteTone={note("dueDate").tone}
              >
                <InputTypeIn
                  type="date"
                  value={dueDate}
                  aria-label="Vencimento"
                  variant={error("dueDate") ? "error" : "primary"}
                  onChange={(event) => {
                    touch("dueDate");
                    setDueDate(event.target.value);
                  }}
                />
              </PatternField>
              <PatternField
                label="Competência"
                span={4}
                filled={filled.has("competence")}
                note={note("competence", "Mês do consumo ou do serviço").text}
                noteTone={note("competence").tone}
              >
                <Select
                  value={competence}
                  label="Competência"
                  placeholder="Mês"
                  searchAbove={99}
                  options={months.map((month) => ({
                    value: month,
                    label: monthLabel(month),
                  }))}
                  error={Boolean(error("competence"))}
                  onChange={(value) => {
                    touch("competence");
                    setCompetence(value);
                  }}
                />
              </PatternField>
              {real ? (
                <PatternField label="Pedido no Zeev" span={4} note="Opcional">
                  <InputTypeIn
                    value={zeev}
                    maxLength={40}
                    aria-label="Pedido no Zeev"
                    placeholder="Número da solicitação"
                    onChange={(event) => setZeev(event.target.value)}
                  />
                </PatternField>
              ) : (
                <PatternField
                  label="Estimativa vale até"
                  span={4}
                  note={error("estimateUntil")}
                  noteTone="error"
                >
                  <InputTypeIn
                    type="date"
                    value={estimateUntil}
                    aria-label="Estimativa vale até"
                    variant={error("estimateUntil") ? "error" : "primary"}
                    onChange={(event) => setEstimateUntil(event.target.value)}
                  />
                </PatternField>
              )}
            </FormSection>

            <FormSection title="Para onde foi">
              <PatternField
                label="Natureza"
                filled={filled.has("account")}
                note={note("account").text}
                noteTone={note("account").tone}
              >
                <Select
                  value={accountId}
                  label="Natureza"
                  placeholder="Escolha a natureza"
                  options={context.accounts.map((item) => ({
                    value: item.id,
                    label: `${item.code} · ${item.label}`,
                  }))}
                  error={Boolean(error("account"))}
                  onChange={(value) => {
                    touch("account");
                    setAccountId(value);
                  }}
                />
              </PatternField>
              <PatternField label="Destino">
                <Segmented
                  label="Destino"
                  value={destination}
                  options={DESTINATIONS}
                  onChange={setDestination}
                />
              </PatternField>
              {destination === "VEHICLE" ? (
                <PatternField
                  label="Placas"
                  note={
                    plateError ??
                    error("plates") ??
                    "Digite a placa e tecle Enter. Uma conta pode ter vários veículos."
                  }
                  noteTone={plateError || error("plates") ? "error" : undefined}
                >
                  <div
                    className="tp-plates"
                    data-error={
                      plateError || error("plates") ? "true" : undefined
                    }
                  >
                    {plates.map((value) => (
                      <span key={value} className="tp-plate">
                        {formatPlate(value)}
                        <button
                          type="button"
                          className="ton-focusable rounded-08"
                          aria-label={`Remover ${formatPlate(value)}`}
                          onClick={() =>
                            setPlates(plates.filter((item) => item !== value))
                          }
                        >
                          <SvgX size={12} />
                        </button>
                      </span>
                    ))}
                    <div className="flex-1 min-w-[8rem]">
                      <InputTypeIn
                        value={plateDraft}
                        variant="internal"
                        aria-label="Placa"
                        placeholder={plates.length ? "Outra placa" : "ABC1D23"}
                        onChange={(event) => {
                          setPlateDraft(event.target.value.toUpperCase());
                          setPlateError(null);
                        }}
                        onKeyDown={onPlateKey}
                        onBlur={() => plateDraft.trim() && addPlate(plateDraft)}
                      />
                    </div>
                  </div>
                </PatternField>
              ) : (
                <PatternField
                  label={
                    destination === "SITE"
                      ? "Obra ou local"
                      : "Detalhe (opcional)"
                  }
                  note={error("destinationNote")}
                  noteTone="error"
                >
                  <InputTypeIn
                    value={destinationNote}
                    maxLength={300}
                    aria-label="Detalhe do destino"
                    placeholder={
                      destination === "SITE"
                        ? "Ex.: aterro, garagem, posto de coleta"
                        : "Ex.: material de limpeza da sede"
                    }
                    variant={error("destinationNote") ? "error" : "primary"}
                    onChange={(event) => setDestinationNote(event.target.value)}
                  />
                </PatternField>
              )}
              <PatternField
                label="Descrição"
                note={
                  error("description") ?? "O que foi comprado ou contratado"
                }
                noteTone={error("description") ? "error" : undefined}
              >
                <InputTextArea
                  value={description}
                  rows={2}
                  autoResize
                  maxRows={5}
                  maxLength={1000}
                  aria-label="Descrição"
                  placeholder="Ex.: troca de bomba hidráulica e filtro"
                  variant={error("description") ? "error" : "primary"}
                  onChange={(event) => setDescription(event.target.value)}
                />
              </PatternField>
            </FormSection>
            {failure && (
              <Text as="p" font="secondary-body" color="status-error-05">
                {failure}
              </Text>
            )}
          </div>
          <div className="tp-form-foot">
            <Text font="secondary-body" color="text-03">
              {[
                amountValue ? brl(amountValue) : null,
                dueDate ? `vence ${brDate(dueDate)}` : null,
                files.length
                  ? `${files.length} ${files.length === 1 ? "anexo" : "anexos"}`
                  : null,
              ]
                .filter(Boolean)
                .join(" · ") || "Preencha ou arraste os documentos"}
            </Text>
            <div className="tp-actions">
              <Button
                prominence="secondary"
                disabled={busy}
                onClick={() => router.back()}
              >
                Cancelar
              </Button>
              <Button disabled={busy} onClick={() => void submit()}>
                {busy
                  ? "Enviando…"
                  : editing
                    ? "Salvar alterações"
                    : !real
                      ? "Registrar estimativa"
                      : sendAll && parcels.length > 1
                        ? `Enviar as ${parcels.length} parcelas`
                        : "Enviar ao financeiro"}
              </Button>
            </div>
          </div>
        </div>
      </div>
      {newSupplier && (
        <SupplierDialog
          supplier={null}
          context={context}
          initialTaxId={newSupplier.taxId}
          initialName={newSupplier.name}
          onClose={() => setNewSupplier(null)}
          onSaved={async (created) => {
            setNewSupplier(null);
            const list = (await suppliers.mutate()) ?? [];
            touch("supplier");
            chooseSupplier(created.id, [...list, created]);
          }}
        />
      )}
    </>
  );
}

export default function TitleEditor({ id }: { id?: string }) {
  const context = usePayablesContext();
  const title = useTitle(id ?? null);
  const [ready, setReady] = useState(!id);
  useEffect(() => {
    if (title.data) setReady(true);
  }, [title.data]);
  return (
    <PageContainer>
      {(context.error || title.error) && (
        <ErrorState message="Não foi possível abrir a conta." />
      )}
      {(!context.data || !ready) && !context.error && !title.error && (
        <LoadingBlock label="Carregando…" lines={8} />
      )}
      {context.data && ready && title.data && !title.data.can_edit ? (
        <ErrorState message="Este título já foi conferido pelo financeiro e não muda mais. Peça para devolvê-lo à unidade." />
      ) : (
        context.data &&
        ready && (
          <Editor
            context={context.data}
            title={id ? (title.data ?? null) : null}
          />
        )
      )}
    </PageContainer>
  );
}
