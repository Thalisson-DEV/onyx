"use client";

import { SideModal } from "@/views/ton/components/kit";
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { Route } from "next";
import {
  Button,
  CopyButton,
  InputTextArea,
  InputTypeIn,
  Text,
} from "@opal/components";
import {
  SvgAlertCircle,
  SvgAlertTriangle,
  SvgChevronLeft,
  SvgChevronRight,
  SvgEdit,
  SvgExternalLink,
  SvgFileText,
  SvgInfo,
  SvgPaperclip,
  SvgTrash,
} from "@opal/icons";
import { toast } from "@opal/layouts";
import {
  ACTION_DONE,
  ACTION_LABEL,
  DESTINATIONS,
  EVENT_LABEL,
  ROLES,
  STATUS,
  attachmentUrl,
  brDate,
  brDateTime,
  brl,
  documentText,
  errorText,
  fileSize,
  formatPlate,
  guessRole,
  monthLabel,
  payablesJson,
  pixText,
  queueNeighbours,
  titleNumber,
  uploadAttachment,
  usePayablesContext,
  useTitle,
  type AttachmentView,
  type CheckView,
  type PayablesContext,
  type TitleAction,
  type TitleDetail,
} from "@/lib/ton/payables";
import {
  BackLink,
  EmptyState,
  ErrorState,
  LoadingBlock,
  PageContainer,
  StatusPill,
} from "@/views/ton/components/ui";
import { PatternHead } from "@/views/ton/components/pattern";
import InvoicePreview from "@/views/ton/PayablesPage/InvoicePreview";

const NEEDS_REASON: TitleAction[] = ["RETURN", "CANCEL", "UNDO_RELEASE"];
const ROLE_LABEL: Record<string, string> = Object.fromEntries(
  ROLES.map((role) => [role.value, role.label])
);
const MATCH_ICON = { OK: "✓", ATTENTION: "!", MISMATCH: "✕", UNKNOWN: "?" };
// Shown in "Conferido pelo TON"; the rest of the checks get their own alert.
const COVERED = new Set([
  "LATE_NOTICE",
  "NEEDS_HUMAN_LOOK",
  "ATTACHMENT_DUE",
  "INSTALLMENTS_SUM",
]);

function Fact({
  label,
  value,
  wide,
}: {
  label: string;
  value: string;
  wide?: boolean;
}) {
  return (
    <div
      className={
        wide ? "tp-fact-wide flex flex-col gap-0.5" : "flex flex-col gap-0.5"
      }
    >
      <Text font="secondary-body" color="text-03">
        {label}
      </Text>
      <Text font="main-ui-body" color="text-05">
        {value}
      </Text>
    </div>
  );
}

function SectionTitle({ children }: { children: string }) {
  return (
    <Text as="h2" font="main-ui-action" color="text-05">
      {children}
    </Text>
  );
}

function readingText(attachment: AttachmentView): string {
  if (attachment.read_kind === "BOLETO")
    return [
      "Boleto lido",
      attachment.read_amount ? brl(attachment.read_amount) : null,
      attachment.read_due_date
        ? `vence ${brDate(attachment.read_due_date)}`
        : null,
    ]
      .filter(Boolean)
      .join(" · ");
  if (attachment.read_kind === "XML")
    return [
      "Nota lida",
      attachment.read_document_number
        ? `nº ${attachment.read_document_number}`
        : null,
      attachment.read_amount ? brl(attachment.read_amount) : null,
    ]
      .filter(Boolean)
      .join(" · ");
  if (attachment.read_kind === "PDF")
    return "CNPJ do fornecedor encontrado no arquivo";
  return "Sem leitura automática: confira olhando o arquivo";
}

