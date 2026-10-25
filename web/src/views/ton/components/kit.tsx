"use client";

/*
 * Shared pieces of every TON screen (visual system approved 2026-10-24):
 * one tag shape, the TON mark, view tabs, the collapsible filter bar, the
 * switch and the side drawer that replaces every dialog. Styles live in
 * shell/ton-theme.css under the `tn-` prefix. These are brand controls
 * with no Opal equivalent (tabs with counts and totals, removable filter
 * tokens, a resizable drawer), so they use native buttons styled by tokens.
 */

import {
  createContext,
  useContext,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type ReactNode,
  type KeyboardEvent as ReactKeyboardEvent,
  type PointerEvent as ReactPointerEvent,
} from "react";
import { createPortal } from "react-dom";
import { Text } from "@opal/components";
import {
  SvgChevronDown,
  SvgFilter,
  SvgMaximize2,
  SvgSearch,
  SvgX,
} from "@opal/icons";
import type { IconFunctionComponent } from "@opal/types";
import { cn } from "@opal/utils";
import { COPY } from "@/lib/ton/copy";

export type TagTone = "ok" | "info" | "warn" | "danger" | "neutral" | "brand";

interface TagProps {
  tone?: TagTone;
  children: ReactNode;
}

/** The only shape a state takes in the TON: situation, deadline, kind. */
export function Tag({ tone = "neutral", children }: TagProps) {
  return (
    <span className="tn-tag" data-tone={tone}>
      {children}
    </span>
  );
}

interface TonMarkProps {
  children: ReactNode;
}

/** What the TON pointed out or proposed: gold diamond and text. */
export function TonMark({ children }: TonMarkProps) {
  return (
    <span className="tn-mark">
      <span aria-hidden className="tn-diamond" />
      {children}
    </span>
  );
}

export function Diamond() {
  return <span aria-hidden className="tn-diamond" />;
}

interface PageFrameProps {
  children: ReactNode;
  /** Long reading (assistant, report) keeps a narrower column. */
  width?: "full" | "reading";
  className?: string;
}

/** The workspace frame: full width, one 24px gutter, up to 1680px. */
export function PageFrame({
  children,
  width = "full",
  className,
}: PageFrameProps) {
  return (
    <div className={cn("tn-page", className)} data-width={width}>
      {children}
    </div>
  );
}

interface PageHeadProps {
  /** Where the page sits (area of the product), above the title. */
  eyebrow?: string;
  title: string;
  description?: string;
  /** Tags beside the title (official result, not ready...). */
  status?: ReactNode;
  actions?: ReactNode;
}

export function PageHead({
  eyebrow,
  title,
  description,
  status,
  actions,
}: PageHeadProps) {
  return (
    <header className="tn-head">
      <div className="tn-head-text">
        {eyebrow && <span className="tn-head-eyebrow">{eyebrow}</span>}
        <div className="tn-head-title">
          <h1 className="ton-title">
            <Text font="heading-h2" color="inherit">
              {title}
            </Text>
          </h1>
          {status}
        </div>
        {description && (
          <Text as="p" font="secondary-body" color="text-03">
            {description}
          </Text>
        )}
      </div>
      {actions && <div className="tn-head-actions">{actions}</div>}
    </header>
  );
}

export type DotTone = "danger" | "warn" | "ok" | "info" | "gold" | "neutral";

export interface ViewTab<K extends string> {
  key: K;
  label: string;
  count?: number;
  total?: string;
  tone?: DotTone;
}

interface ViewTabsProps<K extends string> {
  label: string;
  views: ViewTab<K>[];
  value: K;
  onChange: (key: K) => void;
}

