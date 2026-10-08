"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { Route } from "next";
import { Button, InputTextArea, InputTypeIn, Modal, Text } from "@opal/components";
import { SvgPlus, SvgSparkle, SvgWorkflow } from "@opal/icons";
import {
  AUTOMATIONS_API,
  COPY,
  KIND_LABELS,
  send,
  useAutomationCatalog,
  type AutomationDetail,
  type AutomationKind,
  type DraftResult,
} from "@/lib/ton/automations";
import { Field, Select } from "@/views/ton/AutomationsPage/designer/fields";
import { nodeIcon } from "@/views/ton/AutomationsPage/designer/icons";

export type NewMode = "blank" | "template" | "ask";

interface NewAutomationModalProps {
  mode: NewMode | null;
  onClose: () => void;
}

export default function NewAutomationModal({ mode, onClose }: NewAutomationModalProps) {
  const router = useRouter();
  const catalog = useAutomationCatalog();
  const [name, setName] = useState("");
  const [kind, setKind] = useState<AutomationKind>("GENERAL");
  const [template, setTemplate] = useState<string | null>(null);
  const [request, setRequest] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function create() {
    setBusy(true);
    setError(null);
    try {
      if (mode === "ask") {
        const result = await send<DraftResult>(`${AUTOMATIONS_API}/drafts`, { request });
        router.push(result.editor_url as Route);
        return;
      }
      const result = await send<AutomationDetail>(AUTOMATIONS_API, {
        name: name.trim(),
        kind,
        template: mode === "template" ? template : null,
      });
      router.push(`/ton/automacoes/${result.id}/editar` as Route);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : String(failure));
      setBusy(false);
    }
  }

  const title = mode === "ask" ? COPY.askTon : mode === "template" ? COPY.fromTemplate : COPY.blank;
  const ready = mode === "ask" ? request.trim().length >= 10 : name.trim().length >= 3 && (mode !== "template" || template !== null);
  const triggerIcons = new Map((catalog.data?.nodes ?? []).map((spec) => [spec.type, spec.icon]));

  return (
    <Modal open={mode !== null} onOpenChange={(value) => !value && onClose()}>
      <Modal.Content width={mode === "template" ? "lg" : "md"}>
        <Modal.Header icon={mode === "ask" ? SvgSparkle : SvgWorkflow} title={title} description={mode === "ask" ? COPY.askTonHint : mode === "template" ? COPY.templateHint : COPY.blankHint} onClose={onClose} />
        <Modal.Body>
          <div className="flex flex-col gap-4">
            {mode === "ask" ? (
              <InputTextArea rows={6} autoResize maxRows={14} aria-label={COPY.askTon} placeholder={COPY.draftPlaceholder} value={request} onChange={(event) => setRequest(event.target.value)} />
            ) : (
              <>
                {mode === "template" && (
                  <div className="ton-auto-templates" role="radiogroup">
                    {(catalog.data?.templates ?? []).map((item) => {
                      const Icon = nodeIcon(triggerIcons.get(item.trigger_type));
                      return (
                        <button
                          key={item.key}
                          type="button"
                          role="radio"
                          aria-checked={template === item.key}
                          data-active={template === item.key || undefined}
                          className="ton-auto-template ton-focusable"
                          onClick={() => {
                            setTemplate(item.key);
                            setKind(item.kind);
                            if (!name.trim()) setName(item.name);
                          }}
                        >
                          <span className="ton-auto-node-icon">
                            <Icon size={16} />
                          </span>
                          <span className="flex min-w-0 flex-col items-start text-start">
                            <span className="ton-auto-add-label">{item.name}</span>
                            <span className="ton-auto-add-desc">{item.description}</span>
                            <span className="ton-auto-kind-pill">{KIND_LABELS[item.kind]}</span>
                          </span>
                        </button>
                      );
                    })}
                  </div>
                )}
                <Field label={COPY.name} required>
                  <InputTypeIn aria-label={COPY.name} placeholder={COPY.namePlaceholder} value={name} maxLength={120} onChange={(event) => setName(event.target.value)} />
                </Field>
                {mode === "blank" && (
                  <Field label={COPY.type}>
                    <Select value={kind} label={COPY.type} options={(catalog.data?.kinds ?? []).map((item): [string, string] => [item.key, `${item.label} — ${item.description}`])} onChange={(value) => setKind(value as AutomationKind)} />
                  </Field>
                )}
              </>
            )}
            {busy && mode === "ask" && (
              <Text font="secondary-body" color="text-03">
                {COPY.drafting}
              </Text>
            )}
            {error && (
              <Text font="secondary-body" color="text-05">
                {error}
              </Text>
            )}
          </div>
        </Modal.Body>
        <Modal.Footer>
          <Button prominence="secondary" onClick={onClose}>
            {COPY.cancel}
          </Button>
          <Button icon={mode === "ask" ? SvgSparkle : SvgPlus} disabled={!ready || busy} onClick={() => void create()}>
            {mode === "ask" ? COPY.draftCreate : COPY.create}
          </Button>
        </Modal.Footer>
      </Modal.Content>
    </Modal>
  );
}
