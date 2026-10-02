"use client";

import type { Route } from "next";
import { Button, Text } from "@opal/components";
import { SvgArrowRight } from "@opal/icons";
import { COPY, formatShortMonth } from "@/lib/ton/copy";
import { StatusPill } from "@/views/ton/components/ui";
import type { BlockerPage } from "@/views/ton/PendingPage/model";

const MISSING = COPY.decisionLoop.missing;

function monthYear(period: string): string {
  return `${formatShortMonth(period).replace(".", "")}/${period.slice(0, 4)}`;
}

/** Missing months are a data gap, not a decision: say which and how to import. */
export default function MissingActualsGuide({
  page,
  closingPeriod,
}: {
  page: BlockerPage;
  closingPeriod: string;
}) {
  const missing = page.rows.flatMap((row) => row.periods);
  const covered = page.covered_periods ?? [];
  const year = closingPeriod.slice(0, 4);
  const range = MISSING.range(
    monthYear(`${year}-01-01`),
    monthYear(closingPeriod)
  );
  // SAFETY: /ton/fontes is a static route; only its query varies.
  const href =
    `/ton/fontes?importar=financial_launches&ate=${closingPeriod.slice(0, 7)}` as Route;
  const closingLabel = monthYear(closingPeriod);
  return (
    <div className="flex flex-col gap-4">
      <Text font="main-ui-body" color="text-04">
        {MISSING.why(closingLabel)}
      </Text>
      <dl className="grid grid-cols-1 sm:grid-cols-[140px_1fr] gap-x-4 gap-y-2">
        <dt className="ton-eyebrow pt-1">{MISSING.have}</dt>
        <dd className="flex flex-wrap gap-1.5">
          {covered.map((period) => (
            <StatusPill key={period} tone="success">
              {monthYear(period)}
            </StatusPill>
          ))}
        </dd>
        <dt className="ton-eyebrow pt-1">{MISSING.missing}</dt>
        <dd className="flex flex-wrap gap-1.5">
          {missing.map((period) => (
            <StatusPill key={period} tone="warning">
              {monthYear(period)}
            </StatusPill>
          ))}
        </dd>
      </dl>
      <Text font="main-ui-action" color="text-05">
        {MISSING.notDecision}
      </Text>
      <ol className="flex flex-col gap-2">
        {MISSING.steps.map((step, index) => (
          <li key={index} className="flex items-start gap-3">
            <span className="ton-step" data-state="next">
              {index + 1}
            </span>
            <Text font="main-ui-body" color="text-04">
              {step(range)}
            </Text>
          </li>
        ))}
      </ol>
      <div>
        <Button href={href} rightIcon={SvgArrowRight}>
          {MISSING.cta}
        </Button>
      </div>
    </div>
  );
}
