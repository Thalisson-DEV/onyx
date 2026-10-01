"use client";

import DrePage from "@/views/admin/DrePage";
import { COPY } from "@/lib/ton/copy";
import ClosingFrame from "@/views/ton/components/ClosingFrame";
import { TonCard } from "@/views/ton/components/ui";

export default function TonDrePage() {
  return (
    <ClosingFrame
      active="dre"
      title={COPY.dre.title}
      description={COPY.dre.description}
      wide
    >
      <TonCard className="p-5 sm:p-6" as="div">
        <DrePage embedded />
      </TonCard>
    </ClosingFrame>
  );
}