/** Saved questions of a screen, each with its count and total. */
export function ViewTabs<K extends string>({
  label,
  views,
  value,
  onChange,
}: ViewTabsProps<K>) {
  return (
    <div className="tn-views" role="group" aria-label={label}>
      {views.map((view) => (
        <button
          key={view.key}
          type="button"
          className="tn-view ton-focusable"
          aria-pressed={view.key === value}
          onClick={() => onChange(view.key)}
        >
          {view.tone && (
            <span aria-hidden className="tn-dot" data-tone={view.tone} />
          )}
          {view.label}
          {view.count !== undefined && (
            <span className="tn-view-count">{view.count}</span>
          )}
          {view.total && <span className="tn-view-total">{view.total}</span>}
        </button>
      ))}
    </div>
  );
}

export interface FilterToken {
  key: string;
  label: string;
  value: string;
  onRemove: () => void;
}

interface FilterBarProps {
  search?: {
    value: string;
    onChange: (value: string) => void;
    placeholder: string;
  };
  /** Active filters shown as removable tokens beside the toggle. */
  tokens?: FilterToken[];
  onClear?: () => void;
  /** Fields of the collapsible panel; omit for a bar without panel. */
  panel?: ReactNode;
  panelFooter?: ReactNode;
  /** Controls after the spacer (group by, compare...). */
  end?: ReactNode;
  /** Controls right after the search (unit, period). */
  start?: ReactNode;
  toggleLabel?: string;
  defaultOpen?: boolean;
}

/** One bar per table: search, "Filtros" that opens the panel, tokens. */
export function FilterBar({
  search,
  tokens = [],
  onClear,
  panel,
  panelFooter,
  end,
  start,
  toggleLabel = COPY.kit.filters,
  defaultOpen = false,
}: FilterBarProps) {
  const [open, setOpen] = useState(defaultOpen);
  const panelId = useId();
  return (
    <>
      <div className="tn-toolbar">
        {search && (
          <label className="tn-search">
            <SvgSearch size={14} />
            <input
              type="search"
              aria-label={search.placeholder}
              placeholder={search.placeholder}
              value={search.value}
              onChange={(event) => search.onChange(event.target.value)}
            />
          </label>
        )}
        {start}
        {panel && (
          <button
            type="button"
            className="tn-btn tn-filter-toggle ton-focusable"
            aria-expanded={open}
            aria-controls={panelId}
            onClick={() => setOpen((value) => !value)}
          >
            <SvgFilter size={14} />
            {toggleLabel}
            {tokens.length > 0 && (
              <span className="tn-filter-count">{tokens.length}</span>
            )}
            <SvgChevronDown size={12} className="tn-chev" />
          </button>
        )}
        {tokens.map((token) => (
          <span key={token.key} className="tn-token">
            {token.label}: <b>{token.value}</b>
            <button
              type="button"
              className="ton-focusable"
              aria-label={COPY.kit.removeFilter(token.label)}
              onClick={token.onRemove}
            >
              <SvgX size={10} />
            </button>
          </span>
        ))}
        {tokens.length > 0 && onClear && (
          <button
            type="button"
            className="tn-link ton-focusable"
            onClick={onClear}
          >
            {COPY.kit.clearFilters}
          </button>
        )}
        <span className="tn-spacer" />
        {end}
      </div>
      {panel && open && (
        <div id={panelId} className="tn-filter-panel">
          {panel}
          <div className="tn-filter-foot">
            <span className="tn-hint">{COPY.kit.filtersHint}</span>
            <span className="tn-spacer" />
            {panelFooter}
            <button
              type="button"
              className="tn-btn ton-focusable"
              onClick={() => setOpen(false)}
            >
              {COPY.kit.collapse}
            </button>
          </div>
        </div>
      )}
    </>
  );
}

interface FilterFieldProps {
  label: string;
  /** Columns of the 6-column panel grid. */
  span?: 1 | 2 | 3 | 6;
  children: ReactNode;
}

export function FilterField({ label, span = 1, children }: FilterFieldProps) {
  return (
    <div className="tn-field" data-span={span === 1 ? undefined : span}>
      <span className="tn-field-label">{label}</span>
      {children}
    </div>
  );
}

