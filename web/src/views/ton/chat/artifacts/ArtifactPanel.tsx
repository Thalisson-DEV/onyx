"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Button, Text } from "@opal/components";
import {
  SvgArrowLeft,
  SvgArrowRight,
  SvgDownload,
  SvgMaximize2,
  SvgPlayCircle,
  SvgSpreadsheetFile,
  SvgX,
} from "@opal/icons";
import { cn } from "@opal/utils";
import { COPY, formatRelativeDateTime } from "@/lib/ton/copy";
import {
  artifactTables,
  composeTonMessage,
  downloadText,
  slugify,
  toCsv,
  useArtifactStore,
  type TonArtifact,
} from "@/lib/ton/artifacts";
import { Diamond } from "@/views/ton/components/kit";
import {
  ArtifactBody,
  BlockView,
  SlideView,
} from "@/views/ton/chat/artifacts/ArtifactView";
import { ARTIFACT_ICONS } from "@/views/ton/chat/artifacts/ArtifactCard";
import { printArtifact } from "@/views/ton/chat/artifacts/print";

const ART = COPY.artifacts;
type Tab = "view" | "data" | "versions";

function Presenter({
  artifact,
  start,
  onExit,
}: {
  artifact: TonArtifact;
  start: number;
  onExit: (slide: number) => void;
}) {
  const [index, setIndex] = useState(start);
  const [host, setHost] = useState<HTMLElement | null>(null);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => setHost(document.body), []);
  const total = artifact.slides.length;
  const exit = useRef(onExit);
  const current = useRef(index);
  useEffect(() => {
    exit.current = onExit;
    current.current = index;
  });
  // A modal show: the arrows and Esc drive it wherever the focus is.
  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    node.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") exit.current(current.current);
      else if (["ArrowRight", " ", "PageDown"].includes(event.key))
        setIndex((value) => Math.min(value + 1, total - 1));
      else if (["ArrowLeft", "PageUp"].includes(event.key))
        setIndex((value) => Math.max(value - 1, 0));
      else return;
      event.preventDefault();
    };
    window.addEventListener("keydown", onKey);
    // Full screen when the browser allows it; leaving it (Esc) ends the show.
    let entered = false;
    const onFullscreen = () => {
      if (document.fullscreenElement) entered = true;
      else if (entered) exit.current(current.current);
    };
    document.addEventListener("fullscreenchange", onFullscreen);
    node.requestFullscreen?.().catch(() => undefined);
    return () => {
      window.removeEventListener("keydown", onKey);
      document.removeEventListener("fullscreenchange", onFullscreen);
      if (document.fullscreenElement) void document.exitFullscreen();
    };
  }, [total, host]);
  const slide = artifact.slides[index];
  if (!host) return null;
  // On <body>: an animated ancestor would trap a fixed overlay inside it.
  return createPortal(
    <div
      ref={ref}
      className="tn-art-presenter"
      role="dialog"
      aria-modal="true"
      aria-label={artifact.title}
      tabIndex={-1}
    >
      <div className="tn-art-presenter-stage">
        {slide && <SlideView slide={slide} index={index} total={total} />}
      </div>
      <div className="tn-art-presenter-bar">
        <Button
          prominence="tertiary"
          icon={SvgArrowLeft}
          aria-label={ART.presenter.prev}
          disabled={index === 0}
          onClick={() => setIndex(index - 1)}
        />
        <span>{`${index + 1} / ${total}`}</span>
        <Button
          prominence="tertiary"
          icon={SvgArrowRight}
          aria-label={ART.presenter.next}
          disabled={index >= total - 1}
          onClick={() => setIndex(index + 1)}
        />
        <span className="tn-art-presenter-hint">{ART.presenter.hint}</span>
        <Button prominence="secondary" onClick={() => onExit(index)}>
          {ART.presenter.exit}
        </Button>
      </div>
    </div>,
    host
  );
}

/**
 * The open artifact beside the conversation: read it, take its data, see
 * its versions, export or present it, or ask the TON to adjust it.
 */
