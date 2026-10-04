"use client";

import { useState, type ReactNode } from "react";
import { Button } from "@opal/components";
import {
  SvgChevronDown,
  SvgChevronUp,
  SvgClipboard,
  SvgServer,
  SvgUsers,
} from "@opal/icons";
import type { IconFunctionComponent } from "@opal/types";
import { COPY } from "@/lib/ton/copy";
import {
  isSpecialistActive,
  type DataOrigin,
  type SpecialistWork,
  type WorkSource,
} from "@/lib/ton/work-log";
import TonSources from "@/views/ton/chat/TonSources";
import SpecialistsBoard from "@/views/ton/chat/SpecialistsBoard";

const D = COPY.work.details;

type Panel = "sources" | "specialists" | "results";

interface ToggleProps {
  panel: Panel;
  open: Panel | null;
  icon: IconFunctionComponent;
  label: string;
  count: number;
  onToggle: (panel: Panel) => void;
}

function Toggle({ panel, open, icon, label, count, onToggle }: ToggleProps) {
  const expanded = open === panel;
  return (
    <Button
      prominence="tertiary"
      size="sm"
      icon={icon}
      rightIcon={expanded ? SvgChevronUp : SvgChevronDown}
      interaction={expanded ? "hover" : "rest"}
      aria-expanded={expanded}
      aria-controls={`ton-details-${panel}`}
      onClick={() => onToggle(panel)}
    >
      {`${label} · ${count}`}
    </Button>
  );
}

export interface AnswerDetailsProps {
  sources: WorkSource[];
  origins: DataOrigin[];
  specialists: SpecialistWork[];
  /** Result cards that do not ask for an action. */
  results: ReactNode[];
}

/**
 * Supporting detail for an answer, folded by default: sources, specialists
 * and result cards each open on request, one at a time.
 */
export default function AnswerDetails({
  sources,
  origins,
  specialists,
  results,
}: AnswerDetailsProps) {
  const [open, setOpen] = useState<Panel | null>(null);
  const active = specialists.filter(isSpecialistActive).length;
  const toggle = (panel: Panel) =>
    setOpen((current) => (current === panel ? null : panel));
  if (
    !sources.length &&
    !origins.length &&
    !specialists.length &&
    !results.length
  )
    return null;
  return (
    <div className="ton-details">
      <div
        role="group"
        aria-label={D.label}
        className="ton-details-bar flex flex-wrap items-center gap-1"
      >
        {(sources.length > 0 || origins.length > 0) && (
          <Toggle
            panel="sources"
            open={open}
            icon={SvgServer}
            label={D.sources}
            count={sources.length + origins.length}
            onToggle={toggle}
          />
        )}
        {specialists.length > 0 && (
          <Toggle
            panel="specialists"
            open={open}
            icon={SvgUsers}
            label={D.specialists}
            count={active}
            onToggle={toggle}
          />
        )}
        {results.length > 0 && (
          <Toggle
            panel="results"
            open={open}
            icon={SvgClipboard}
            label={D.results}
            count={results.length}
            onToggle={toggle}
          />
        )}
      </div>
      {open && (
        <div
          id={`ton-details-${open}`}
          key={open}
          className="ton-details-panel"
        >
          {open === "sources" && (
            <TonSources sources={sources} origins={origins} />
          )}
          {open === "specialists" && (
            <SpecialistsBoard specialists={specialists} />
          )}
          {open === "results" && (
            <div className="flex flex-col gap-2">{results}</div>
          )}
        </div>
      )}
    </div>
  );
}
