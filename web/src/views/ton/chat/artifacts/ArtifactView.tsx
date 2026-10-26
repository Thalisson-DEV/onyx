"use client";

import {
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
} from "react";
import { CompactMarkdown } from "@opal/components";
import { cn } from "@opal/utils";
import {
  formatArtifactValue,
  isNumericCell,
  type ArtifactBlock,
  type ArtifactSeries,
  type ArtifactSlide,
  type ArtifactFormat,
  type TonArtifact,
} from "@/lib/ton/artifacts";

const MARK = "/ton/vale-norte-mark.png";

function Kpis({ block }: { block: Extract<ArtifactBlock, { type: "kpis" }> }) {
  return (
    <div className="tn-art-kpis" data-count={block.items.length}>
      {block.items.map((item, index) => (
        <div key={index} className="tn-art-kpi">
          <span className="tn-art-kpi-label">{item.label}</span>
          <span className="tn-art-kpi-value">
            {item.display ??
              (item.value !== null
                ? formatArtifactValue(item.value, "number")
                : "—")}
          </span>
          {item.note && (
            <span className="tn-art-kpi-note" data-tone={item.tone}>
              {item.note}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

function Bars({
  block,
}: {
  block: Extract<ArtifactBlock, { type: "barras" }>;
}) {
  const max = Math.max(
    ...block.items.map((item) => Math.abs(item.value ?? 0)),
    1
  );
  return (
    <div className="tn-art-bars" role="list">
      {block.items.map((item, index) => {
        const value = item.value ?? 0;
        return (
          <div key={index} className="tn-art-bar" role="listitem">
            <span className="tn-art-bar-label" title={item.label}>
              {item.label}
            </span>
            <span className="tn-art-bar-track" aria-hidden>
              <span
                className="tn-art-bar-fill"
                data-tone={value < 0 ? "bad" : item.tone}
                style={{ width: `${(Math.abs(value) / max) * 100}%` }}
              />
            </span>
            <span className="tn-art-bar-value">
              {item.display ?? formatArtifactValue(value, block.format)}
            </span>
            {item.note && <span className="tn-art-bar-note">{item.note}</span>}
          </div>
        );
      })}
    </div>
  );
}

const W = 640;
const H = 220;
const PAD = { top: 12, right: 16, bottom: 28, left: 72 };

function niceTicks(min: number, max: number): number[] {
  const span = max - min || Math.abs(max) || 1;
  const step = 10 ** Math.floor(Math.log10(span / 4));
  const unit = [1, 2, 2.5, 5, 10].find((m) => span / (m * step) <= 5) ?? 10;
  const size = unit * step;
  const start = Math.floor(min / size) * size;
  const ticks: number[] = [];
  for (let tick = start; tick <= max + size * 0.5; tick += size)
    ticks.push(tick);
  return ticks;
}

function Line({
  series,
  format,
}: {
  series: ArtifactSeries[];
  format: ArtifactFormat;
}) {
  const labels = series[0]?.points.map((point) => point.label) ?? [];
  const values = series.flatMap((serie) => serie.points.map((p) => p.value));
  const ticks = niceTicks(Math.min(0, ...values), Math.max(...values));
  const lo = ticks[0] ?? 0;
  const hi = ticks[ticks.length - 1] ?? 1;
  const x = (index: number) =>
    PAD.left +
    (labels.length <= 1
      ? (W - PAD.left - PAD.right) / 2
      : (index / (labels.length - 1)) * (W - PAD.left - PAD.right));
  const y = (value: number) =>
    PAD.top + (1 - (value - lo) / (hi - lo || 1)) * (H - PAD.top - PAD.bottom);
  // Short labels (jan, fev…) all fit; longer ones are thinned out.
  const fits = labels.every((label) => label.length <= 4) ? 12 : 8;
  const every = Math.ceil(labels.length / fits);
  return (
    <figure className="tn-art-line">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={series.map((serie) => serie.name).join(", ")}
      >
        {ticks.map((tick) => (
          <g key={tick}>
            <line
              x1={PAD.left}
              x2={W - PAD.right}
              y1={y(tick)}
              y2={y(tick)}
              className="tn-art-grid"
            />
            <text
              x={PAD.left - 8}
              y={y(tick) + 4}
              textAnchor="end"
              className="tn-art-axis"
            >
              {formatArtifactValue(tick, format)}
            </text>
          </g>
        ))}
        {labels.map((label, index) =>
          index % every === 0 ? (
            <text
              key={label + index}
              x={x(index)}
              y={H - 8}
              textAnchor="middle"
              className="tn-art-axis"
            >
              {label}
            </text>
          ) : null
        )}
        {series.map((serie, index) => (
          <g key={serie.name + index} data-series={index}>
            <polyline
              fill="none"
              className="tn-art-series"
              points={serie.points
                .map((point, i) => `${x(i)},${y(point.value)}`)
                .join(" ")}
            />
            {serie.points.map((point, i) => (
              <circle
                key={i}
                cx={x(i)}
                cy={y(point.value)}
                r={3}
                className="tn-art-dot"
              >
                <title>{`${serie.name} · ${point.label}: ${formatArtifactValue(point.value, format)}`}</title>
              </circle>
            ))}
          </g>
        ))}
      </svg>
      {series.length > 1 && (
        <figcaption className="tn-art-legend">
          {series.map((serie, index) => (
            <span key={serie.name + index} data-series={index}>
              {serie.name}
            </span>
          ))}
        </figcaption>
      )}
    </figure>
  );
}

function Table({
  block,
}: {
  block: Extract<ArtifactBlock, { type: "tabela" }>;
}) {
  // A money column stays right-aligned even with a "sem cálculo" among the
  // numbers: most filled cells being numbers is enough.
  const numeric = useMemo(
    () =>
      block.columns.map((_, column) => {
        if (column === 0) return false;
        const filled = block.rows
          .map((row) => row[column])
          .filter((cell) => cell !== undefined && cell !== "");
        const numbers = filled.filter((cell) => isNumericCell(cell!)).length;
        return numbers > 0 && numbers * 2 >= filled.length;
      }),
    [block]
  );
  return (
    <div className="tn-art-table-wrap">
      <table className="tn-art-table">
        <thead>
          <tr>
            {block.columns.map((column, index) => (
              <th
                key={index}
                scope="col"
                className={cn(numeric[index] && "tn-num")}
              >
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {block.rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {block.columns.map((_, index) => (
                <td key={index} className={cn(numeric[index] && "tn-num")}>
                  {row[index] ?? ""}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function BlockView({ block }: { block: ArtifactBlock }) {
  return (
    <section className="tn-art-block" data-type={block.type}>
      {block.title && <h4 className="tn-art-block-title">{block.title}</h4>}
      {block.type === "kpis" && <Kpis block={block} />}
      {block.type === "barras" && <Bars block={block} />}
      {block.type === "linha" && (
        <Line series={block.series} format={block.format} />
      )}
      {block.type === "tabela" && <Table block={block} />}
      {block.type === "texto" && (
        <CompactMarkdown className="tn-art-text">{block.body}</CompactMarkdown>
      )}
    </section>
  );
}

/** Slides are laid out at 1280×720 and scaled, so a slide looks the same
 * in the side panel, on the presenter and on paper. */
const SLIDE_WIDTH = 1280;

function useSlideScale() {
  const ref = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(0.5);
  useLayoutEffect(() => {
    const node = ref.current;
    if (!node) return;
    const measure = () => {
      const width = node.clientWidth;
      if (width > 0) setScale(width / SLIDE_WIDTH);
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  return { ref, scale };
}

export function SlideView({
  slide,
  index,
  total,
}: {
  slide: ArtifactSlide;
  index: number;
  total: number;
}) {
  const { ref, scale } = useSlideScale();
  return (
    <div
      ref={ref}
      className="tn-art-slide-frame"
      // SAFETY: a CSS custom property; React passes it through untouched.
      style={{ "--tn-slide-scale": scale } as CSSProperties}
    >
      <SlideCanvas slide={slide} index={index} total={total} />
    </div>
  );
}

function SlideCanvas({
  slide,
  index,
  total,
}: {
  slide: ArtifactSlide;
  index: number;
  total: number;
}) {
  return (
    <article
      className="tn-art-slide"
      data-has-block={slide.block ? "" : undefined}
    >
      <img src={MARK} alt="" className="tn-art-slide-mark" />
      <div className="tn-art-slide-copy">
        {slide.kicker && (
          <span className="tn-art-slide-kicker">{slide.kicker}</span>
        )}
        <h3 className="tn-art-slide-title">{slide.title}</h3>
        {slide.body && (
          <CompactMarkdown className="tn-art-slide-body">
            {slide.body}
          </CompactMarkdown>
        )}
        {slide.metric && (
          <p className="tn-art-slide-metric">
            {slide.metric.value}
            <small>{slide.metric.label}</small>
          </p>
        )}
      </div>
      {slide.block && (
        <div className="tn-art-slide-block">
          <BlockView block={slide.block} />
        </div>
      )}
      <span className="tn-art-slide-page">{`${index + 1} / ${total}`}</span>
    </article>
  );
}

export function DashboardView({ artifact }: { artifact: TonArtifact }) {
  return (
    <div className="tn-art-sheet">
      <header className="tn-art-sheet-head">
        <h3>{artifact.title}</h3>
        {artifact.subtitle && <p>{artifact.subtitle}</p>}
      </header>
      {artifact.blocks.map((block, index) => (
        <BlockView key={index} block={block} />
      ))}
    </div>
  );
}

export function ReportView({ artifact }: { artifact: TonArtifact }) {
  const issued = new Date(artifact.created_at).toLocaleDateString("pt-BR");
  return (
    <div className="tn-art-page">
      <header className="tn-art-page-head">
        <img src={MARK} alt="" width={22} height={22} />
        <span>Vale Norte · Controladoria</span>
        <span className="flex-1" />
        <span>{`Emitido em ${issued}`}</span>
      </header>
      <h3 className="tn-art-page-title">{artifact.title}</h3>
      {artifact.subtitle && (
        <p className="tn-art-page-sub">{artifact.subtitle}</p>
      )}
      {artifact.blocks.map((block, index) => (
        <BlockView key={index} block={block} />
      ))}
      {artifact.sources.length > 0 && (
        <footer className="tn-art-page-foot">
          {`Fontes: ${artifact.sources.join(" · ")}`}
        </footer>
      )}
    </div>
  );
}

export function ArtifactBody({
  artifact,
  slide,
  onSlide,
}: {
  artifact: TonArtifact;
  slide: number;
  onSlide: (index: number) => void;
}) {
  if (artifact.artifact_kind === "apresentacao") {
    const current = artifact.slides[slide] ?? artifact.slides[0];
    return (
      <div className="tn-art-deck">
        {current && (
          <SlideView
            slide={current}
            index={Math.min(slide, artifact.slides.length - 1)}
            total={artifact.slides.length}
          />
        )}
        <ol className="tn-art-thumbs" aria-label="Slides">
          {artifact.slides.map((item, index) => (
            <li key={index}>
              {/* A slide thumbnail is a whole-card target. */}
              <button
                type="button"
                className="tn-art-thumb ton-focusable"
                aria-current={index === slide || undefined}
                onClick={() => onSlide(index)}
              >
                <span className="tn-art-thumb-frame" aria-hidden>
                  <span>{item.title}</span>
                </span>
                <span className="tn-art-thumb-label">{`${index + 1} · ${item.kicker ?? item.title}`}</span>
              </button>
            </li>
          ))}
        </ol>
        {/* Printing lays every slide on its own page. */}
        <div className="tn-art-print-only">
          {artifact.slides.map((item, index) => (
            <SlideView
              key={index}
              slide={item}
              index={index}
              total={artifact.slides.length}
            />
          ))}
        </div>
      </div>
    );
  }
  if (artifact.artifact_kind === "relatorio")
    return <ReportView artifact={artifact} />;
  return <DashboardView artifact={artifact} />;
}
