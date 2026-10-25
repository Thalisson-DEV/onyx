"use client";

import { SideModal } from "@/views/ton/components/kit";
import useSWR from "swr";
import { Button, CopyButton, Text } from "@opal/components";
import { SvgInfo } from "@opal/icons";
import { correctionJson, type ReminderDraft } from "@/lib/ton/correction";
import { ErrorState, LoadingBlock } from "@/views/ton/components/ui";

/**
 * One message per owner. Sending waits for the e-mail domain; until then the
 * Controladoria copies the text.
 */
export default function ReminderDialog({
  ids,
  onClose,
}: {
  ids: string[];
  onClose: () => void;
}) {
  const drafts = useSWR(["reminder", ...ids], () =>
    correctionJson<ReminderDraft[]>("POST", "/cases/reminder", { ids })
  );
  const notice = drafts.data?.find((draft) => !draft.can_send)?.why_not;
  return (
    <SideModal open onOpenChange={(open) => !open && onClose()}>
      <SideModal.Content width="lg">
        <SideModal.Header
          title="Cobrar por e-mail"
          description="Uma mensagem por responsável, com os casos e o que fazer."
          onClose={onClose}
        />
        <SideModal.Body>
          <div className="w-full flex flex-col gap-4">
            {drafts.isLoading && (
              <LoadingBlock label="Montando as mensagens…" lines={5} />
            )}
            {drafts.error && (
              <ErrorState message="Não foi possível montar as mensagens." />
            )}
            {notice && (
              <div className="tp-alert" data-tone="info">
                <SvgInfo size={16} className="text-text-03 shrink-0" />
                <Text font="secondary-body" color="text-04">
                  {notice}
                </Text>
              </div>
            )}
            {drafts.data?.length === 0 && (
              <Text as="p" font="secondary-body" color="text-03">
                Os casos selecionados já estão corrigidos ou com risco aceito.
              </Text>
            )}
            {drafts.data?.map((draft) => (
              <section key={draft.owner} className="ton-card tp-section">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-col">
                    <Text font="secondary-body" color="text-03">
                      {`Para: ${draft.owner}`}
                    </Text>
                    <Text font="main-ui-action" color="text-05">
                      {draft.subject}
                    </Text>
                  </div>
                  <CopyButton
                    size="sm"
                    prominence="secondary"
                    getCopyText={() => `${draft.subject}\n\n${draft.body}`}
                  >
                    Copiar mensagem
                  </CopyButton>
                </div>
                <pre className="tp-mail">{draft.body}</pre>
              </section>
            ))}
          </div>
        </SideModal.Body>
        <SideModal.Footer>
          <Button prominence="secondary" onClick={onClose}>
            Fechar
          </Button>
          <Button disabled>Enviar</Button>
        </SideModal.Footer>
      </SideModal.Content>
    </SideModal>
  );
}