function Viewer({
  title,
  canAttach,
  busy,
  onUpload,
  onRemove,
}: {
  title: TitleDetail;
  canAttach: boolean;
  busy: boolean;
  onUpload: (files: FileList) => void;
  onRemove: (attachment: AttachmentView) => void;
}) {
  const [index, setIndex] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  const current =
    title.attachments[Math.min(index, title.attachments.length - 1)];
  const url = current ? attachmentUrl(title.id, current.id) : "";
  const isPdf =
    current?.content_type === "application/pdf" ||
    current?.original_name.toLowerCase().endsWith(".pdf");
  const isImage = current?.content_type.startsWith("image/");
  return (
    <div className="ton-card tp-viewer">
      <div className="tp-viewer-tabs" role="tablist" aria-label="Documentos">
        {title.attachments.map((attachment, position) => (
          <button
            key={attachment.id}
            type="button"
            role="tab"
            aria-selected={attachment.id === current?.id}
            className="tp-viewer-tab ton-focusable"
            onClick={() => setIndex(position)}
          >
            {`${ROLE_LABEL[attachment.role] ?? "Anexo"}${attachment.original_name.toLowerCase().endsWith(".xml") ? " (XML)" : ""}`}
          </button>
        ))}
        {canAttach && (
          <span className="ms-auto">
            <Button
              size="sm"
              prominence="tertiary"
              icon={SvgPaperclip}
              disabled={busy}
              onClick={() => input.current?.click()}
            >
              Anexar
            </Button>
            <input
              ref={input}
              type="file"
              multiple
              accept=".pdf,.xml,.jpg,.jpeg,.png"
              className="hidden"
              onChange={(event) => {
                if (event.target.files) onUpload(event.target.files);
                event.target.value = "";
              }}
            />
          </span>
        )}
      </div>
      {!current ? (
        <div className="tp-viewer-empty">
          <SvgFileText size={24} className="text-text-03" />
          <Text font="main-ui-action" color="text-05">
            Nenhum documento anexado
          </Text>
          <Text font="secondary-body" color="text-03">
            {title.kind === "ESTIMATE"
              ? "Estimativa não tem nota. Quando a nota chegar, envie a conta real e escolha esta estimativa."
              : "Sem nota e boleto, o título não é liberado."}
          </Text>
        </div>
      ) : (
        <>
          {isPdf && (
            <iframe
              title={current.stored_name}
              src={url}
              className="tp-viewer-frame"
            />
          )}
          {isImage && (
            <img
              src={url}
              alt={current.stored_name}
              className="tp-viewer-image"
            />
          )}
          {!isPdf && !isImage && <InvoicePreview url={url} />}
          <div
            className="tp-file"
            style={{ borderTop: "1px solid var(--border-01)" }}
          >
            <SvgFileText size={16} className="text-text-03" />
            <span className="flex flex-col min-w-0">
              <Text font="main-ui-body" color="text-05" maxLines={1}>
                {current.stored_name}
              </Text>
              <Text font="secondary-body" color="text-03">
                {`${fileSize(current.size_bytes)} · ${readingText(current)}`}
              </Text>
            </span>
            <a
              href={url}
              target="_blank"
              rel="noreferrer"
              className="ton-focusable ton-link-button flex items-center gap-1"
            >
              Abrir
              <SvgExternalLink size={12} />
            </a>
            {title.can_edit ? (
              <Button
                size="sm"
                prominence="tertiary"
                icon={SvgTrash}
                aria-label={`Remover ${current.stored_name}`}
                disabled={busy}
                onClick={() => onRemove(current)}
              />
            ) : (
              <span />
            )}
          </div>
        </>
      )}
    </div>
  );
}

