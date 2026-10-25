"use client";

import { SideModal } from "@/views/ton/components/kit";
import { useState } from "react";
import { Button, InputTypeIn, Text } from "@opal/components";
import { toast } from "@opal/layouts";
import {
  OWNER_AREAS,
  caseNumber,
  correctionJson,
  type CaseRow,
} from "@/lib/ton/correction";
import { errorText } from "@/lib/ton/payables";
import { PatternField } from "@/views/ton/components/pattern";
import { Select } from "@/views/ton/PayablesPage/fields";

interface OwnerDialogProps {
  cases: CaseRow[];
  onClose: () => void;
  onSaved: () => void;
}

const DEADLINE_TEXT: Record<string, string> = {
  CRITICAL: "crítica: 5 dias úteis",
  HIGH: "alta: 15 dias",
  MEDIUM: "média: 30 dias",
  MONITORING: "monitoramento: 30 dias",
};

/** Who fixes the selected cases and by when; the régua suggests the deadline. */
export default function OwnerDialog({
  cases,
  onClose,
  onSaved,
}: OwnerDialogProps) {
  const first = cases[0];
  const suggested = cases.every(
    (row) => row.suggested_area === first?.suggested_area
  )
    ? first?.suggested_area
    : undefined;
  const [area, setArea] = useState(first?.owner_area ?? suggested ?? "");
  const [name, setName] = useState(first?.owner_name ?? "");
  const [due, setDue] = useState("");
  const [busy, setBusy] = useState(false);
  const levels = Array.from(new Set(cases.map((row) => row.criticality)));

  async function save() {
    setBusy(true);
    try {
      await correctionJson("POST", "/cases/owner", {
        ids: cases.map((row) => row.id),
        owner_area: area,
        owner_name: name.trim() || null,
        due_date: due || null,
      });
      toast.success(
        cases.length === 1
          ? "Responsável definido."
          : `Responsável definido em ${cases.length} casos.`
      );
      onSaved();
    } catch (error) {
      toast.error(errorText(error, "Não foi possível salvar."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <SideModal open onOpenChange={(open) => !open && !busy && onClose()}>
      <SideModal.Content width="md">
        <SideModal.Header
          title="Responsável e prazo"
          description={
            cases.length === 1 && first
              ? `${caseNumber(first.number)} · ${first.title}`
              : `${cases.length} casos selecionados`
          }
          onClose={() => !busy && onClose()}
        />
        <SideModal.Body>
          <div className="w-full tp-form-section">
            <PatternField
              label="Área"
              span={4}
              note={
                suggested
                  ? `O TON sugere ${suggested} para este tipo de caso.`
                  : null
              }
            >
              <Select
                value={area}
                label="Área"
                placeholder="Escolha a área"
                searchAbove={99}
                options={OWNER_AREAS.map((item) => ({
                  value: item,
                  label: item,
                }))}
                onChange={setArea}
              />
            </PatternField>
            <PatternField label="Pessoa" span={4} note="Opcional por enquanto">
              <InputTypeIn
                value={name}
                maxLength={120}
                aria-label="Pessoa responsável"
                placeholder="Nome de quem corrige"
                onChange={(event) => setName(event.target.value)}
              />
            </PatternField>
            <PatternField
              label="Prazo"
              span={4}
              note={`Vazio: prazo da régua (${levels.map((level) => DEADLINE_TEXT[level]).join("; ")}), contado a partir de hoje.`}
            >
              <InputTypeIn
                type="date"
                value={due}
                aria-label="Prazo"
                onChange={(event) => setDue(event.target.value)}
              />
            </PatternField>
          </div>
          {cases.length > 1 && (
            <Text as="p" font="secondary-body" color="text-03">
              O mesmo responsável vale para todos os casos selecionados.
            </Text>
          )}
        </SideModal.Body>
        <SideModal.Footer>
          <Button prominence="secondary" disabled={busy} onClick={onClose}>
            Cancelar
          </Button>
          <Button disabled={busy || !area} onClick={() => void save()}>
            {busy ? "Salvando…" : "Salvar"}
          </Button>
        </SideModal.Footer>
      </SideModal.Content>
    </SideModal>
  );
}
