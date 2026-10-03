"use client";

import Link from "next/link";
import type { Route } from "next";
import type { ReactNode } from "react";
import { Button, Text } from "@opal/components";
import {
  SvgAlertCircle,
  SvgChevronLeft,
  SvgChevronRight,
  SvgRefreshCw,
} from "@opal/icons";
import type { IconFunctionComponent } from "@opal/types";
import { cn } from "@opal/utils";

export type TonTone = "success" | "warning" | "danger" | "neutral" | "brand";

interface TonCardProps {
  children: ReactNode;
  className?: string;
  as?: "section" | "div" | "article";
  labelledBy?: string;
}

export function TonCard({
  children,
  className,
  as: Tag = "section",
  labelledBy,
}: TonCardProps) {
  return (
    <Tag aria-labelledby={labelledBy} className={cn("ton-card", className)}>
      {children}
    </Tag>
  );
}

interface CardHeaderProps {
  id?: string;
  title: string;
  description?: string;
  action?: { href: Route; label: string };
  icon?: IconFunctionComponent;
}

export function CardHeader({
  id,
  title,
  description,
  action,
  icon: Icon,
}: CardHeaderProps) {
  return (
    <div className="flex items-start justify-between gap-3">
      <div className="flex items-start gap-3 min-w-0">
        {Icon && (
          <span className="ton-icon-tile flex items-center justify-center w-8 h-8 shrink-0">
            <Icon size={16} />
          </span>
        )}
        <div className="flex flex-col gap-0.5 min-w-0">
          <Text as="h2" id={id} font="heading-h3" color="text-05">
            {title}
          </Text>
          {description && (
            <Text as="p" font="secondary-body" color="text-03">
              {description}
            </Text>
          )}
        </div>
      </div>
      {action && <ChevronLink href={action.href} label={action.label} />}
    </div>
  );
}

export function ChevronLink({ href, label }: { href: Route; label: string }) {
  return (
    <Link
      href={href}
      className="ton-focusable ton-brand-text flex items-center gap-1 shrink-0 rounded-08 px-1"
    >
      <Text font="secondary-action" color="inherit">
        {label}
      </Text>
      <SvgChevronRight size={14} />
    </Link>
  );
}

export function StatusPill({
  tone,
  children,
}: {
  tone: TonTone;
  children: string;
}) {
  return (
    <span className="ton-pill" data-tone={tone}>
      {children}
    </span>
  );
}

export function StatusDot({ tone }: { tone: TonTone }) {
  return <span aria-hidden className="ton-dot" data-tone={tone} />;
}

interface IconTileProps {
  icon: IconFunctionComponent;
  tone?: "brand" | "warning" | "neutral" | "gold";
  size?: "sm" | "md" | "lg";
}

export function IconTile({
  icon: Icon,
  tone = "brand",
  size = "md",
}: IconTileProps) {
  const box =
    size === "lg" ? "w-11 h-11" : size === "sm" ? "w-7 h-7" : "w-9 h-9";
  const glyph = size === "lg" ? 20 : size === "sm" ? 14 : 18;
  return (
    <span
      className={cn(
        "ton-icon-tile flex items-center justify-center shrink-0",
        box
      )}
      data-tone={tone === "brand" ? undefined : tone}
    >
      <Icon size={glyph} />
    </span>
  );
}

/** Specialist status as returned by /api/ton/agent/specialists or closing. */
export function specialistTone(status: string): TonTone {
  const value = status.toLowerCase();
  if (value.startsWith("operacional")) return "success";
  if (value.startsWith("parcial")) return "warning";
  return "neutral";
}

export function routineTone(status: string): TonTone {
  const value = status.toLowerCase();
  if (value.startsWith("agendada") || value.startsWith("ativa"))
    return "success";
  if (value.includes("manual")) return "brand";
  return "neutral";
}

/** Outcome of a routine run or report publication. */
export function runTone(status: string | null | undefined): TonTone {
  // The API returns either codes or already translated labels.
  const value = (status ?? "").toUpperCase();
  if (value.includes("BLOQUEIO") || value.includes("BLOCKED")) return "warning";
  if (value === "PARTIAL" || value.startsWith("PARCIAL")) return "warning";
  if (value.includes("FAIL") || value.startsWith("FALH") || value === "ERROR")
    return "danger";
  if (
    ["COMPLETED", "PASSED", "SUCCEEDED", "PUBLISHED"].includes(value) ||
    value.startsWith("CONCLU") ||
    value.startsWith("PUBLICAD")
  )
    return "success";
  return "neutral";
}