function ReasonDialog({
  title,
  intro,
  confirm,
  danger,
  withReference,
  optionalReason,
  onClose,
  onConfirm,
}: {
  title: string;
  intro: string;
  confirm: string;
  danger?: boolean;
  withReference?: boolean;
  optionalReason?: boolean;
  onClose: () => void;
  onConfirm: (reason: string, reference: string) => Promise<void>;
}) {
  const [reason, setReason] = useState("");
  const [reference, setReference] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <SideModal open onOpenChange={(open) => !open && !busy && onClose()}>
      <SideModal.Content width="sm">
        <SideModal.Header
          title={title}
          description={intro}
          onClose={() => !busy && onClose()}
        />
        <SideModal.Body>
          <div className="w-full flex flex-col gap-3">
            {withReference && (
              <InputTypeIn
                value={reference}
                maxLength={80}
                aria-label="Número do lançamento no NG"
                placeholder="Número do lançamento no NG (opcional)"
                onChange={(event) => setReference(event.target.value)}
              />
            )}
            {!withReference && (
              <InputTextArea
                value={reason}
                rows={3}
                maxLength={1000}
                aria-label="Motivo"
                placeholder={
                  optionalReason
                    ? "Observação (opcional)"
                    : "Motivo, que fica no histórico"
                }
                onChange={(event) => setReason(event.target.value)}
              />
            )}
          </div>
        </SideModal.Body>
        <SideModal.Footer>
          <Button prominence="secondary" disabled={busy} onClick={onClose}>
            Voltar
          </Button>
          <Button
            variant={danger ? "danger" : undefined}
            disabled={
              busy ||
              (!withReference && !optionalReason && reason.trim().length < 5)
            }
            onClick={async () => {
              setBusy(true);
              await onConfirm(reason.trim(), reference.trim());
              setBusy(false);
            }}
          >
            {busy ? "Salvando…" : confirm}
          </Button>
        </SideModal.Footer>
      </SideModal.Content>
    </SideModal>
  );
}

const PROMPTS: Partial<
  Record<TitleAction, { intro: string; danger?: boolean }>
> = {
  RETURN: {
    intro:
      "A unidade recebe o título de volta com o motivo, corrige e reenvia.",
  },
  CANCEL: {
    intro: "O título sai da agenda. O histórico fica guardado.",
    danger: true,
  },
  UNDO_RELEASE: {
    intro: "O título volta para conferido e sai do lote de pagamento.",
  },
  BOOK: {
    intro:
      "Registre que o título já está lançado no NG. O pagamento vem da baixa no NG.",
  },
};

