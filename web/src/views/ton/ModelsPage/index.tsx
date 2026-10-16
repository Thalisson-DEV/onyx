"use client";

import { SvgLock } from "@opal/icons";
import { useUser } from "@/providers/UserProvider";
import { COPY } from "@/lib/ton/copy";
import { LanguageModelsSettings } from "@/views/admin/LanguageModelsPage";
import {
  BackLink,
  EmptyState,
  PageContainer,
  PageHeader,
} from "@/views/ton/components/ui";

/**
 * The upstream language-model settings (providers, keys, default model)
 * mounted inside the TON shell, so the operator never leaves TON to configure
 * the assistant's AI provider. Same API, same provider modals.
 */
export default function ModelsPage() {
  const { hasAdminAccess } = useUser();

  if (!hasAdminAccess) {
    return (
      <PageContainer>
        <EmptyState
          icon={SvgLock}
          title={COPY.admin.noAccessTitle}
          description={COPY.admin.noAccessDescription}
        />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <BackLink href="/ton/administracao" label={COPY.admin.back} />
      <PageHeader
        eyebrow={COPY.admin.models.eyebrow}
        title={COPY.admin.models.title}
        description={COPY.admin.models.pageDescription}
      />
      <div className="flex flex-col gap-6">
        <LanguageModelsSettings showCostOverrides={false} />
      </div>
    </PageContainer>
  );
}
