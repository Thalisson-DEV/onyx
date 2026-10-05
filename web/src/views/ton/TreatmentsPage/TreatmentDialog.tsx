"use client";

import { useState, type ReactNode } from "react";
import {
  Button,
  InputSingleSelect,
  InputTextArea,
  InputTypeIn,
  Modal,
  Text,
} from "@opal/components";
import { postJson } from "@/lib/ton/classification";
import {
  TREATMENTS_API,
  TREATMENTS_COPY,
  treatmentKey,
  type TreatmentCreate,
  type TreatmentEffect,
  type TreatmentTable,
  type TreatmentView,
} from "@/lib/ton/treatments";

const COPY = TREATMENTS_COPY.dialog;
const ANY = "__any__";
const EFFECTS: TreatmentEffect[] = [
  "EXCLUDE",
  "RECLASSIFY",
  "REPLACE_BY_SOURCE",
];

interface TreatmentDialogProps {
  table: TreatmentTable;
  /** Set for a new version of an existing treatment. */
  base: TreatmentView | null;
  onClose: () => void;
  onSaved: (treatment: TreatmentView) => void;
}

/** "2026-04-01" <-> "2026-04" for the month input. */
function toMonth(value: string | null): string {
  return value ? value.slice(0, 7) : "";
}

function fromMonth(value: string): string | null {
  return value ? `${value}-01` : null;
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="ton-eyebrow">{label}</span>
      {children}
    </div>
  );
}

function Select({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
}) {
  return (
    <InputSingleSelect value={value} onValueChange={onChange}>
      <InputSingleSelect.Trigger placeholder={label} aria-label={label} />
      <InputSingleSelect.Content>
        {options.map((option) => (
          <InputSingleSelect.Item key={option.value} value={option.value}>
            {option.label}
          </InputSingleSelect.Item>
        ))}
      </InputSingleSelect.Content>
    </InputSingleSelect>
  );
}