function Conference({ id, context }: { id: string; context: PayablesContext }) {
  const router = useRouter();
  const detail = useTitle(id);
  const [prompt, setPrompt] = useState<TitleAction | null>(null);
  const [deciding, setDeciding] = useState<CheckView | null>(null);
  const [busy, setBusy] = useState(false);
  const { previous, next } = queueNeighbours(id);
  const title = detail.data;
  const finance = context.is_finance;

  function go(target: string | null) {
    router.push(
      (target
        ? `/ton/contas-a-pagar/${target}`
        : "/ton/contas-a-pagar") as Route
    );
  }

  async function apply(
    request: Promise<TitleDetail>,
    message?: string
  ): Promise<boolean> {
    setBusy(true);
    try {
      await detail.mutate(await request, { revalidate: false });
      if (message) toast.success(message);
      return true;
    } catch (error) {
      toast.error(errorText(error, "Não foi possível concluir."));
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function run(
    action: TitleAction,
    reason = "",
    reference = "",
    thenNext = false
  ) {
    const done = await apply(
      payablesJson<TitleDetail>("POST", `/titles/${id}/actions`, {
        action,
        reason: reason || null,
        ng_reference: reference || null,
      }),
      ACTION_DONE[action]
    );
    if (!done) return;
    setPrompt(null);
    if (thenNext) go(next);
  }

  function choose(action: TitleAction) {
    if (PROMPTS[action]) setPrompt(action);
    else void run(action);
  }

  if (detail.isLoading) return <LoadingBlock label="Carregando…" lines={8} />;
  if (detail.error || !title)
    return (
      <ErrorState
        message="Não foi possível abrir o título."
        onRetry={() => detail.mutate()}
      />
    );

  const blocking = title.checks.filter(
    (check) => check.severity === "BLOCK" && !check.decided
  );
  const otherAlerts = title.checks.filter(
    (check) =>
      check.severity !== "BLOCK" && !check.decided && !COVERED.has(check.code)
  );
  const decided = title.checks.filter((check) => check.decided);
  const returned =
    title.status === "RETURNED"
      ? title.events.find((event) => event.action === "RETURN")?.reason
      : null;
  const destination =
    DESTINATIONS.find((item) => item.value === title.destination_kind)?.label ??
    "";
  const canAttach =
    title.kind === "REAL" &&
    (title.can_edit ||
      (finance &&
        !["BOOKED", "PAID", "CANCELLED", "ESTIMATE_REPLACED"].includes(
          title.status
        )));
  const has = (action: TitleAction) => title.actions.includes(action);

  return (
    <>
      <BackLink href={"/ton/contas-a-pagar" as Route} label="Contas a pagar" />
      <PatternHead
        eyebrow={`${titleNumber(title.number)} · ${title.unit_name}`}
        title={title.supplier_name}
        description={`${title.kind === "ESTIMATE" ? `Estimativa até ${brDate(title.estimate_until)}` : `${documentText(title)} · parcela ${title.installment_number} de ${title.installment_count}`} · vence ${brDate(title.due_date)} · ${brl(title.amount)}`}
        actions={
          <StatusPill tone={STATUS[title.status].tone}>
            {STATUS[title.status].label}
          </StatusPill>
        }
      />
      <div className="tp-split">
        <Viewer
          title={title}
          canAttach={canAttach}
          busy={busy}
          onUpload={(files) => {
            void (async () => {
              for (const file of Array.from(files)) {
                await apply(
                  uploadAttachment(id, file, guessRole(file.name)),
                  `${file.name} anexado.`
                );
              }
            })();
          }}
          onRemove={(attachment) =>
            void apply(
              payablesJson<TitleDetail>(
                "DELETE",
                `/titles/${id}/attachments/${attachment.id}`
              ),
              "Anexo removido."
            )
          }
        />
        <div className="tp-stack">
          {returned && (
            <div className="tp-alert" role="status">
              <SvgAlertCircle
                size={18}
                className="text-status-error-05 shrink-0"
              />
              <div className="flex flex-col gap-0.5">
                <Text font="main-ui-action" color="text-05">
                  Devolvido pelo financeiro
                </Text>
                <Text font="secondary-body" color="text-04">
                  {returned}
                </Text>
              </div>
            </div>
          )}
          {blocking.map((check) => {
            const other = check.code === "DUPLICATE" ? check.subject : null;
            return (
              <div
                key={`${check.code}-${check.subject}`}
                className="tp-alert"
                role="alert"
              >
                <SvgAlertCircle
                  size={18}
                  className="text-status-error-05 shrink-0"
                />
                <div className="flex flex-col gap-2 min-w-0">
                  <div className="flex flex-col gap-0.5">
                    <Text font="main-ui-action" color="text-05">
                      {check.title}
                    </Text>
                    <Text font="secondary-body" color="text-04">
                      {check.detail}
                    </Text>
                  </div>
                  {(other || (finance && check.decidable)) && (
                    <span className="flex flex-wrap gap-2">
                      {other && (
                        <Button
                          size="sm"
                          prominence="secondary"
                          onClick={() => go(other)}
                        >
                          Abrir o outro título
                        </Button>
                      )}
                      {finance && check.decidable && (
                        <Button
                          size="sm"
                          prominence="tertiary"
                          onClick={() => setDeciding(check)}
                        >
                          Não se aplica…
                        </Button>
                      )}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
          {otherAlerts.map((check) => (
            <div
              key={`${check.code}-${check.subject}`}
              className="tp-alert"
              data-tone={check.severity === "INFO" ? "info" : "warning"}
            >
              {check.severity === "INFO" ? (
                <SvgInfo size={18} className="text-text-03 shrink-0" />
              ) : (
                <SvgAlertTriangle
                  size={18}
                  className="text-status-warning-05 shrink-0"
                />
              )}
              <div className="flex flex-col gap-0.5">
                <Text font="main-ui-action" color="text-05">
                  {check.title}
                </Text>
                <Text font="secondary-body" color="text-04">
                  {check.detail}
                </Text>
              </div>
            </div>
          ))}

          {title.confirmations.length > 0 && (
            <section className="ton-card tp-section">
              <SectionTitle>
                Conferido pelo TON contra os documentos
              </SectionTitle>
              <div className="tp-match">
                {title.confirmations.map((item) => (
                  <MatchRow
                    key={item.label}
                    label={item.label}
                    value={item.value}
                    state={item.state}
                  />
                ))}
              </div>
              {decided.map((check) => (
                <Text
                  key={`${check.code}-${check.subject}`}
                  font="secondary-body"
                  color="text-03"
                >
                  {`${check.title}: dispensado — ${check.decision_reason ?? ""}`}
                </Text>
              ))}
            </section>
          )}

          <section className="ton-card tp-section">
            <SectionTitle>Para lançar no NG</SectionTitle>
            <div className="tp-facts">
              <Fact
                label="Natureza"
                value={`${title.account_code} ${title.account_label}`}
              />
              <Fact label="Competência" value={monthLabel(title.competence)} />
              <Fact
                label="Destino"
                value={[
                  destination,
                  title.destination_kind === "VEHICLE"
                    ? title.vehicle_plates.map(formatPlate).join(", ")
                    : title.destination_note,
                ]
                  .filter(Boolean)
                  .join(" · ")}
              />
              <Fact label="Emissão" value={brDate(title.issue_date)} />
              <Fact
                label="Fornecedor"
                value={`${title.supplier.legal_name} · ${title.supplier_tax_id}`}
                wide
              />
              <Fact
                label="Pagar por"
                value={
                  title.supplier.pix_key
                    ? `${title.payment_method} · chave ${pixText(title.supplier.pix_key_type, title.supplier.pix_key)}`
                    : title.payment_method
                }
              />
              {title.installment_count > 1 ? (
                <Fact
                  label="Total da compra"
                  value={brl(title.purchase_total)}
                />
              ) : (
                <Fact
                  label="Pedido no Zeev"
                  value={title.zeev_request ?? "—"}
                />
              )}
              {title.ng_reference && (
                <Fact label="Lançamento no NG" value={title.ng_reference} />
              )}
              <div className="tp-fact-wide flex flex-col gap-1">
                <span className="flex items-center justify-between gap-2">
                  <Text font="secondary-body" color="text-03">
                    Histórico sugerido para o NG
                  </Text>
                  <CopyButton
                    size="sm"
                    prominence="tertiary"
                    getCopyText={() => title.ng_history}
                  >
                    Copiar
                  </CopyButton>
                </span>
                <Text font="main-ui-body" color="text-05">
                  {title.ng_history}
                </Text>
              </div>
            </div>
          </section>

          {title.same_document.length > 0 && (
            <section className="ton-card tp-section">
              <SectionTitle>Outras parcelas do mesmo documento</SectionTitle>
              <div className="flex flex-col">
                {title.same_document.map((other) => (
                  <button
                    key={other.id}
                    type="button"
                    className="ton-focusable ton-picker-row justify-between"
                    onClick={() => go(other.id)}
                  >
                    <Text font="main-ui-body" color="text-05">
                      {`${titleNumber(other.number)} · parcela ${other.installment_number}/${other.installment_count} · vence ${brDate(other.due_date)}`}
                    </Text>
                    <span className="flex items-center gap-3">
                      <Text font="main-ui-action" color="text-05">
                        {brl(other.amount)}
                      </Text>
                      <StatusPill tone={STATUS[other.status].tone}>
                        {STATUS[other.status].label}
                      </StatusPill>
                    </span>
                  </button>
                ))}
              </div>
            </section>
          )}

          <section className="ton-card tp-section">
            <SectionTitle>Histórico</SectionTitle>
            <ol className="flex flex-col gap-3">
              {title.events.map((event) => (
                <li key={event.id} className="flex flex-col">
                  <Text font="main-ui-body" color="text-05">
                    {event.action === "STATUS" && event.to_status
                      ? `Passou para “${STATUS[event.to_status].label}”`
                      : (EVENT_LABEL[event.action] ?? event.action)}
                  </Text>
                  <Text font="secondary-body" color="text-03">
                    {[event.actor, brDateTime(event.created_at)]
                      .filter(Boolean)
                      .join(" · ")}
                  </Text>
                  {event.reason && event.action !== "STATUS" && (
                    <Text font="secondary-body" color="text-04">
                      {event.reason}
                    </Text>
                  )}
                </li>
              ))}
            </ol>
          </section>
        </div>
      </div>

      <div className="tp-actionbar">
        <div className="tp-actionbar-start">
          <Button
            prominence="tertiary"
            icon={SvgChevronLeft}
            disabled={!previous}
            onClick={() => go(previous)}
          >
            Anterior
          </Button>
          <Button
            prominence="tertiary"
            rightIcon={SvgChevronRight}
            disabled={!next}
            onClick={() => go(next)}
          >
            Próximo
          </Button>
        </div>
        {title.can_edit && (
          <Button
            prominence="secondary"
            icon={SvgEdit}
            disabled={busy}
            onClick={() =>
              router.push(`/ton/contas-a-pagar/${id}/corrigir` as Route)
            }
          >
            Corrigir
          </Button>
        )}
        {has("CANCEL") && (
          <Button
            prominence="tertiary"
            variant="danger"
            disabled={busy}
            onClick={() => choose("CANCEL")}
          >
            Cancelar título
          </Button>
        )}
        {has("UNDO_RELEASE") && (
          <Button
            prominence="secondary"
            disabled={busy}
            onClick={() => choose("UNDO_RELEASE")}
          >
            Desfazer liberação
          </Button>
        )}
        {has("RETURN") && (
          <Button
            prominence="secondary"
            disabled={busy}
            onClick={() => choose("RETURN")}
          >
            Devolver à unidade
          </Button>
        )}
        {has("RESUBMIT") && (
          <Button disabled={busy} onClick={() => choose("RESUBMIT")}>
            Reenviar ao financeiro
          </Button>
        )}
        {has("RELEASE") && (
          <Button
            disabled={busy || blocking.length > 0}
            onClick={() => choose("RELEASE")}
          >
            {blocking.length > 0
              ? "Liberar (resolva o que impede)"
              : "Liberar para pagar"}
          </Button>
        )}
        {has("BOOK") && (
          <Button disabled={busy} onClick={() => choose("BOOK")}>
            Registrar lançamento no NG
          </Button>
        )}
        {has("CONFER") && (
          <Button
            disabled={busy}
            onClick={() => void run("CONFER", "", "", Boolean(next))}
          >
            {next ? "Conferido, próximo" : "Marcar como conferido"}
          </Button>
        )}
      </div>

      {prompt && PROMPTS[prompt] && (
        <ReasonDialog
          title={ACTION_LABEL[prompt]}
          intro={PROMPTS[prompt]?.intro ?? ""}
          confirm={ACTION_LABEL[prompt]}
          danger={PROMPTS[prompt]?.danger}
          withReference={prompt === "BOOK"}
          optionalReason={!NEEDS_REASON.includes(prompt)}
          onClose={() => setPrompt(null)}
          onConfirm={(reason, reference) => run(prompt, reason, reference)}
        />
      )}
      {deciding && (
        <ReasonDialog
          title={`Não se aplica: ${deciding.title}`}
          intro="Explique por que este apontamento não impede o pagamento. O motivo fica no histórico do título."
          confirm="Dispensar"
          onClose={() => setDeciding(null)}
          onConfirm={async (reason) => {
            const done = await apply(
              payablesJson<TitleDetail>("POST", `/titles/${id}/decisions`, {
                check_code: deciding.code,
                subject: deciding.subject,
                reason,
              }),
              "Apontamento dispensado."
            );
            if (done) setDeciding(null);
          }}
        />
      )}
    </>
  );
}

function MatchRow({
  label,
  value,
  state,
}: {
  label: string;
  value: string;
  state: keyof typeof MATCH_ICON;
}) {
  return (
    <>
      <Text font="main-ui-body" color="text-04">
        {label}
      </Text>
      <Text font="main-ui-body" color="text-05">
        {value}
      </Text>
      <span className="tp-match-icon" data-state={state} aria-label={state}>
        {MATCH_ICON[state]}
      </span>
    </>
  );
}

export default function TitlePage({ id }: { id: string }) {
  const context = usePayablesContext();
  return (
    <PageContainer>
      {context.error && (
        <EmptyState
          icon={SvgFileText}
          title="Sem acesso às contas a pagar"
          description="Peça ao administrador do TON para liberar sua unidade."
        />
      )}
      {!context.data && !context.error && (
        <LoadingBlock label="Carregando…" lines={8} />
      )}
      {context.data && <Conference id={id} context={context.data} />}
    </PageContainer>
  );
}
