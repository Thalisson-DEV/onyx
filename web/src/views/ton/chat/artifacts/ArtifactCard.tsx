"use client";

import { useEffect } from "react";
import { Button, Text } from "@opal/components";
import {
  SvgBarChart,
  SvgFileText,
  SvgSlidesFile,
  SvgDownload,
} from "@opal/icons";
import type { IconFunctionComponent } from "@opal/types";
import { COPY } from "@/lib/ton/copy";
import {
  artifactVersion,
  useArtifactStore,
  type ArtifactKind,
  type TonArtifact,
} from "@/lib/ton/artifacts";
import { printArtifact } from "@/views/ton/chat/artifacts/print";

const ART = COPY.artifacts;

export const ARTIFACT_ICONS: Record<ArtifactKind, IconFunctionComponent> = {
  painel: SvgBarChart,
  apresentacao: SvgSlidesFile,
  relatorio: SvgFileText,
};

/** A just-built artifact opens by itself; an old one waits for a click. */
const FRESH_MS = 3 * 60_000;

function meta(artifact: TonArtifact): string {
  if (artifact.artifact_kind === "apresentacao")
    return ART.slides(artifact.slides.length);
  const charts = artifact.blocks.filter(
    (block) => block.type === "barras" || block.type === "linha"
  ).length;
  const tables = artifact.blocks.filter(
    (block) => block.type === "tabela"
  ).length;
  return [
    charts ? ART.charts(charts) : null,
    tables ? ART.tables(tables) : null,
    artifact.subtitle,
  ]
    .filter(Boolean)
    .join(" · ");
}

/** The artifact in the conversation: what it is, and where it opens. */
export default function ArtifactCard({ artifact }: { artifact: TonArtifact }) {
  const register = useArtifactStore((state) => state.register);
  const show = useArtifactStore((state) => state.show);
  const versions = useArtifactStore((state) => state.versions);
  const isOpen = useArtifactStore(
    (state) => state.open?.createdAt === artifact.created_at
  );
  const seen = useArtifactStore((state) => !!state.seen[artifact.created_at]);
  const Icon = ARTIFACT_ICONS[artifact.artifact_kind];

  useEffect(() => {
    register(artifact);
  }, [artifact, register]);

  useEffect(() => {
    const age = Date.now() - new Date(artifact.created_at).getTime();
    if (!seen && age < FRESH_MS) show(artifact);
    // Only on arrival: closing the panel must not reopen it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const version = artifactVersion(versions, artifact);
  return (
    <div className="tn-art-card" data-open={isOpen || undefined}>
      <span className="tn-art-card-icon" aria-hidden>
        <Icon size={20} />
      </span>
      <span className="flex flex-1 min-w-0 flex-col">
        <span className="tn-art-kind">{`${ART.kinds[artifact.artifact_kind]} · v${version}`}</span>
        <Text font="main-ui-action" color="text-05">
          {artifact.title}
        </Text>
        <Text font="secondary-body" color="text-03">
          {meta(artifact)}
        </Text>
      </span>
      <Button
        prominence="tertiary"
        size="sm"
        icon={SvgDownload}
        tooltip={ART.print}
        aria-label={ART.print}
        onClick={() => {
          show(artifact);
          printArtifact(artifact);
        }}
      />
      <Button
        size="sm"
        prominence={isOpen ? "secondary" : "primary"}
        onClick={() => show(artifact)}
      >
        {isOpen ? ART.opened : ART.open}
      </Button>
    </div>
  );
}