export default function TreatmentDialog({
  table,
  base,
  onClose,
  onSaved,
}: TreatmentDialogProps) {
  const [title, setTitle] = useState(base?.title ?? "");
  const [accountId, setAccountId] = useState(base?.account_id ?? "");
  const [effect, setEffect] = useState<TreatmentEffect>(
    base?.effect ?? "EXCLUDE"
  );
  const [targetId, setTargetId] = useState(base?.target_account_id ?? "");
  const [unitId, setUnitId] = useState(base?.unit_id ?? ANY);
  const [from, setFrom] = useState(toMonth(base?.period_from ?? null));
  const [to, setTo] = useState(toMonth(base?.period_to ?? null));
  const [blocked, setBlocked] = useState(
    base ? base.status === "BLOCKED" : false
  );
  const [requiredSource, setRequiredSource] = useState(
    base?.required_source ?? ""
  );
  const [justification, setJustification] = useState("");
  const [evidence, setEvidence] = useState("");
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  const mustWait = effect === "REPLACE_BY_SOURCE";
  const waiting = blocked || mustWait;
  const key = base?.treatment_key ?? treatmentKey(title);
  const ready =
    title.trim().length >= 3 &&
    key.length > 0 &&
    accountId !== "" &&
    (effect !== "RECLASSIFY" || (targetId !== "" && targetId !== accountId)) &&
    (!waiting || requiredSource.trim().length >= 3) &&
    (!from || !to || from <= to) &&
    justification.trim().length >= 3 &&
    evidence.trim().length >= 3;

  async function save() {
    setBusy(true);
    setFailed(false);
    const request: TreatmentCreate = {
      treatment_key: key,
      title: title.trim(),
      status: waiting ? "BLOCKED" : "ACTIVE",
      effect,
      account_id: accountId,
      unit_id: unitId === ANY ? null : unitId,
      period_from: fromMonth(from),
      period_to: fromMonth(to),
      target_account_id: effect === "RECLASSIFY" ? targetId : null,
      required_source: waiting ? requiredSource.trim() : null,
      justification: justification.trim(),
      evidence: evidence.trim(),
    };
    try {
      onSaved(await postJson<TreatmentView>(TREATMENTS_API, request));
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  const accounts = table.accounts.map((item) => ({
    value: item.id,
    label: item.label,
  }));

  return (
    <Modal
      open
      onOpenChange={(open) => {
        if (!open && !busy) onClose();
      }}
    >
      <Modal.Content width="md">
        <Modal.Header
          title={base ? COPY.versionTitle(base.title) : COPY.createTitle}
        />
        <Modal.Body>
          <div className="flex flex-col gap-4">
            <Text as="p" font="secondary-body" color="text-03">
              {COPY.intro}
            </Text>
            <Field label={COPY.title}>
              <InputTypeIn
                value={title}
                placeholder={COPY.titlePlaceholder}
                maxLength={200}
                aria-label={COPY.title}
                onChange={(event) => setTitle(event.target.value)}
              />
            </Field>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Field label={COPY.nature}>
                <Select
                  label={COPY.nature}
                  value={accountId}
                  options={accounts}
                  onChange={setAccountId}
                />
              </Field>
              <Field label={COPY.effect}>
                <Select
                  label={COPY.effect}
                  value={effect}
                  options={EFFECTS.map((item) => ({
                    value: item,
                    label: TREATMENTS_COPY.effect[item],
                  }))}
                  onChange={(value) => {
                    const picked = EFFECTS.find((item) => item === value);
                    if (picked) setEffect(picked);
                  }}
                />
              </Field>
            </div>
            <Text as="p" font="secondary-body" color="text-03">
              {TREATMENTS_COPY.effectHelp[effect]}
            </Text>
            {effect === "RECLASSIFY" && (
              <Field label={COPY.target}>
                <Select
                  label={COPY.target}
                  value={targetId}
                  options={accounts.filter((item) => item.value !== accountId)}
                  onChange={setTargetId}
                />
              </Field>
            )}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <Field label={COPY.unit}>
                <Select
                  label={COPY.unit}
                  value={unitId}
                  options={[
                    { value: ANY, label: COPY.any },
                    ...table.units.map((item) => ({
                      value: item.id,
                      label: item.label,
                    })),
                  ]}
                  onChange={setUnitId}
                />
              </Field>
              <Field label={`${COPY.period} · ${COPY.from}`}>
                <InputTypeIn
                  type="month"
                  value={from}
                  aria-label={COPY.from}
                  onChange={(event) => setFrom(event.target.value)}
                />
              </Field>
              <Field label={`${COPY.period} · ${COPY.to}`}>
                <InputTypeIn
                  type="month"
                  value={to}
                  aria-label={COPY.to}
                  onChange={(event) => setTo(event.target.value)}
                />
              </Field>
            </div>
            {!mustWait && (
              <Field label={COPY.apply}>
                <Select
                  label={COPY.apply}
                  value={blocked ? "BLOCKED" : "ACTIVE"}
                  options={[
                    { value: "ACTIVE", label: COPY.applyNow },
                    { value: "BLOCKED", label: COPY.applyBlocked },
                  ]}
                  onChange={(value) => setBlocked(value === "BLOCKED")}
                />
              </Field>
            )}
            {waiting && (
              <Field label={COPY.requiredSource}>
                <InputTypeIn
                  value={requiredSource}
                  placeholder={COPY.requiredSourcePlaceholder}
                  maxLength={500}
                  aria-label={COPY.requiredSource}
                  onChange={(event) => setRequiredSource(event.target.value)}
                />
              </Field>
            )}
            <Field label={COPY.justification}>
              <InputTextArea
                value={justification}
                rows={2}
                maxLength={2000}
                aria-label={COPY.justification}
                onChange={(event) => setJustification(event.target.value)}
              />
            </Field>
            <Field label={COPY.evidence}>
              <InputTypeIn
                value={evidence}
                placeholder={COPY.evidencePlaceholder}
                maxLength={1000}
                aria-label={COPY.evidence}
                onChange={(event) => setEvidence(event.target.value)}
              />
            </Field>
            {failed && (
              <span role="alert" className="text-status-error-05">
                <Text font="secondary-body" color="inherit">
                  {COPY.failed}
                </Text>
              </span>
            )}
            <div className="flex justify-end gap-2">
              <Button prominence="tertiary" disabled={busy} onClick={onClose}>
                {COPY.cancel}
              </Button>
              <Button disabled={!ready || busy} onClick={() => void save()}>
                {busy ? COPY.saving : COPY.save}
              </Button>
            </div>
          </div>
        </Modal.Body>
      </Modal.Content>
    </Modal>
  );
}
