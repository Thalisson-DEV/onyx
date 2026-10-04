"use client";

import { Text, Tooltip } from "@opal/components";
import { COPY } from "@/lib/ton/copy";
import { getBusinessLabel, getStatusTone } from "@/lib/ton/labels";
import { specialistIdentity } from "@/lib/ton/specialists";
import {
  isSpecialistActive,
  type SpecialistStep,
  type SpecialistWork,
} from "@/lib/ton/work-log";
import SpecialistMark from "@/views/ton/chat/SpecialistMark";

const S = COPY.work.specialists;

type StepState = "done" | "skipped" | "blocked" | "pending";

function stepState(status: string): StepState {
  if (/conclu|passed|aprovad/i.test(status)) return "done";
  if (/não execut|nao execut|skipped/i.test(status)) return "skipped";
  if (/bloque|falh|failed/i.test(status)) return "blocked";
  return "pending";
}

function pillTone(status: string): string {
  const tone = getStatusTone(status);
  if (tone === "success") return "success";
  if (tone === "warning") return "warning";
  if (tone === "error") return "danger";
  return "neutral";
}

function ProtocolStrip({ steps }: { steps: SpecialistStep[] }) {
  if (!steps.length) return null;
  const done = steps.filter((step) => stepState(step.status) === "done").length;
  return (
    <div className="flex flex-col gap-1.5">
      <ol className="ton-protocol" aria-label={S.protocol(done, steps.length)}>
        {steps.map((step, index) => {
          const state = stepState(step.status);
          const label = `${step.code}: ${getBusinessLabel(step.status)}${
            step.reason ? ` — ${step.reason}` : ""
          }`;
          return (
            <Tooltip key={`${step.code}-${index}`} side="top" tooltip={label}>
              <li
                className="ton-protocol-step"
                data-state={state}
                aria-label={label}
              >
                <span
                  className="ton-protocol-bar"
                  style={{ animationDelay: `${index * 45}ms` }}
                />
                <span className="ton-protocol-label">
                  <Text font="figure-small-label" color="text-03">
                    {step.code}
                  </Text>
                </span>
              </li>
            </Tooltip>
          );
        })}
      </ol>
      <Text font="secondary-body" color="text-03">
        {S.protocol(done, steps.length)}
      </Text>
    </div>
  );
}

function SpecialistRow({ specialist }: { specialist: SpecialistWork }) {
  const identity = specialistIdentity(specialist.key, specialist.name);
  // One line per distinct reason a step did not run.
  const skipped = [
    ...new Map(
      specialist.steps
        .filter((step) => stepState(step.status) !== "done" && step.reason)
        .map((step) => [step.reason, step])
    ).values(),
  ];
  return (
    <li className="ton-specialist">
      <SpecialistMark
        specialistKey={specialist.key}
        fallbackName={specialist.name}
        size={32}
      />
      <div className="flex min-w-0 flex-col gap-2">
        <div className="flex flex-col">
          <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <Text font="main-ui-action" color="text-05">
              {identity.name}
            </Text>
            {specialist.status && (
              <span
                className="ton-pill"
                data-tone={pillTone(specialist.status)}
              >
                {getBusinessLabel(specialist.status)}
              </span>
            )}
          </span>
          {identity.role && (
            <Text font="secondary-body" color="text-03">
              {identity.role}
            </Text>
          )}
        </div>
        {specialist.reason && (
          <Text font="secondary-body" color="text-04">
            {specialist.reason}
          </Text>
        )}
        <ProtocolStrip steps={specialist.steps} />
        {skipped.length > 0 && (
          <ul className="flex flex-col gap-0.5">
            {skipped.map((step) => (
              <li key={step.code}>
                <Text font="secondary-body" color="text-03">
                  {`${step.code} · ${S.skippedTitle.toLowerCase()}: ${step.reason}`}
                </Text>
              </li>
            ))}
          </ul>
        )}
        {specialist.actions.length > 0 && (
          <div className="flex flex-col gap-0.5">
            <Text font="secondary-action" color="text-04">
              {S.actions}
            </Text>
            <ul className="flex list-disc flex-col gap-0.5 ps-5">
              {specialist.actions.map((action) => (
                <li key={action}>
                  <Text font="secondary-body" color="text-04">
                    {action}
                  </Text>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </li>
  );
}

export interface SpecialistsBoardProps {
  specialists: SpecialistWork[];
}

/** Who worked on a closing analysis and what each one did. */
export default function SpecialistsBoard({
  specialists,
}: SpecialistsBoardProps) {
  const active = specialists.filter(isSpecialistActive);
  const waiting = specialists.filter((item) => !isSpecialistActive(item));
  if (!active.length && !waiting.length) return null;
  return (
    <section className="ton-specialists" aria-label={S.title}>
      <div className="flex flex-col">
        <Text font="main-ui-action" color="text-05">
          {S.title}
        </Text>
        <Text font="secondary-body" color="text-03">
          {S.subtitle}
        </Text>
      </div>
      {active.length > 0 && (
        <ul className="flex flex-col gap-3">
          {active.map((specialist) => (
            <SpecialistRow key={specialist.key} specialist={specialist} />
          ))}
        </ul>
      )}
      {waiting.length > 0 && (
        <div className="flex flex-wrap items-center gap-3 border-t border-border-01 pt-3">
          <span className="flex items-center gap-1">
            {waiting.map((specialist) => {
              const identity = specialistIdentity(
                specialist.key,
                specialist.name
              );
              return (
                <Tooltip
                  key={specialist.key}
                  side="top"
                  tooltip={
                    specialist.reason
                      ? `${identity.name} · ${specialist.reason}`
                      : identity.name
                  }
                >
                  <span>
                    <SpecialistMark
                      specialistKey={specialist.key}
                      fallbackName={specialist.name}
                      size={24}
                      muted
                    />
                  </span>
                </Tooltip>
              );
            })}
          </span>
          <Text font="secondary-body" color="text-03">
            {S.waiting(waiting.length)}
          </Text>
        </div>
      )}
    </section>
  );
}
