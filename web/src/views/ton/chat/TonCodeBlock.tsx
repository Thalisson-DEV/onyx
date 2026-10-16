"use client";

import { useMemo } from "react";
import hljs from "highlight.js/lib/core";
import python from "highlight.js/lib/languages/python";
import { CopyButton, Text } from "@opal/components";
import "@/app/app/message/custom-code-styles.css";
import { COPY } from "@/lib/ton/copy";

hljs.registerLanguage("python", python);

const WORK = COPY.work;

interface TonCodeBlockProps {
  /** Source or console text to show. */
  text: string;
  /** "python" highlights the source; "output" shows console text as is. */
  kind: "python" | "output";
}

/**
 * Read-only code viewer for the assistant's helper calculations: a header with
 * the language, the line count and a copy action, then numbered lines.
 * highlight.js escapes the source before adding its spans, so the generated
 * HTML is safe to inject.
 */
export default function TonCodeBlock({ text, kind }: TonCodeBlockProps) {
  // Drop blank lines around the program but keep the first line's indent.
  const source = text.replace(/^(?:[ \t]*\n)+/, "").replace(/\s+$/, "");
  const lines = useMemo(() => {
    if (kind !== "python") return source.split("\n").map(escapeHtml);
    try {
      // Highlight the whole program once so multi-line strings keep their
      // colors, then split the HTML back into lines.
      return splitHighlighted(
        hljs.highlight(source, { language: "python", ignoreIllegals: true })
          .value
      );
    } catch {
      return source.split("\n").map(escapeHtml);
    }
  }, [source, kind]);

  return (
    <div className="ton-codeblock">
      <div className="ton-codeblock-head">
        <span className="ton-codeblock-lang">
          {kind === "python" ? WORK.python.language : WORK.python.output}
        </span>
        <Text font="secondary-body" color="text-03">
          {WORK.python.lines(lines.length)}
        </Text>
        <span className="flex-1" />
        <CopyButton size="sm" getCopyText={() => source}>
          {WORK.python.copy}
        </CopyButton>
      </div>
      <pre className="ton-codeblock-body hljs">
        <code>
          {lines.map((html, index) => (
            <span key={index} className="ton-codeblock-line">
              <span className="ton-codeblock-num" aria-hidden>
                {index + 1}
              </span>
              <span dangerouslySetInnerHTML={{ __html: html || " " }} />
            </span>
          ))}
        </code>
      </pre>
    </div>
  );
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

/** Splits hljs HTML into lines, closing and reopening spans across breaks. */
function splitHighlighted(html: string): string[] {
  const out: string[] = [];
  const open: string[] = [];
  let line = "";
  const tokens = html.split(/(<span[^>]*>|<\/span>|\n)/);
  for (const token of tokens) {
    if (token === "\n") {
      out.push(line + "</span>".repeat(open.length));
      line = open.join("");
    } else if (token.startsWith("<span")) {
      open.push(token);
      line += token;
    } else if (token === "</span>") {
      open.pop();
      line += token;
    } else {
      line += token;
    }
  }
  out.push(line + "</span>".repeat(open.length));
  return out;
}
