"use client";

import { Diamond, SideModal } from "@/views/ton/components/kit";
import { useAskTon } from "@/views/ton/ask/AskTon";
import { useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import type { Route } from "next";
import { Button, InputTextArea, Text } from "@opal/components";
import {
  SvgBubbleText,
  SvgChevronLeft,
  SvgChevronRight,
  SvgEdit,
  SvgInfo,
} from "@opal/icons";
import { toast } from "@opal/layouts";
import { brDate, brDateTime, brl, errorText } from "@/lib/ton/payables";
import {
  CRITICALITY_TONE,
  SITUATION_TONE,
  caseNeighbours,
  caseNumber,
  correctionJson,
  isOpen,
  useCase,
  type CaseDetail,
  type EvidenceRow,
} from "@/lib/ton/correction";
import {
  BackLink,
  ErrorState,
  LoadingBlock,
  PageContainer,
  StatusPill,
} from "@/views/ton/components/ui";
import { PatternHead } from "@/views/ton/components/pattern";
import OwnerDialog from "@/views/ton/CorrectionPage/OwnerDialog";

const PAGE = 40;

function Part({
  step,
  title,
  question,
  children,
}: {
  step: number;
  title: string;
  question: string;
  children: ReactNode;
}) {
  return (
    <section className="tp-part">
      <div className="tp-part-title">
        <span className="tp-step">{step}</span>
        <div className="flex flex-col gap-0.5">
          <Text as="h2" font="main-ui-action" color="text-05">
            {title}
          </Text>
          <Text font="secondary-body" color="text-03">
            {question}
          </Text>
        </div>
      </div>
      <div className="tp-part-body">{children}</div>
    </section>
  );
}

function Pairs({ items }: { items: [string, string][] }) {
  return (
    <dl className="tp-kv">
      {items.map(([label, value]) => (
        <div key={label} className="contents">
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

type Field =
  | "emission"
  | "document"
  | "amount"
  | "account"
  | "unit"
  | "history";
const FIELDS: Field[] = [
  "emission",
  "document",
  "amount",
  "account",
  "unit",
  "history",
];

/** Fields whose value differs inside each pair, by group key. */
function differences(rows: EvidenceRow[]): Map<string, Set<Field>> {
  const groups = new Map<string, EvidenceRow[]>();
  for (const row of rows) {
    if (!row.group) continue;
    groups.set(row.group, [...(groups.get(row.group) ?? []), row]);
  }
  const result = new Map<string, Set<Field>>();
  for (const [key, members] of groups) {
    const differing = new Set<Field>();
    for (const field of FIELDS) {
      if (new Set(members.map((member) => member[field] ?? "")).size > 1)
        differing.add(field);
    }
    result.set(key, differing);
  }
  return result;
}

function Evidence({ rows, total }: { rows: EvidenceRow[]; total: number }) {
  const [all, setAll] = useState(false);
  const shown = all ? rows : rows.slice(0, PAGE);
  const paired = rows.some((row) => row.group);
  const readable = rows.some((row) => row.history || row.emission);
  const diff = differences(rows);
  const tone = (row: EvidenceRow, field: Field, extra?: string) => {
    if (!row.group) return extra;
    const marked = diff.get(row.group)?.has(field) ? "tp-diff" : "tp-same";
    return extra ? `${marked} ${extra}` : marked;
  };
  return (
    <div className="flex flex-col gap-2">
      <div className="tp-evidence">
        <table className="tp-table">
          <thead>
            <tr>
              <th scope="col">Aba e linha</th>
              {readable ? (
                <>
                  <th scope="col">Emissão</th>
                  <th scope="col">Documento</th>
                  <th scope="col" className="tp-end">
                    Valor
                  </th>
                  <th scope="col">Natureza</th>
                  <th scope="col">Unidade</th>
                  <th scope="col">Histórico</th>
                </>
              ) : (
                <>
                  <th scope="col">Onde</th>
                  <th scope="col" className="tp-end">
                    Valor
                  </th>
                </>
              )}
              <th scope="col">Hoje</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((row, index) => {
              const start =
                paired &&
                row.group !== null &&
                shown[index - 1]?.group !== row.group;
              return (
                <tr
                  key={`${row.occurrence_code}-${row.sheet}-${row.row}-${index}`}
                  data-pair-start={start ? "true" : undefined}
                >
                  <td className="tp-strong">{`${row.sheet ?? "—"} · ${row.row ?? "—"}`}</td>
                  {readable ? (
                    <>
                      <td className={tone(row, "emission")}>
                        {row.emission ? brDate(row.emission) : "—"}
                      </td>
                      <td className={tone(row, "document")}>
                        {row.document ?? "—"}
                      </td>
                      <td className={tone(row, "amount", "tp-end")}>
                        {row.amount ? brl(row.amount) : "—"}
                      </td>
                      <td
                        className={tone(row, "account")}
                        title={row.account ?? undefined}
                      >
                        {row.account?.split(" ")[0] ?? "—"}
                      </td>
                      <td className={tone(row, "unit")}>
                        {row.unit?.replace(/^\d+\s*-\s*/, "") || (
                          <span className="tp-muted">sem unidade</span>
                        )}
                      </td>
                      <td className={tone(row, "history", "tp-history")}>
                        {row.history ?? "—"}
                      </td>
                    </>
                  ) : (
                    <>
                      <td>
                        {row.column
                          ? `coluna ${row.column} (valor ilegível)`
                          : "—"}
                      </td>
                      <td className="tp-end">
                        {row.amount ? brl(row.amount) : "—"}
                      </td>
                    </>
                  )}
                  <td>
                    <StatusPill
                      tone={row.status === "FIXED" ? "success" : "warning"}
                    >
                      {row.status === "FIXED" ? "Corrigido" : "Na origem"}
                    </StatusPill>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <span className="flex flex-wrap items-center justify-between gap-2">
        <Text font="secondary-body" color="text-03">
          {paired
            ? "Cada par está separado por uma linha mais forte. Em destaque o que muda entre as linhas do par; em cinza o que é igual."
            : `${total} ${total === 1 ? "item" : "itens"} na origem.`}
        </Text>
        {rows.length > PAGE && (
          <button
            type="button"
            className="ton-focusable ton-link-button"
            onClick={() => setAll(!all)}
          >
            {all ? "Mostrar menos" : `Mostrar todos (${rows.length})`}
          </button>
        )}
      </span>
      {total > rows.length && (
        <Text font="secondary-body" color="text-03">
          {`Mostrando ${rows.length} de ${total}.`}
        </Text>
      )}
    </div>
  );
}

function ReasonDialog({
  title,
  intro,
  confirm,
  onClose,
  onConfirm,
}: {
  title: string;
  intro: string;
  confirm: string;
  onClose: () => void;
  onConfirm: (reason: string) => Promise<void>;
}) {
  const [reason, setReason] = useState("");
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
          <InputTextArea
            value={reason}
            rows={3}
            maxLength={1000}
            aria-label="Motivo"
            placeholder="Motivo, que fica no histórico do caso"
            onChange={(event) => setReason(event.target.value)}
          />
        </SideModal.Body>
        <SideModal.Footer>
          <Button prominence="secondary" disabled={busy} onClick={onClose}>
            Voltar
          </Button>
          <Button
            disabled={busy || reason.trim().length < 5}
            onClick={async () => {
              setBusy(true);
              await onConfirm(reason.trim());
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

function Sheet({ id }: { id: string }) {
  const router = useRouter();
  const { ask: askTon } = useAskTon();
  const detail = useCase(id);
  const [assigning, setAssigning] = useState(false);
  const [deciding, setDeciding] = useState<"ACCEPT_RISK" | "REOPEN" | null>(
    null
  );
  const [editingAction, setEditingAction] = useState(false);
  const [actionDraft, setActionDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const { previous, next } = caseNeighbours(id);
  const item = detail.data;

  async function apply(
    request: Promise<CaseDetail>,
    message: string
  ): Promise<boolean> {
    setBusy(true);
    try {
      await detail.mutate(await request, { revalidate: false });
      toast.success(message);
      return true;
    } catch (error) {
      toast.error(errorText(error, "Não foi possível concluir."));
      return false;
    } finally {
      setBusy(false);
    }
  }

  function go(target: string | null) {
    router.push(
      (target ? `/ton/ocorrencias/${target}` : "/ton/ocorrencias") as Route
    );
  }

  if (detail.isLoading) return <LoadingBlock label="Carregando…" lines={8} />;
  if (detail.error || !item)
    return (
      <ErrorState
        message="Não foi possível abrir o caso."
        onRetry={() => detail.mutate()}
      />
    );

  const owner = [item.owner_area, item.owner_name].filter(Boolean).join(" · ");
  const open = isOpen(item);
  const askAbout = () =>
    askTon({
      screen: `${caseNumber(item.number)} · ${item.title}`,
      chips: ["Plano de correção", caseNumber(item.number), item.title],
      details: [
        `Caso ${caseNumber(item.number)} do plano de correção: ${item.title}`,
        `Meses: ${item.months.join(", ")} · área ${item.owner_area ?? item.suggested_area}${owner ? ` · responsável ${owner}` : ""}`,
        `Situação: ${item.situation}`,
      ],
      suggestions: [
        "Mostre os lançamentos e explique a causa provável",
        "Qual o próximo passo e quem deve fazer?",
        "Como verificar que foi corrigido?",
      ],
    });

  return (
    <>
      <BackLink href={"/ton/ocorrencias" as Route} label="Plano de correção" />
      <PatternHead
        eyebrow={`${caseNumber(item.number)} · ${item.owner_area ?? item.suggested_area} · ${item.months.join(", ")}`}
        title={item.title}
        description={item.summary}
        actions={
          <>
            <StatusPill tone={CRITICALITY_TONE[item.criticality]}>
              {item.criticality_label}
            </StatusPill>
            <StatusPill tone={SITUATION_TONE[item.situation]}>
              {item.situation_label}
            </StatusPill>
          </>
        }
      />

      <div className="ton-card tp-sheet">
        <Part step={1} title="De onde veio" question="Arquivo, aba e linhas">
          <Pairs
            items={[
              ["Sistema", item.origin.system],
              ["Arquivo", item.origin.file_name ?? "—"],
              [
                "Importado",
                item.origin.imported_at
                  ? brDateTime(item.origin.imported_at)
                  : "—",
              ],
              ["Abas", item.origin.sheets.join(", ") || "—"],
            ]}
          />
          <Evidence rows={item.evidence} total={item.evidence_total} />
        </Part>

        <Part
          step={2}
          title="Como o TON achou"
          question="A regra, em português"
        >
          <Text as="p" font="main-ui-body" color="text-05">
            {item.found}
          </Text>
          <Pairs
            items={[
              ["Regra", `${item.rule_title} (${item.rule_code})`],
              ["Primeira vez", brDateTime(item.first_detected_at)],
              ["Última vez", brDateTime(item.last_detected_at)],
            ]}
          />
        </Part>

        <Part
          step={3}
          title="Por que importa"
          question="Quanto pesa e onde distorce"
        >
          <Pairs
            items={[
              [
                "Impacto",
                item.has_amount
                  ? `${brl(item.situation === "VERIFIED" ? item.impact_total : item.impact_open)} (${item.impact_basis})`
                  : item.impact_basis,
              ],
              [
                "Criticidade",
                `${item.criticality_label}: ${item.criticality_reason}`,
              ],
              ["Onde distorce", item.matters],
              ["Causa provável", item.cause],
              ...(item.closing_note
                ? ([["No fechamento", item.closing_note]] as [string, string][])
                : []),
            ]}
          />
        </Part>

        <Part
          step={4}
          title="O que fazer"
          question="Quem, até quando e como o TON confere"
        >
          {editingAction ? (
            <div className="flex flex-col gap-2">
              <InputTextArea
                value={actionDraft}
                rows={3}
                maxLength={1000}
                aria-label="Ação"
                onChange={(event) => setActionDraft(event.target.value)}
              />
              <span className="flex gap-2">
                <Button
                  size="sm"
                  disabled={busy}
                  onClick={async () => {
                    const done = await apply(
                      correctionJson<CaseDetail>("PUT", `/cases/${id}/action`, {
                        action_text: actionDraft.trim() || null,
                      }),
                      "Ação salva."
                    );
                    if (done) setEditingAction(false);
                  }}
                >
                  Salvar
                </Button>
                <Button
                  size="sm"
                  prominence="secondary"
                  disabled={busy}
                  onClick={() => setEditingAction(false)}
                >
                  Cancelar
                </Button>
              </span>
            </div>
          ) : (
            <span className="flex items-start justify-between gap-3">
              <Text as="p" font="main-ui-body" color="text-05">
                {item.action}
              </Text>
              {open && (
                <Button
                  size="sm"
                  prominence="tertiary"
                  icon={SvgEdit}
                  onClick={() => {
                    setActionDraft(item.action);
                    setEditingAction(true);
                  }}
                >
                  Alterar
                </Button>
              )}
            </span>
          )}
          <Pairs
            items={[
              [
                "Responsável",
                owner || `A definir (sugerido: ${item.suggested_area})`,
              ],
              ["Prazo", item.due_date ? brDate(item.due_date) : "A definir"],
              ["Verificação", item.verify],
              ...(item.decision_reason
                ? ([["Risco aceito", item.decision_reason]] as [
                    string,
                    string,
                  ][])
                : []),
            ]}
          />
          <ul className="tp-timeline" aria-label="Histórico do caso">
            {item.timeline.map((entry, index) => (
              <li key={`${entry.at}-${index}`}>
                <span
                  className="tp-timeline-dot"
                  data-kind={entry.kind}
                  aria-hidden
                />
                <div className="flex flex-col">
                  <Text font="main-ui-body" color="text-05">
                    {entry.label}
                  </Text>
                  <Text font="secondary-body" color="text-03">
                    {[brDateTime(entry.at), entry.actor, entry.detail]
                      .filter(Boolean)
                      .join(" · ")}
                  </Text>
                </div>
              </li>
            ))}
          </ul>
          {item.fixed_count > 0 && open && (
            <div className="tp-alert" data-tone="info">
              <SvgInfo size={16} className="text-text-03 shrink-0" />
              <Text font="secondary-body" color="text-04">
                {`${item.fixed_count} de ${item.member_count} já foram corrigidos e verificados; o caso fecha quando todos forem.`}
              </Text>
            </div>
          )}
        </Part>
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
        <button
          type="button"
          className="tn-btn ton-focusable"
          data-variant="gold"
          onClick={askAbout}
        >
          <Diamond />
          Perguntar ao TON
        </button>
        {item.situation === "ACCEPTED" && (
          <Button
            prominence="secondary"
            disabled={busy}
            onClick={() => setDeciding("REOPEN")}
          >
            Reabrir
          </Button>
        )}
        {open && (
          <Button
            prominence="secondary"
            disabled={busy}
            onClick={() => setDeciding("ACCEPT_RISK")}
          >
            Aceitar o risco…
          </Button>
        )}
        {open && (
          <Button disabled={busy} onClick={() => setAssigning(true)}>
            {item.owner_area
              ? "Trocar responsável ou prazo"
              : "Definir responsável e prazo"}
          </Button>
        )}
      </div>

      {assigning && (
        <OwnerDialog
          cases={[item]}
          onClose={() => setAssigning(false)}
          onSaved={async () => {
            setAssigning(false);
            await detail.mutate();
          }}
        />
      )}
      {deciding && (
        <ReasonDialog
          title={
            deciding === "ACCEPT_RISK" ? "Aceitar o risco" : "Reabrir o caso"
          }
          intro={
            deciding === "ACCEPT_RISK"
              ? "O caso sai da cobrança, mas continua visível. Diga por que não será corrigido na origem."
              : "O caso volta para a cobrança."
          }
          confirm={deciding === "ACCEPT_RISK" ? "Aceitar o risco" : "Reabrir"}
          onClose={() => setDeciding(null)}
          onConfirm={async (reason) => {
            const done = await apply(
              correctionJson<CaseDetail>("POST", `/cases/${id}/decision`, {
                decision: deciding,
                reason,
              }),
              deciding === "ACCEPT_RISK" ? "Risco aceito." : "Caso reaberto."
            );
            if (done) setDeciding(null);
          }}
        />
      )}
    </>
  );
}

export default function CasePage({ id }: { id: string }) {
  return (
    <PageContainer>
      <Sheet id={id} />
    </PageContainer>
  );
}
