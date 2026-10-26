/**
 * The TON ends an answer with "Próximos passos:" and a short list of requests
 * the person can click. The list leaves the text and becomes buttons; any
 * other content after the heading keeps the answer as written.
 */

const HEADING =
  /(?:^|\n)[ \t]*(?:#{1,6}[ \t]*)?(?:\*\*|__)?[ \t]*pr[oó]ximos passos[ \t]*(?:\*\*|__)?[ \t]*:?[ \t]*(?:\*\*|__)?[ \t]*(?=\n|$)/gi;
const ITEM = /^[ \t]*(?:[-*•]|\d+[.)])[ \t]+(.+?)[ \t]*$/;

export interface SplitAnswer {
  body: string;
  steps: string[];
}

function clean(item: string): string {
  return item
    .replace(/\*\*|__|`/g, "")
    .replace(/^["“]|["”]$/g, "")
    .replace(/[.;]$/, "")
    .trim();
}

export function splitNextSteps(text: string): SplitAnswer {
  let last: RegExpExecArray | null = null;
  for (const match of text.matchAll(HEADING)) last = match;
  if (!last) return { body: text, steps: [] };
  const rest = text.slice(last.index + last[0].length);
  const lines = rest.split("\n").filter((line) => line.trim());
  // Mid-stream the list may not have started; hide the heading already.
  if (!lines.every((line) => ITEM.test(line))) return { body: text, steps: [] };
  const steps = lines
    .map((line) => clean(ITEM.exec(line)?.[1] ?? ""))
    .filter((step) => step.length > 0 && step.length <= 120)
    .slice(0, 4);
  return { body: text.slice(0, last.index).trimEnd(), steps };
}
