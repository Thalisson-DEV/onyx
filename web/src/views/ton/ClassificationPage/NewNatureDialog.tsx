"use client";

import { useState } from "react";
import {
  Button,
  InputSingleSelect,
  InputTextArea,
  InputTypeIn,
  Modal,
  Text,
} from "@opal/components";
import {
  CLASSIFICATION_API,
  CLASSIFICATION_COPY,
  postJson,
  type DreGroupView,
  type NatureView,
} from "@/lib/ton/classification";

const COPY = CLASSIFICATION_COPY.natures;

interface NewNatureDialogProps {
  groups: DreGroupView[];
  defaultGroup?: string | null;
  onClose: () => void;
  onCreated: (nature: NatureView) => void;
}

export default function NewNatureDialog({
  groups,
  defaultGroup,
  onClose,
  onCreated,
}: NewNatureDialogProps) {
  const [name, setName] = useState("");
  const [group, setGroup] = useState(defaultGroup ?? "");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const ready =
    name.trim().length >= 2 && group !== "" && reason.trim().length >= 3;

  async function save() {
    setBusy(true);
    setFailed(false);
    try {
      const nature = await postJson<NatureView>(`${CLASSIFICATION_API}/natures`, {
        natureza: name.trim(),
        dre_group_code: group,
        reason: reason.trim(),
      });
      onCreated(nature);
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open
      onOpenChange={(open) => {
        if (!open && !busy) onClose();
      }}
    >
      <Modal.Content width="sm">
        <Modal.Header title={COPY.dialogTitle} />
        <Modal.Body>
          <div className="flex flex-col gap-4">
            <Text as="p" font="secondary-body" color="text-03">
              {COPY.dialogIntro}
            </Text>
            <label className="flex flex-col gap-1.5">
              <span className="ton-eyebrow">{COPY.name}</span>
              <InputTypeIn
                value={name}
                placeholder={COPY.namePlaceholder}
                maxLength={100}
                onChange={(event) => setName(event.target.value)}
              />
            </label>
            <div className="flex flex-col gap-1.5">
              <span className="ton-eyebrow">{COPY.group}</span>
              <InputSingleSelect value={group} onValueChange={setGroup}>
                <InputSingleSelect.Trigger
                  placeholder={COPY.group}
                  aria-label={COPY.group}
                />
                <InputSingleSelect.Content>
                  {groups.map((item) => (
                    <InputSingleSelect.Item key={item.code} value={item.code}>
                      {item.label}
                    </InputSingleSelect.Item>
                  ))}
                </InputSingleSelect.Content>
              </InputSingleSelect>
            </div>
            <label className="flex flex-col gap-1.5">
              <span className="ton-eyebrow">{COPY.reason}</span>
              <InputTextArea
                value={reason}
                rows={2}
                maxLength={400}
                onChange={(event) => setReason(event.target.value)}
              />
            </label>
            {failed && (
              <span role="alert" className="text-status-error-05">
                <Text font="secondary-body" color="inherit">
                  {COPY.failed}
                </Text>
              </span>
            )}
            <div className="flex justify-end gap-2">
              <Button prominence="tertiary" disabled={busy} onClick={onClose}>
                {CLASSIFICATION_COPY.panel.cancel}
              </Button>
              <Button disabled={!ready || busy} onClick={() => void save()}>
                {busy ? CLASSIFICATION_COPY.panel.saving : COPY.save}
              </Button>
            </div>
          </div>
        </Modal.Body>
      </Modal.Content>
    </Modal>
  );
}
