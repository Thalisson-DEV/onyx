import type { ClassificationStatus } from "@/lib/ton/classification";
import type { TonTone } from "@/views/ton/components/ui";

/** Select value that opens the new-natureza dialog instead of picking one. */
export const NEW_NATURE = "__new_nature__";

export const STATUS_TONE: Record<ClassificationStatus, TonTone> = {
  PENDING: "danger",
  AWAITING_CONFIRMATION: "warning",
  CONFIRMED: "success",
};

export const STATUS_LABEL: Record<ClassificationStatus, string> = {
  PENDING: "Sem natureza",
  AWAITING_CONFIRMATION: "Aguardando decisão",
  CONFIRMED: "Confirmada",
};