interface SwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  children: ReactNode;
  /** Gold when the switch filters by what the TON pointed out. */
  tone?: "brand" | "gold";
}

export function Switch({ checked, onChange, children, tone }: SwitchProps) {
  return (
    <button
      type="button"
      className="tn-switch ton-focusable"
      aria-pressed={checked}
      data-tone={tone}
      onClick={() => onChange(!checked)}
    >
      <span aria-hidden className="tn-switch-track" />
      {children}
    </button>
  );
}

interface SegmentedProps<K extends string> {
  label: string;
  /** Visible lead-in, e.g. "Agrupar". */
  lead?: string;
  options: { key: K; label: string }[];
  value: K;
  onChange: (key: K) => void;
}

export function Segmented<K extends string>({
  label,
  lead,
  options,
  value,
  onChange,
}: SegmentedProps<K>) {
  return (
    <div className="ton-segmented" role="group" aria-label={label}>
      {lead && (
        <span className="px-2">
          <Text font="secondary-body" color="text-03">
            {lead}
          </Text>
        </span>
      )}
      {options.map((option) => (
        <button
          key={option.key}
          type="button"
          className="ton-segment ton-focusable"
          aria-pressed={option.key === value}
          onClick={() => onChange(option.key)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

const MIN_WIDTH = 380;
/** Matches the slide-out in ton-theme.css. */
const EXIT_MS = 160;
const WIDE_WIDTH = 820;

function readWidth(key: string | undefined, fallback: number): number {
  if (!key) return fallback;
  try {
    const value = Number(window.localStorage.getItem(`ton.drawer.${key}`));
    return Number.isFinite(value) && value >= MIN_WIDTH ? value : fallback;
  } catch {
    return fallback;
  }
}

function writeWidth(key: string | undefined, width: number) {
  if (!key) return;
  try {
    window.localStorage.setItem(`ton.drawer.${key}`, String(Math.round(width)));
  } catch {
    // Storage can be blocked; the width still holds for this visit.
  }
}

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  eyebrow?: ReactNode;
  /** One line under the title: what this panel is for. */
  description?: ReactNode;
  /** Tinted band under the header: the figures or the context at a glance. */
  summary?: ReactNode;
  /** Shown before the title (the TON avatar in the ask panel). */
  leading?: ReactNode;
  /** Extra header buttons before widen/close. */
  actions?: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
  /** Forms and decisions dim the page; details and the TON do not. */
  modal?: boolean;
  defaultWidth?: number;
  /** Remembers the width the user dragged to, per kind of drawer. */
  storageKey?: string;
  /** Rendered between header and body without scrolling (tabs). */
  subheader?: ReactNode;
  bodyClassName?: string;
}

/**
 * The side drawer: every registration, detail and decision opens here,
 * never in a centered dialog. Drag the left edge or use the widen button.
 */
export function Drawer({
  open,
  onClose,
  title,
  eyebrow,
  description,
  summary,
  leading,
  actions,
  footer,
  children,
  modal = false,
  defaultWidth = 480,
  storageKey,
  subheader,
  bodyClassName,
}: DrawerProps) {
  const [width, setWidth] = useState(defaultWidth);
  const [mounted, setMounted] = useState(false);
  const [closing, setClosing] = useState(false);
  const titleId = useId();
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    setMounted(true);
    setWidth(readWidth(storageKey, defaultWidth));
  }, [storageKey, defaultWidth]);

  // Callers pass a fresh onClose each render; the listener reads the latest.
  const closeHandler = useRef(onClose);
  useEffect(() => {
    closeHandler.current = onClose;
  });

  // The sheet slides out before it unmounts; the caller closes after it.
  const closeTimer = useRef<number | null>(null);
  function requestClose() {
    if (closeTimer.current !== null) return;
    setClosing(true);
    closeTimer.current = window.setTimeout(() => {
      closeTimer.current = null;
      setClosing(false);
      closeHandler.current();
    }, EXIT_MS);
  }
  useEffect(
    () => () => {
      if (closeTimer.current !== null) window.clearTimeout(closeTimer.current);
    },
    []
  );
  const requestCloseRef = useRef(requestClose);
  useEffect(() => {
    requestCloseRef.current = requestClose;
  });

  useEffect(() => {
    if (!open || !mounted) return;
    // Focus moves in once, when the drawer opens, never while typing.
    closeRef.current?.focus();
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") requestCloseRef.current();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, mounted]);

  function resize(next: number) {
    const max = Math.max(MIN_WIDTH, window.innerWidth - 48);
    const clamped = Math.min(max, Math.max(MIN_WIDTH, next));
    setWidth(clamped);
    writeWidth(storageKey, clamped);
  }

  function startDrag(event: ReactPointerEvent<HTMLButtonElement>) {
    event.preventDefault();
    const startX = event.clientX;
    const startWidth = width;
    function move(moveEvent: PointerEvent) {
      resize(startWidth + (startX - moveEvent.clientX));
    }
    function up() {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
    }
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  }

  function onHandleKey(event: ReactKeyboardEvent<HTMLButtonElement>) {
    if (event.key === "ArrowLeft") resize(width + 40);
    if (event.key === "ArrowRight") resize(width - 40);
  }

  if (!open || !mounted) return null;
  const wide = width >= WIDE_WIDTH - 20;
  const state = closing ? "closing" : "open";
  return createPortal(
    <>
      {modal && (
        <div
          aria-hidden
          className="tn-scrim"
          data-state={state}
          onClick={requestClose}
        />
      )}
      <aside
        role={modal ? "dialog" : "complementary"}
        aria-modal={modal || undefined}
        aria-labelledby={titleId}
        className="tn-drawer"
        data-state={state}
        data-wide={wide || undefined}
        style={{ width }}
      >
        <button
          type="button"
          className="tn-drawer-handle"
          aria-label={COPY.kit.resize}
          onPointerDown={startDrag}
          onKeyDown={onHandleKey}
        />
        <header className="tn-drawer-head">
          {leading}
          <div className="tn-drawer-heading">
            {eyebrow && <span className="tn-drawer-eyebrow">{eyebrow}</span>}
            <h2 id={titleId} className="tn-drawer-title">
              {title}
            </h2>
            {description && (
              <p className="tn-drawer-description">{description}</p>
            )}
          </div>
          <div className="tn-drawer-tools">
            {actions}
            <button
              type="button"
              className="tn-icon-btn ton-focusable"
              aria-label={wide ? COPY.kit.narrow : COPY.kit.widen}
              onClick={() => resize(wide ? defaultWidth : WIDE_WIDTH)}
            >
              <SvgMaximize2 size={14} />
            </button>
            <button
              ref={closeRef}
              type="button"
              className="tn-icon-btn ton-focusable"
              aria-label={COPY.kit.close}
              onClick={requestClose}
            >
              <SvgX size={16} />
            </button>
          </div>
        </header>
        {summary && <div className="tn-drawer-summary">{summary}</div>}
        {subheader}
        <div className={cn("tn-drawer-body", bodyClassName)}>{children}</div>
        {footer && <footer className="tn-drawer-foot">{footer}</footer>}
      </aside>
    </>,
    document.body
  );
}

interface DrawerSectionProps {
  title: string;
  children: ReactNode;
}

export function DrawerSection({ title, children }: DrawerSectionProps) {
  return (
    <section className="flex flex-col gap-2.5">
      <h3 className="tn-section-title">{title}</h3>
      {children}
    </section>
  );
}

const SIDE_WIDTH = { sm: 440, md: 520, lg: 680, xl: 860, full: 1040 } as const;

interface SideModalContextValue {
  onClose: () => void;
  titleId: string;
  closing: boolean;
}

const SideModalContext = createContext<SideModalContextValue>({
  onClose: () => undefined,
  titleId: "",
  closing: false,
});

interface SideModalRootProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  children: ReactNode;
}

function SideModalRoot({
  open = true,
  onOpenChange,
  children,
}: SideModalRootProps) {
  const titleId = useId();
  const [closing, setClosing] = useState(false);
  const closeHandler = useRef(() => onOpenChange?.(false));
  useEffect(() => {
    closeHandler.current = () => onOpenChange?.(false);
  });
  const timer = useRef<number | null>(null);
  useEffect(
    () => () => {
      if (timer.current !== null) window.clearTimeout(timer.current);
    },
    []
  );
  const value = useMemo(
    () => ({
      onClose: () => {
        if (timer.current !== null) return;
        setClosing(true);
        timer.current = window.setTimeout(() => {
          timer.current = null;
          setClosing(false);
          closeHandler.current();
        }, EXIT_MS);
      },
      titleId,
      closing,
    }),
    [titleId, closing]
  );
  if (!open) return null;
  return (
    <SideModalContext.Provider value={value}>
      {children}
    </SideModalContext.Provider>
  );
}

interface SideModalContentProps {
  width?: keyof typeof SIDE_WIDTH;
  children: ReactNode;
  /** Accepted for parity with the Opal modal; a drawer has no position. */
  position?: "center" | "top";
  height?: string;
  preventAccidentalClose?: boolean;
}

function SideModalContent({ width = "md", children }: SideModalContentProps) {
  const { onClose, titleId, closing } = useContext(SideModalContext);
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  if (!mounted) return null;
  return createPortal(
    <>
      <div
        aria-hidden
        className="tn-scrim"
        data-state={closing ? "closing" : "open"}
        onClick={onClose}
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="tn-drawer"
        data-state={closing ? "closing" : "open"}
        style={{ width: SIDE_WIDTH[width] }}
      >
        {children}
      </aside>
    </>,
    document.body
  );
}

interface SideModalHeaderProps {
  title: string;
  description?: string;
  icon?: IconFunctionComponent;
  onClose?: () => void;
}

function SideModalHeader({
  title,
  description,
  icon: Icon,
  onClose,
}: SideModalHeaderProps) {
  const context = useContext(SideModalContext);
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    closeRef.current?.focus();
  }, []);
  return (
    <header className="tn-drawer-head">
      {Icon && (
        <span className="tn-drawer-icon" aria-hidden>
          <Icon size={18} />
        </span>
      )}
      <div className="tn-drawer-heading">
        <h2 id={context.titleId} className="tn-drawer-title">
          {title}
        </h2>
        {description && <p className="tn-drawer-description">{description}</p>}
      </div>
      <div className="tn-drawer-tools">
        <button
          ref={closeRef}
          type="button"
          className="tn-icon-btn ton-focusable"
          aria-label={COPY.kit.close}
          onClick={context.onClose}
        >
          <SvgX size={16} />
        </button>
      </div>
    </header>
  );
}

interface SideModalSectionProps {
  children: ReactNode;
  /** Accepted for parity with the Opal modal sections. */
  twoTone?: boolean;
  alignItems?: string;
  justifyContent?: string;
}

function SideModalBody({ children }: SideModalSectionProps) {
  return <div className="tn-drawer-body">{children}</div>;
}

function SideModalFooter({ children }: SideModalSectionProps) {
  return <footer className="tn-drawer-foot justify-end">{children}</footer>;
}

/**
 * Same parts as the Opal modal (Content, Header, Body, Footer), drawn as the
 * side drawer: every registration in the TON opens beside the page.
 */
export const SideModal = Object.assign(SideModalRoot, {
  Content: SideModalContent,
  Header: SideModalHeader,
  Body: SideModalBody,
  Footer: SideModalFooter,
});
