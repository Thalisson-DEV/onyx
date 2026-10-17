"use client";

import { useState } from "react";
import {
  BasicModalFooter,
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
/** Select value that switches the dialog to creating a DRE group too. */
export const NEW_GROUP = "__new_group__";

interface NewNatureDialogProps {
  groups: DreGroupView[];
  defaultGroup?: string | null;
  /** What the person typed in the picker before asking to create it. */
  initialName?: string;
  onClose: () => void;
  onCreated: (nature: NatureView) => void;
}

export default function NewNatureDialog({
  groups,
  defaultGroup,
  initialName,
  onClose,
  onCreated,
}: NewNatureDialogProps) {
  const [name, setName] = useState(initialName ?? "");
  const [group, setGroup] = useState(defaultGroup ?? "");
  const [reason, setReason] = useState("");
  const [groupName, setGroupName] = useState("");
  const [inResult, setInResult] = useState(true);
  const creatingGroup = group === NEW_GROUP;
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const ready =
    name.trim().length >= 2 &&
    group !== "" &&
    (!creatingGroup || groupName.trim().length >= 2);

  async function save() {
    setBusy(true);
    setFailed(false);
    try {
      const nature = await postJson<NatureView>(
        `${CLASSIFICATION_API}/natures`,
        creatingGroup
          ? {
              natureza: name.trim(),
              dre_group_code: "",
              reason: reason.trim(),
              new_group_label: groupName.trim(),
              new_group_in_result: inResult,
            }
          : {
              natureza: name.trim(),
              dre_group_code: group,
              reason: reason.trim(),
            }
      );
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
        <Modal.Header
          title={creatingGroup ? COPY.groupDialogTitle : COPY.dialogTitle}
          description={
            creatingGroup ? COPY.groupDialogIntro : COPY.dialogIntro
          }
          onClose={() => !busy && onClose()}
        />
        <Modal.Body>
          <div className="flex w-full flex-col gap-4">
            <label className="flex flex-col gap-1.5">
              <span className="ton-eyebrow">
                {creatingGroup ? COPY.firstNature : COPY.name}
              </span>
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
                  <InputSingleSelect.Item value={NEW_GROUP}>
                    {COPY.newGroupOption}
                  </InputSingleSelect.Item>
                </InputSingleSelect.Content>
              </InputSingleSelect>
            </div>
            {creatingGroup && (
              <div className="ton-new-group">
                <label className="flex flex-col gap-1.5">
                  <span className="ton-eyebrow">{COPY.groupName}</span>
                  <InputTypeIn
                    value={groupName}
                    placeholder={COPY.groupNamePlaceholder}
                    maxLength={100}
                    onChange={(event) => setGroupName(event.target.value)}
                  />
                </label>
                <div
                  role="radiogroup"
                  aria-label={COPY.groupResult}
                  className="flex flex-col gap-1.5"
                >
                  <span className="ton-eyebrow">{COPY.groupResult}</span>
                  {([true, false] as const).map((value) => (
                    <label
                      key={String(value)}
                      aria-label={value ? COPY.inResult : COPY.outOfResult}
                      className="flex items-start gap-2"
                    >
                      <input
                        type="radio"
                        name="ton-new-group-result"
                        className="ton-checkbox mt-0.5"
                        checked={inResult === value}
                        onChange={() => setInResult(value)}
                      />
                      <span className="flex flex-col">
                        <Text font="main-ui-action" color="text-05">
                          {value ? COPY.inResult : COPY.outOfResult}
                        </Text>
                        <Text font="secondary-body" color="text-03">
                          {value ? COPY.inResultHelp : COPY.outOfResultHelp}
                        </Text>
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            )}
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
          </div>
        </Modal.Body>
        <Modal.Footer>
          <BasicModalFooter
            cancel={
              <Button prominence="secondary" disabled={busy} onClick={onClose}>
                {CLASSIFICATION_COPY.change.cancel}
              </Button>
            }
            submit={
              <Button disabled={!ready || busy} onClick={() => void save()}>
                {busy
                  ? CLASSIFICATION_COPY.saving
                  : creatingGroup
                    ? COPY.saveWithGroup
                    : COPY.save}
              </Button>
            }
          />
        </Modal.Footer>
      </Modal.Content>
    </Modal>
  );
}
