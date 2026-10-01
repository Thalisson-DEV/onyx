"use client";

import { Button, Text } from "@opal/components";
import {
  SvgArrowRight,
  SvgCheckCircle,
  SvgPlayCircle,
  SvgSimpleLoader,
  SvgWorkflow,
} from "@opal/icons";
import { useUser } from "@/providers/UserProvider";
import { useR3Execution } from "@/lib/ton/hooks";
import { useTonAccess, useTonClosing, useTonRoutines } from "@/lib/ton/api";
import { COPY, formatRelativeDateTime } from "@/lib/ton/copy";
import { getBusinessLabel } from "@/lib/ton/labels";
import {
  IconTile,
  LoadingBlock,
  StatusPill,
  TonCard,
  routineTone,
} from "@/views/ton/components/ui";

interface FactProps {
  label: string;
  value: string;
}

function Fact({ label, value }: FactProps) {
  return (
    <div className="flex flex-col gap-0.5 min-w-0">
      <span className="ton-eyebrow">{label}</span>
      <Text font="main-ui-action" color="text-05">
        {value}
      </Text>
    </div>
  );
}

interface R3SpotlightProps {
  /** Show the link to the automations page (hidden on that page itself). */
  showManageLink?: boolean;
}

export default function R3Spotlight({
  showManageLink = true,
}: R3SpotlightProps) {
  const { user } = useUser();
  const access = useTonAccess();
  const routines = useTonRoutines();
  const closing = useTonClosing();
  const execution = useR3Execution(
    closing.data,
    access.canRunReports,
    user?.id,
    access.canReadReports
  );
  const routine = routines.data?.find((item) => item.key === "R3");
  const latest = execution.latest;
  const lastRun = latest?.output.generated_at ?? routine?.last_run ?? null;

  return (
    <TonCard className="flex flex-col gap-4 p-5" labelledBy="ton-r3-title">
      <div className="flex items-start gap-3">
        <IconTile icon={SvgWorkflow} tone="gold" size="lg" />
        <div className="flex flex-col gap-1 min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="ton-eyebrow">{COPY.home.automation.title}</span>
            {routine && (
              <StatusPill tone={routineTone(routine.status)}>
                {routine.status}
              </StatusPill>
            )}
          </div>
          <Text as="h2" id="ton-r3-title" font="heading-h3" color="text-05">
            {routine?.name ?? "Fechamento preliminar mensal"}
          </Text>
          {routine && (
            <Text as="p" font="secondary-body" color="text-03">
              {routine.schedule}
            </Text>
          )}
        </div>
      </div>

      {routines.isLoading && <LoadingBlock label={COPY.common.loading} />}

      {routine && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 rounded-12 bg-background-neutral-01 p-3">
          <Fact
            label={COPY.home.automation.nextRun}
            value={
              routine.next_run
                ? formatRelativeDateTime(routine.next_run)
                : COPY.common.notAvailable
            }
          />
          <Fact
            label={COPY.home.automation.lastRun}
            value={
              lastRun
                ? formatRelativeDateTime(lastRun)
                : COPY.home.automation.notRunYet
            }
          />
          <Fact
            label={COPY.home.automation.lastResult}
            value={
              latest
                ? getBusinessLabel(latest.status)
                : (routine.last_result ?? COPY.home.automation.notRunYet)
            }
          />
        </div>
      )}

      <div aria-live="polite" className="flex flex-col gap-2">
        {execution.running && (
          <div className="flex items-center gap-2">
            <SvgSimpleLoader size={16} />
            <Text font="main-ui-body" color="text-04">
              {COPY.home.automation.running}
            </Text>
          </div>
        )}
        {execution.failed && (
          <Text as="p" font="main-ui-body" color="status-error-05">
            {COPY.home.automation.runFailed}
          </Text>
        )}
        {!execution.running &&
          !execution.failed &&
          execution.startedAt &&
          latest && (
            <div className="flex items-center gap-2">
              <SvgCheckCircle size={16} className="ton-brand-text" />
              <Text font="main-ui-action" color="text-05">
                {COPY.home.automation.completed}
              </Text>
            </div>
          )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {access.canRunReports && routine?.manual_available && (
          <Button
            onClick={execution.run}
            disabled={execution.running || !closing.data}
            icon={execution.running ? SvgSimpleLoader : SvgPlayCircle}
          >
            {execution.running
              ? COPY.home.automation.running
              : execution.failed
                ? COPY.common.retry
                : COPY.home.automation.runNow}
          </Button>
        )}
        {latest && (
          <Button
            href={latest.report_url}
            prominence="secondary"
            rightIcon={SvgArrowRight}
          >
            {COPY.home.automation.openResult}
          </Button>
        )}
        {showManageLink && (
          <Button href="/ton/automacoes" prominence="tertiary">
            {COPY.home.automation.manageAutomations}
          </Button>
        )}
      </div>
    </TonCard>
  );
}