export function sourceTone(status: string): TonTone {
  if (status === "CURRENT") return "success";
  if (status === "PROCESSING") return "brand";
  if (status === "FAILED") return "danger";
  if (status === "UNCONFIGURED") return "neutral";
  return "warning";
}

export function PageContainer({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "w-full max-w-[1200px] mx-auto self-start px-4 sm:px-6 lg:px-8 py-6 lg:py-8 flex flex-col gap-6",
        className
      )}
    >
      {children}
    </div>
  );
}

interface PageHeaderProps {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: PageHeaderProps) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div className="flex flex-col gap-1.5 min-w-0">
        {eyebrow && <span className="ton-eyebrow">{eyebrow}</span>}
        <h1 className="ton-title">
          <Text font="heading-h1" color="inherit">
            {title}
          </Text>
        </h1>
        {description && (
          <Text as="p" font="main-ui-body" color="text-03">
            {description}
          </Text>
        )}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </header>
  );
}

export function LoadingBlock({
  label,
  lines = 3,
}: {
  label: string;
  lines?: number;
}) {
  return (
    <div role="status" aria-label={label} className="flex flex-col gap-2 py-1">
      {Array.from({ length: lines }, (_, index) => (
        <span
          key={index}
          className="h-4 rounded-08 bg-background-neutral-02 animate-pulse"
          style={{ width: `${90 - index * 15}%` }}
        />
      ))}
    </div>
  );
}

interface EmptyStateProps {
  icon: IconFunctionComponent;
  title: string;
  description?: string;
  action?: ReactNode;
  tone?: "brand" | "neutral" | "gold" | "warning";
}

/** A deliberate, centered empty or healthy state; never a blank card. */
export function EmptyState({
  icon,
  title,
  description,
  action,
  tone = "neutral",
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center text-center gap-3 px-4 py-8">
      <IconTile icon={icon} tone={tone} size="lg" />
      <div className="flex flex-col gap-1 max-w-md">
        <Text as="p" font="main-ui-action" color="text-05">
          {title}
        </Text>
        {description && (
          <Text as="p" font="secondary-body" color="text-03">
            {description}
          </Text>
        )}
      </div>
      {action}
    </div>
  );
}

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
  compact?: boolean;
}

/** Explicit failure with a way forward. */
export function ErrorState({ message, onRetry, compact }: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(
        "flex items-start gap-3 rounded-12 border border-01 bg-background-neutral-01",
        compact ? "p-3" : "p-4"
      )}
    >
      <SvgAlertCircle size={18} className="text-status-error-05 shrink-0" />
      <div className="flex flex-col gap-2 min-w-0 flex-1">
        <Text as="p" font="main-ui-body" color="text-04">
          {message ??
            "Não foi possível carregar esta informação. Tente novamente em instantes."}
        </Text>
        {onRetry && (
          <span>
            <Button
              size="sm"
              prominence="secondary"
              icon={SvgRefreshCw}
              onClick={onRetry}
            >
              Tentar novamente
            </Button>
          </span>
        )}
      </div>
    </div>
  );
}

export function BackLink({ href, label }: { href: Route; label: string }) {
  return (
    <Link
      href={href}
      className="ton-focusable flex items-center gap-1 w-fit rounded-08 text-text-03 hover:text-text-05"
    >
      <SvgChevronLeft size={14} />
      <Text font="secondary-action" color="inherit">
        {label}
      </Text>
    </Link>
  );
}

interface MetricProps {
  label: string;
  value: string;
  detail?: string;
  tone?: TonTone;
}

/** Amounts and counts never wrap; text values may. */
const NUMERIC = /^[-−+]?\s?(R\$|\d)/;

/** A labelled figure inside a card; tabular numerals, no decoration. */
export function Metric({ label, value, detail, tone }: MetricProps) {
  return (
    <div className="flex flex-col gap-1 min-w-0">
      <span className="ton-eyebrow">{label}</span>
      <span
        className={cn("ton-metric", NUMERIC.test(value) && "ton-metric-num")}
      >
        <Text font="heading-h3" color="inherit">
          {value}
        </Text>
      </span>
      {detail && (
        <span className="flex items-center gap-1.5 min-w-0">
          {tone && <StatusDot tone={tone} />}
          <Text font="secondary-body" color="text-03" maxLines={2}>
            {detail}
          </Text>
        </span>
      )}
    </div>
  );
}
