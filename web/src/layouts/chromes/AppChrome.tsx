"use client";

import { useCallback, useRef, useState, type ReactNode } from "react";
import { RootLayout, RootLayoutRightPanelSlotContext } from "@opal/layouts";
import AppHeader from "@/layouts/chromes/AppHeader";
import { cn, markdown } from "@opal/utils";
import { INTERACTIVE_SELECTOR } from "@/lib/utils";
import { useAppBackground } from "@/providers/AppBackgroundProvider";
import { useTheme } from "next-themes";
import useBrowserInfo from "@/hooks/useBrowserInfo";
import { Text } from "@opal/components";
import { useAppDocumentTitle, useCustomFooterContent } from "@/lib/app/hooks";
import { useAppPosition } from "@/lib/position/hooks";

// ---------------------------------------------------------------------------
// Footer
// ---------------------------------------------------------------------------

function Footer() {
  const customFooterContent = useCustomFooterContent();

  return (
    <RootLayout.Footer>
      {/* Padding is unconditional. It used to drop its top half during chat, to
          absorb a spacer the composer's old shadow needed; the composer is
          border-defined now, so neither the spacer nor the compensation exists.
          See plans/ton/frontend/004-composer.md. */}
      <div
        className={
          // Wrapping a long disclaimer needs both halves. `[&>*]:min-w-0`
          // lets the text shrink, since a flex item's min-width is `auto`
          // and otherwise holds it at its min-content width. `wordWrap` on
          // the Text below then lets an unbroken run split, which ordinary
          // wrapping will not do — it only breaks at whitespace, so a
          // pasted URL or one long token would still overflow.
          "relative w-full flex flex-row justify-center items-center gap-2 px-2 sm:px-4 py-2 mt-auto [&>*]:min-w-0"
        }
      >
        <Text
          font="secondary-action"
          color="text-03"
          as="p"
          wordWrap="wrap-anywhere"
          textPosition="text-center"
        >
          {markdown(customFooterContent)}
        </Text>
      </div>
    </RootLayout.Footer>
  );
}

// ---------------------------------------------------------------------------
// AppChrome
// ---------------------------------------------------------------------------

interface AppChromeProps {
  children: React.ReactNode;
}

export default function AppChrome({ children }: AppChromeProps) {
  const [rightPanel, setRightPanel] = useState<ReactNode>(null);

  const appPosition = useAppPosition();
  useAppDocumentTitle();

  const { hasBackground, appBackgroundUrl } = useAppBackground();
  const { resolvedTheme } = useTheme();
  const { isSafari } = useBrowserInfo();
  const isLightMode = resolvedTheme === "light";
  const showBackground =
    hasBackground && (appPosition.isChat() || appPosition.isNewSession());

  /* A mask, so the colour stops are alpha channels, not paint: `black` here
     means "keep", `transparent` means "drop". They are not theme colours and are
     the correct literals for the job. The width is the reading measure, so it
     reads from the same variable the transcript and the composer use instead of
     repeating 25rem. */
  const horizontalBlurMask = `linear-gradient(
    to right,
    transparent 0%,
    black max(0%, calc(50% - var(--app-page-main-content-width) / 2)),
    black min(100%, calc(50% + var(--app-page-main-content-width) / 2)),
    transparent 100%
  )`;

  const inputWasFocused = useRef(false);

  // Track whether the chat input was focused before a mousedown, so we can
  // restore focus on mouseup if no text was selected. This preserves
  // click-drag text selection while keeping the input focused on plain clicks.
  const handleMouseDown = useCallback(
    (event: React.MouseEvent<HTMLDivElement>) => {
      const activeEl = document.activeElement;
      const isFocused =
        activeEl instanceof HTMLElement &&
        activeEl.id === "onyx-chat-input-textbox";
      const target = event.target;
      const isInteractive =
        target instanceof HTMLElement && !!target.closest(INTERACTIVE_SELECTOR);
      inputWasFocused.current = isFocused && !isInteractive;
    },
    []
  );

  const handleMouseUp = useCallback(() => {
    if (!inputWasFocused.current) return;
    inputWasFocused.current = false;
    const sel = window.getSelection();
    if (sel && !sel.isCollapsed) return;
    const textarea = document.getElementById("onyx-chat-input-textbox");
    if (textarea && document.activeElement !== textarea) {
      textarea.focus();
    }
  }, []);

  return (
    <RootLayoutRightPanelSlotContext.Provider value={setRightPanel}>
      <RootLayout.App
        data-main-container
        onMouseDown={handleMouseDown}
        onMouseUp={handleMouseUp}
      >
        <div className="flex flex-row flex-1 min-h-0">
          <div
            className={cn(
              "@container relative isolate flex-1 flex flex-col min-h-0",
              showBackground && "bg-cover bg-center bg-fixed"
            )}
            style={
              showBackground
                ? { backgroundImage: `url(${appBackgroundUrl})` }
                : undefined
            }
          >
            {/* Effect 1 — Vignette overlay for custom backgrounds (disabled in light mode).
              z-[-1] keeps overlays below the normal-flow header/content/footer.
              The scrim reads `--mask-02` instead of a raw `rgba(0, 0, 0, 0.4)`:
              same role, same ladder as every other scrim in the app, and it now
              follows the theme. The effect only exists when an operator has set a
              custom background image, so it is a configured surface rather than
              decoration TON added. */}
            {showBackground && !isLightMode && (
              <div
                className="absolute z-[-1] inset-0 pointer-events-none"
                style={{
                  background: `
                  linear-gradient(to bottom, var(--mask-02) 0%, transparent 4rem),
                  linear-gradient(to top, var(--mask-02) 0%, transparent 4rem)
                `,
                }}
              />
            )}
            {/* Effect 2 — Semi-transparent overlay for readability when background is set */}
            {showBackground && appPosition.isChat() && (
              <>
                <div className="absolute z-[-1] inset-0 backdrop-blur-[1px] pointer-events-none" />
                {isSafari ? (
                  <div
                    className="absolute z-[-1] inset-0 bg-cover bg-center bg-fixed pointer-events-none"
                    style={{
                      backgroundImage: `url(${appBackgroundUrl})`,
                      filter: "blur(16px)",
                      maskImage: horizontalBlurMask,
                      WebkitMaskImage: horizontalBlurMask,
                    }}
                  />
                ) : (
                  <div
                    className="absolute z-[-1] inset-0 backdrop-blur-md transition-all duration-600 pointer-events-none"
                    style={{
                      maskImage: horizontalBlurMask,
                      WebkitMaskImage: horizontalBlurMask,
                    }}
                  />
                )}
              </>
            )}

            {/* Header */}
            <AppHeader />
            <RootLayout.MainContent>{children}</RootLayout.MainContent>
            <Footer />
          </div>
          {rightPanel}
        </div>
      </RootLayout.App>
    </RootLayoutRightPanelSlotContext.Provider>
  );
}
