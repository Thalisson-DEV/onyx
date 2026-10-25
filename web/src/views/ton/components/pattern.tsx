"use client";

import type { ReactNode } from "react";
import { Text } from "@opal/components";
import type { TonTone } from "@/views/ton/components/ui";
import { PageHead } from "@/views/ton/components/kit";

/**
 * Building blocks of the TON page pattern approved on 2026-10-24: head,
 * quick-view chips, a filter row, one table and a sticky batch bar. Styles
 * live in ton.css under the `tp-` prefix.
 */

interface PatternHeadProps {
  eyebrow: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}

export function PatternHead({
  eyebrow,
  title,
  description,
  actions,
}: PatternHeadProps) {
  return (
    <PageHead
      eyebrow={eyebrow}
      title={title}
      description={description}
      actions={actions}
    />
  );
}

interface QuickViewProps {
  label: string;
  /** "3 · R$ 9.402,34" — what the view holds. */
  count: string;
  tone?: TonTone;
  active: boolean;
  onSelect: () => void;
}

/** A filter that answers one question the user asks every day. */
export function QuickView({
  label,
  count,
  tone,
  active,
  onSelect,
}: QuickViewProps) {
  return (
    <button
      type="button"
      className="tp-chip ton-focusable"
      aria-pressed={active}
      onClick={onSelect}
    >
      {tone && <span className="tp-chip-dot" data-tone={tone} aria-hidden />}
      {label}
      <span className="tp-chip-count">{count}</span>
    </button>
  );
}

interface BatchBarProps {
  summary: string;
  children: ReactNode;
}

/** Appears while rows are selected; every button does real work on them. */
export function BatchBar({ summary, children }: BatchBarProps) {
  return (
    <div className="tp-batch" role="region" aria-label="Ações nos selecionados">
      <span className="tp-batch-sum">{summary}</span>
      {children}
    </div>
  );
}

interface BatchButtonProps {
  label: string;
  primary?: boolean;
  disabled?: boolean;
  onClick: () => void;
}

export function BatchButton({
  label,
  primary,
  disabled,
  onClick,
}: BatchButtonProps) {
  return (
    <button
      type="button"
      className="tp-batch-button ton-focusable"
      data-primary={primary ? "true" : undefined}
      disabled={disabled}
      onClick={onClick}
    >
      {label}
    </button>
  );
}

interface FieldProps {
  label: string;
  /** Grid columns out of 12. */
  span?: 3 | 4 | 6 | 8 | 12;
  note?: string | null;
  noteTone?: "filled" | "error";
  /** Filled by the TON from a document: tinted until the person changes it. */
  filled?: boolean;
  htmlFor?: string;
  children: ReactNode;
}

export function PatternField({
  label,
  span = 12,
  note,
  noteTone,
  filled,
  htmlFor,
  children,
}: FieldProps) {
  return (
    <div
      className="tp-field"
      data-span={span === 12 ? undefined : String(span)}
      data-filled={filled ? "true" : undefined}
    >
      <label className="tp-field-label" htmlFor={htmlFor}>
        {label}
      </label>
      {children}
      {note && (
        <span className="tp-field-note" data-tone={noteTone}>
          {note}
        </span>
      )}
    </div>
  );
}

export function FormSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="tp-form-section">
      <h2>
        <Text font="main-ui-action" color="text-05">
          {title}
        </Text>
      </h2>
      {children}
    </section>
  );
}
