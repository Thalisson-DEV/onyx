"use client";

import { useState } from "react";
import { Button, LineItemButton, Popover } from "@opal/components";
import { SvgSquarePlus, SvgX } from "@opal/icons";
import { COPY } from "@/lib/ton/copy";
import {
  focusTonComposer,
  useCreateMode,
  type ArtifactKind,
} from "@/lib/ton/artifacts";
import { ARTIFACT_ICONS } from "@/views/ton/chat/artifacts/ArtifactCard";

const CHAT = COPY.chat;
export const CREATE_ITEMS = CHAT.create.map((item) => ({
  ...item,
  // SAFETY: the copy lists exactly the three artifact kinds.
  key: item.key as ArtifactKind,
}));

/** Mark the next message as a dashboard, deck or report request. */
export function chooseCreate(kind: ArtifactKind): void {
  useCreateMode.getState().setKind(kind);
  focusTonComposer();
}

/**
 * "Criar" in the composer marks what the answer must become; the person
 * writes the ask. The mark stays on the composer until it is sent or cleared.
 */
export default function CreateMenu() {
  const kind = useCreateMode((state) => state.kind);
  const setKind = useCreateMode((state) => state.setKind);
  const [open, setOpen] = useState(false);
  const chosen = CREATE_ITEMS.find((item) => item.key === kind);
  return (
    <span className="tn-create">
      <Popover open={open} onOpenChange={setOpen}>
        <Popover.Trigger asChild>
          <Button
            prominence={chosen ? "secondary" : "tertiary"}
            size="sm"
            icon={chosen ? ARTIFACT_ICONS[chosen.key] : SvgSquarePlus}
            aria-pressed={chosen ? true : undefined}
          >
            {chosen ? chosen.chip : CHAT.composer.create}
          </Button>
        </Popover.Trigger>
        <Popover.Content side="top" align="start" width="xl">
          <Popover.Menu>
            {CREATE_ITEMS.map((item) => (
              <LineItemButton
                key={item.key}
                sizePreset="main-ui"
                rounding={2}
                icon={ARTIFACT_ICONS[item.key]}
                title={item.label}
                description={item.description}
                selectVariant="select-heavy"
                state={item.key === kind ? "selected" : "empty"}
                onClick={() => {
                  setOpen(false);
                  chooseCreate(item.key);
                }}
              />
            ))}
          </Popover.Menu>
        </Popover.Content>
      </Popover>
      {chosen && (
        <Button
          prominence="tertiary"
          size="sm"
          icon={SvgX}
          tooltip={CHAT.composer.clearCreate}
          aria-label={CHAT.composer.clearCreate}
          onClick={() => setKind(null)}
        />
      )}
    </span>
  );
}
