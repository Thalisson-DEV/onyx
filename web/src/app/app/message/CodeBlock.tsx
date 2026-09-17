import { cn } from "@opal/utils";
import Text from "@/refresh-components/texts/Text";
import React, { ReactNode, useMemo, memo } from "react";
import { SvgCode } from "@opal/icons";
import { CopyButton } from "@opal/components";
import { useTranslations } from "next-intl";

interface CodeBlockProps {
  className?: string;
  children?: ReactNode;
  codeText: string;
  showHeader?: boolean;
  noPadding?: boolean;
}

const MemoizedCodeLine = memo(({ content }: { content: ReactNode }) => (
  <>{content}</>
));

export const CodeBlock = memo(function CodeBlock({
  className = "",
  children,
  codeText,
  showHeader = true,
  noPadding = false,
}: CodeBlockProps) {
  const t = useTranslations("chat.messages");

  const language = useMemo(() => {
    return className
      .split(" ")
      .filter((cls) => cls.startsWith("language-"))
      .map((cls) => cls.replace("language-", ""))
      .join(" ");
  }, [className]);

  if (typeof children === "string" && !language) {
    return (
      // dir="ltr": code is always LTR, even inside RTL prose. The dir
      // attribute also bidi-isolates the run from the surrounding text.
      <span
        dir="ltr"
        data-testid="code-block"
        className={cn(
          "font-mono",
          "text-text-05",
          "bg-background-tint-00",
          "rounded-sm",
          "text-[0.75em]",
          "inline",
          "whitespace-pre-wrap",
          "wrap-break-word",
          "py-0.5",
          "px-1",
          className
        )}
      >
        {children}
      </span>
    );
  }

  // Concentric with the wrapper: inner radius = outer radius - the gap between
  // the two boxes. Both come from vars the wrapper sets, so they stay in sync.
  const innerRounding =
    "rounded-[calc(var(--code-block-radius,0px)-var(--code-block-gap,0px))]!";

  const CodeContent = () => {
    if (!language) {
      return (
        // dir="ltr" on both pre branches: code is always LTR, even when
        // the surrounding message resolved to RTL.
        <pre
          dir="ltr"
          className={cn(
            "p-2! m-0 overflow-x-auto w-0 min-w-full hljs",
            innerRounding
          )}
        >
          <code className={`text-sm hljs ${className}`}>
            {Array.isArray(children)
              ? children.map((child, index) => (
                  <MemoizedCodeLine key={index} content={child} />
                ))
              : children}
          </code>
        </pre>
      );
    }

    return (
      <pre
        dir="ltr"
        className={cn(
          "p-2! m-0 overflow-x-auto w-0 min-w-full hljs",
          innerRounding
        )}
      >
        <code className="text-xs">
          {Array.isArray(children)
            ? children.map((child, index) => (
                <MemoizedCodeLine key={index} content={child} />
              ))
            : children}
        </code>
      </pre>
    );
  };

  return (
    <>
      {showHeader ? (
        <div
          className={cn(
            "bg-background-tint-00 rounded-12 max-w-full min-w-0",
            "[--code-block-radius:var(--radius-12)]",
            noPadding
              ? "[--code-block-gap:0px]"
              : "px-1 pb-1 [--code-block-gap:0.25rem]"
          )}
        >
          {language && (
            <div className="flex items-center px-2 py-1 text-sm text-text-04 gap-x-2">
              <SvgCode
                height={12}
                width={12}
                stroke="currentColor"
                className="my-auto"
              />
              <Text secondaryMono>{language}</Text>
              {/* The shared Opal primitive owns the copied feedback (the icon
                  swaps to a check for 3s), the accessible name and the error
                  state, so the hand-rolled raw <button> that reimplemented
                  them is gone. The label keeps the affordance visible. */}
              {codeText && (
                <div className="ms-auto">
                  <CopyButton
                    prominence="tertiary"
                    size="sm"
                    getCopyText={() => codeText}
                  >
                    {t("codeBlock.copyButton.label")}
                  </CopyButton>
                </div>
              )}
            </div>
          )}
          <CodeContent />
        </div>
      ) : (
        <CodeContent />
      )}
    </>
  );
});

CodeBlock.displayName = "CodeBlock";
MemoizedCodeLine.displayName = "MemoizedCodeLine";
