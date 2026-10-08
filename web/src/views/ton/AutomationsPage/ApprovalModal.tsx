"use client";

import { useState } from "react";
import { Button, InputTextArea, Modal, Text } from "@opal/components";
import { SvgUserCheck } from "@opal/icons";
import { AUTOMATIONS_API, COPY, send, type ApprovalView } from "@/lib/ton/automations";

interface ApprovalModalProps {
  approval: ApprovalView | null;
  onClose: () => void;
  onDecided: () => void;
}

export default function ApprovalModal({ approval, onClose, onDecided }: ApprovalModalProps) {
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function decide(outcome: string) {
    if (!approval) return;
    setBusy(true);
    setError(null);
    try {
      await send(`${AUTOMATIONS_API}/approvals/${approval.id}/decide`, { outcome, comment: comment || null });
      setComment("");
      onDecided();
      onClose();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : String(failure));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal open={approval !== null} onOpenChange={(value) => !value && onClose()}>
      <Modal.Content width="md">
        <Modal.Header icon={SvgUserCheck} title={approval?.title ?? ""} description={approval?.automation_name} onClose={onClose} />
        <Modal.Body>
          <div className="flex flex-col gap-3">
            {approval?.details && (
              <div className="ton-auto-approval-details">
                <Text font="main-ui-body" color="text-04">
                  {approval.details}
                </Text>
              </div>
            )}
            <InputTextArea rows={3} autoResize maxRows={8} aria-label={COPY.comment} placeholder={COPY.comment} value={comment} onChange={(event) => setComment(event.target.value)} />
            {error && (
              <Text font="secondary-body" color="text-05">
                {error}
              </Text>
            )}
          </div>
        </Modal.Body>
        <Modal.Footer>
          {(approval?.options ?? []).map((option, index) => (
            <Button key={option} disabled={busy || !approval?.can_decide} prominence={index === 0 ? "primary" : "secondary"} variant={option === "Recusar" ? "danger" : "default"} onClick={() => void decide(option)}>
              {option}
            </Button>
          ))}
        </Modal.Footer>
      </Modal.Content>
    </Modal>
  );
}