export default function ArtifactPanel() {
  const open = useArtifactStore((state) => state.open);
  const versions = useArtifactStore((state) => state.versions);
  const expanded = useArtifactStore((state) => state.expanded);
  const setExpanded = useArtifactStore((state) => state.setExpanded);
  const show = useArtifactStore((state) => state.show);
  const close = useArtifactStore((state) => state.close);
  const [tab, setTab] = useState<Tab>("view");
  const [slide, setSlide] = useState(0);
  const [presenting, setPresenting] = useState(false);

  const list = open ? (versions[open.id] ?? []) : [];
  const artifact = list.find((item) => item.created_at === open?.createdAt);
  const createdAt = artifact?.created_at;
  useEffect(() => {
    setTab("view");
    setSlide(0);
  }, [createdAt]);

  if (!artifact) return null;
  const version = list.indexOf(artifact) + 1;
  const Icon = ARTIFACT_ICONS[artifact.artifact_kind];
  const tables = artifactTables(artifact);
  const isDeck = artifact.artifact_kind === "apresentacao";

  const downloadData = () => {
    const first = tables[0];
    if (!first) return;
    const rows =
      tables.length === 1
        ? first.rows
        : tables.flatMap((table) => [
            [table.title],
            table.columns,
            ...table.rows,
            [],
          ]);
    downloadText(
      `${slugify(artifact.title)}.csv`,
      toCsv(tables.length === 1 ? first.columns : [], rows)
    );
  };

  return (
    <aside
      className={cn("tn-art-panel", expanded && "tn-art-panel-expanded")}
      aria-label={ART.region}
    >
      <header className="tn-art-panel-head">
        <span className="tn-art-card-icon" data-size="sm" aria-hidden>
          <Icon size={16} />
        </span>
        <span className="flex flex-1 min-w-0 flex-col">
          <span className="tn-art-kind">{`${ART.kinds[artifact.artifact_kind]} · v${version}`}</span>
          <span className="tn-art-panel-title" title={artifact.title}>
            {artifact.title}
          </span>
        </span>
        <span className="tn-art-panel-actions">
          {isDeck && (
            <Button
              size="sm"
              prominence="secondary"
              icon={SvgPlayCircle}
              onClick={() => setPresenting(true)}
            >
              {ART.present}
            </Button>
          )}
          {tables.length > 0 && (
            <Button
              size="sm"
              prominence="tertiary"
              icon={SvgSpreadsheetFile}
              tooltip={ART.csv}
              aria-label={ART.csv}
              onClick={downloadData}
            />
          )}
          <Button
            size="sm"
            prominence="tertiary"
            icon={SvgDownload}
            tooltip={ART.print}
            aria-label={ART.print}
            onClick={() => printArtifact(artifact)}
          />
          <Button
            size="sm"
            prominence="tertiary"
            icon={SvgMaximize2}
            tooltip={expanded ? ART.collapse : ART.expand}
            aria-label={expanded ? ART.collapse : ART.expand}
            aria-pressed={expanded}
            onClick={() => setExpanded(!expanded)}
          />
          <Button
            size="sm"
            prominence="tertiary"
            icon={SvgX}
            tooltip={ART.close}
            aria-label={ART.close}
            onClick={close}
          />
        </span>
      </header>
      <div className="tn-art-tabs" role="tablist" aria-label={ART.region}>
        {(["view", "data", "versions"] satisfies Tab[]).map((key) => (
          // Tabs are a segmented row; Opal has no tab primitive for panels.
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={tab === key}
            className="ton-focusable"
            onClick={() => setTab(key)}
          >
            {key === "versions"
              ? ART.tabs.versions(list.length)
              : ART.tabs[key]}
          </button>
        ))}
      </div>
      <div className="tn-art-panel-body">
        {tab === "view" && (
          <div className="tn-art-print">
            <ArtifactBody
              artifact={artifact}
              slide={slide}
              onSlide={setSlide}
            />
          </div>
        )}
        {tab === "data" && (
          <div className="flex flex-col gap-4">
            {tables.length === 0 && (
              <Text font="secondary-body" color="text-03">
                {ART.noData}
              </Text>
            )}
            {tables.map((table, index) => (
              <BlockView
                key={index}
                block={{
                  type: "tabela",
                  title: table.title,
                  columns: table.columns,
                  rows: table.rows,
                }}
              />
            ))}
            <section className="flex flex-col gap-2">
              <Text font="secondary-action" color="text-04">
                {ART.sources}
              </Text>
              {artifact.sources.length ? (
                <span className="flex flex-wrap gap-1.5">
                  {artifact.sources.map((source) => (
                    <span key={source} className="tn-art-source">
                      {source}
                    </span>
                  ))}
                </span>
              ) : (
                <Text font="secondary-body" color="text-03">
                  {ART.noSources}
                </Text>
              )}
            </section>
          </div>
        )}
        {tab === "versions" && (
          <div className="flex flex-col gap-3">
            <ol className="tn-art-versions">
              {[...list].reverse().map((item) => {
                const number = list.indexOf(item) + 1;
                const current = item.created_at === artifact.created_at;
                return (
                  <li key={item.created_at} data-current={current || undefined}>
                    <span className="flex flex-1 min-w-0 flex-col">
                      <Text font="main-ui-action" color="text-05">
                        {`v${number} · ${item.title}`}
                      </Text>
                      <Text font="secondary-body" color="text-03">
                        {formatRelativeDateTime(item.created_at)}
                      </Text>
                    </span>
                    {current ? (
                      <span className="tn-art-source">{ART.current}</span>
                    ) : (
                      <Button
                        size="sm"
                        prominence="secondary"
                        onClick={() => show(item)}
                      >
                        {ART.showVersion}
                      </Button>
                    )}
                  </li>
                );
              })}
            </ol>
            <Text font="secondary-body" color="text-03">
              {ART.versionsHint}
            </Text>
          </div>
        )}
      </div>
      <footer className="tn-art-panel-foot">
        <Diamond />
        <span className="flex-1 min-w-0">{ART.footer}</span>
        <Button
          size="sm"
          prominence="tertiary"
          onClick={() => composeTonMessage(ART.adjustPrompt(artifact.title))}
        >
          {ART.adjust}
        </Button>
      </footer>
      {presenting && isDeck && (
        <Presenter
          artifact={artifact}
          start={slide}
          onExit={(index) => {
            setSlide(index);
            setPresenting(false);
          }}
        />
      )}
    </aside>
  );
}
