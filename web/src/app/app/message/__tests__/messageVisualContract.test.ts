import fs from "node:fs";
import path from "node:path";

const WEB_ROOT = path.resolve(__dirname, "../../../../..");
const read = (relativePath: string): string =>
  fs.readFileSync(path.join(WEB_ROOT, relativePath), "utf8");
const stripComments = (source: string): string =>
  source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

const HUMAN = "src/app/app/message/HumanMessage.tsx";
const TOOLBAR = "src/app/app/message/messageComponents/MessageToolbar.tsx";
const MARKDOWN = "src/app/app/message/messageComponents/markdownUtils.tsx";
const MESSAGE_TEXT =
  "src/app/app/message/messageComponents/renderers/MessageTextRenderer.tsx";
const MINIMAL_MARKDOWN = "src/components/chat/MinimalMarkdown.tsx";
const CODE = "src/app/app/message/CodeBlock.tsx";
const CODE_CSS = "src/app/app/message/custom-code-styles.css";
const ERROR = "src/app/app/message/Resubmit.tsx";
const COMPLETED =
  "src/app/app/message/messageComponents/timeline/headers/CompletedHeader.tsx";
const STOPPED =
  "src/app/app/message/messageComponents/timeline/headers/StoppedHeader.tsx";

describe("TON message visual contract", () => {
  test("uses restrained user geometry and keeps VIS-005 attachments", () => {
    const source = stripComments(read(HUMAN));
    expect(source).toContain("rounded-08 bg-surface py-2 px-3");
    expect(source).not.toMatch(/rounded-t-16|rounded-es-16|shadow-/);
    expect(source).toContain("<FileDisplay files={files || []} />");
  });

  test("uses one tokenized markdown theme", () => {
    for (const file of [MARKDOWN, MESSAGE_TEXT, MINIMAL_MARKDOWN]) {
      const source = stripComments(read(file));
      expect(source).toContain("prose-ton");
      expect(source).not.toMatch(/prose-onyx|dark:prose-invert/);
    }
  });

  test("defines heading hierarchy and a dense overflow-safe table", () => {
    const css = stripComments(read(CODE_CSS));
    expect(css).toMatch(/\.prose-ton h1\s*\{[\s\S]*?font-size:\s*1\.5em/);
    expect(css).toMatch(/\.prose-ton h2\s*\{[\s\S]*?font-size:\s*1\.25em/);
    expect(css).toContain("border-collapse: collapse");
    expect(css).toMatch(/\.prose-ton th\s*\{[\s\S]*?border:/);
    expect(css).toMatch(/\.prose-ton td\s*\{[\s\S]*?border:/);
    expect(css).toMatch(
      /\.markdown-table-breakout\s*\{[\s\S]*?overflow-x:\s*auto/
    );
  });

  test("uses semantic syntax tokens without Atom One colors or glow", () => {
    const css = stripComments(read(CODE_CSS));
    expect(css).toContain("var(--code-keyword)");
    expect(css).toContain("var(--code-string)");
    expect(css).not.toMatch(/#[0-9a-fA-F]{3,8}\b|\.dark\s|box-shadow/);
  });

  test("uses the Opal copy control for code", () => {
    const source = stripComments(read(CODE));
    expect(source).toContain('import { CopyButton } from "@opal/components"');
    expect(source).toContain("getCopyText={() => codeText}");
    expect(source).not.toMatch(/<button|navigator\.clipboard/);
  });

  test("uses semantic error roles", () => {
    const source = stripComments(read(ERROR));
    expect(source).toContain("border-border-subtle");
    expect(source).toContain("bg-background-code-01");
    expect(source).not.toMatch(
      /\bdark:|\b(?:text|bg|border)-(?:red|neutral|gray)-\d+/
    );
  });

  test("keeps message actions visible and keyboard reachable", () => {
    const source = stripComments(read(TOOLBAR));
    expect(source).toContain('role="group"');
    expect(source).toContain('aria-label={t("toolbar.group.ariaLabel")}');
    expect(source).not.toMatch(/pointer-events-none|appear-on-hover/);
  });

  test.each([COMPLETED, STOPPED])(
    "%s has no nested interactive row",
    (file) => {
      const source = stripComments(read(file));
      expect(source).toContain("<Button");
      expect(source).not.toMatch(
        /role="button"|tabIndex=|onKeyDown=|clickOnKeyDown/
      );
    }
  );
});
