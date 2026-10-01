"use client";

import { Tag } from "@opal/components";
import { getBusinessLabel, getStatusColor } from "@/lib/ton/labels";

interface TonStatusTagProps {
  status: string | null | undefined;
  size?: "sm" | "md";
}

export function TonStatusTag({ status, size = "sm" }: TonStatusTagProps) {
  return (
    <Tag
      title={getBusinessLabel(status)}
      color={getStatusColor(status)}
      size={size}
    />
  );
}

export default TonStatusTag;
