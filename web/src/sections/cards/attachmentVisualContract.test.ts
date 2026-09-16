/**
 * TON-VIS-005 attachment contract.
 *
 * Some of what this slice delivers cannot be rendered in jsdom — the chat
 * viewport needs the session store, the query controller, the LLM manager,
 * voice, projects and the agent tree — and some of it is a styling invariant
 * that regresses silently. So this suite asserts those at source level, the way
 * `composerVisualContract.test.ts` and `dropzonePaste.test.tsx` already do.
 *
 * Behaviour that *can* be rendered is covered by `FileCard.test.tsx`,
 * `providers.test.tsx`, `utils.test.ts` and `fileCategory.test.ts`.
 */
import fs from "node:fs";
import path from "node:path";

import en from "@/i18n/messages/en.json";

const WEB_ROOT = path.resolve(__dirname, "../../..");

const read = (relativePath: string): string =>
  fs.readFileSync(path.join(WEB_ROOT, relativePath), "utf8");

/**
 * Comments explain what a rule replaced, so they must not be able to satisfy or
 * break an assertion about the rule itself.
 */
const stripComments = (source: string): string =>
  source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

const APP_PAGE = "src/views/AppPage.tsx";
const FILE_CARD = "src/sections/cards/FileCard.tsx";
const CHIP_STRIP = "src/sections/input/InputChipStrip.tsx";
const APP_INPUT_BAR = "src/sections/input/AppInputBar.tsx";
const PROVIDERS = "src/lib/projects/providers.tsx";
const PROJECT_CONTEXT = "src/lib/projects/components/ProjectContextPanel.tsx";
const SHARED_UTILS = "src/lib/utils.ts";

const FILE_PICKER = "src/refresh-components/popovers/FilePickerPopover.tsx";
const USER_FILES_MODAL = "src/sections/modals/UserFilesModal.tsx";

/** Every attachment surface this slice re-skinned. */
const ATTACHMENT_SOURCES = [
  FILE_CARD,
  CHIP_STRIP,
  PROJECT_CONTEXT,
  FILE_PICKER,
  USER_FILES_MODAL,
] as const;

/**
 * The surfaces that choose a glyph themselves. `ProjectContextPanel` is absent
 * on purpose: it renders `FileCard`, so it inherits the identity rather than
 * re-deriving it.
 */
const CATEGORY_CONSUMERS = [
  FILE_CARD,
  CHIP_STRIP,
  FILE_PICKER,
  USER_FILES_MODAL,
] as const;

/** An extension-to-icon ladder of the kind this slice replaced. */
const ICON_LADDER = /\/\\\.(pptx?|pdf)\$?\/i/;

// ---------------------------------------------------------------------------
// 1. One category function, consumed everywhere
// ---------------------------------------------------------------------------

describe("semantic file categories", () => {
  test("live in one shared module", () => {
    const utils = read(SHARED_UTILS);

    expect(utils).toContain("export enum FileCategory");
    expect(utils).toContain("export function fileCategory(");
    expect(utils).toContain("export function fileCategoryIcon(");
  });

  test("are seeded from the image list rather than a second copy", () => {
    const utils = stripComments(read(SHARED_UTILS));

    expect(utils).toMatch(
      /IMAGE_EXTENSIONS\.map\(\(ext\) => \[ext, FileCategory\.IMAGE\]/
    );
  });

  test.each(CATEGORY_CONSUMERS)("%s reads the shared category", (file) => {
    expect(stripComments(read(file))).toContain("fileCategoryIcon(");
  });

  test.each(ATTACHMENT_SOURCES)(
    "%s keeps no icon ladder of its own",
    (file) => {
      expect(stripComments(read(file))).not.toMatch(ICON_LADDER);
    }
  );

  test("only the image preview decision still asks isImageFile", () => {
    // "Can this be previewed?" is a different question from "what is this?",
    // and `isImageFile` seeds the IMAGE category, so the two cannot disagree.
    for (const file of ATTACHMENT_SOURCES) {
      const source = stripComments(read(file));
      if (file === FILE_CARD) continue;
      expect(source).not.toContain("isImageFile(");
    }
  });

  test("getFileIcon defers to the shared category instead of its own ladder", () => {
    const utils = stripComments(read(SHARED_UTILS));
    const body = /export function getFileIcon\([\s\S]*?\n\}/.exec(utils)?.[0];

    expect(body).toBeTruthy();
    expect(body).toContain("fileCategory(fileName)");
    expect(body).not.toMatch(ICON_LADDER);
  });
});

// ---------------------------------------------------------------------------
// 2. One attachment geometry
// ---------------------------------------------------------------------------

describe("attachment geometry", () => {
  const fileCard = stripComments(read(FILE_CARD));

  test("the row and the image tile share one radius constant", () => {
    expect(fileCard).toContain('const ATTACHMENT_RADIUS = "rounded-12"');
    // Used by both arms: the tile, its <img>, and the failed row's edge.
    expect(fileCard.match(/ATTACHMENT_RADIUS/g)?.length).toBeGreaterThanOrEqual(
      4
    );
  });

  test("the edge is a border in every state, so geometry does not move", () => {
    expect(fileCard).toContain("border-border-error");
    expect(fileCard).toContain("border-border-01");
    expect(fileCard).toContain("border={!isFailed}");
  });

  test("the chip sits inside the composer curve rather than echoing it", () => {
    // `radius-04` is the visual language's compact-control step; the composer
    // itself is `radius-12`.
    expect(stripComments(read(CHIP_STRIP))).toContain("rounded-04");
  });

  test.each(ATTACHMENT_SOURCES)("%s carries no shadow", (file) => {
    expect(stripComments(read(file))).not.toMatch(/shadow-(xs|sm|box-)/);
  });

  test.each(ATTACHMENT_SOURCES)("%s uses no dark: modifier", (file) => {
    expect(stripComments(read(file))).not.toMatch(/\bdark:/);
  });

  test.each(ATTACHMENT_SOURCES)("%s uses no raw hex colour", (file) => {
    expect(stripComments(read(file))).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
  });

  test.each(ATTACHMENT_SOURCES)(
    "%s uses no built-in Tailwind palette colour",
    (file) => {
      expect(stripComments(read(file))).not.toMatch(
        /\b(bg|text|border|stroke|fill)-(gray|neutral|slate|zinc|red|green|blue|amber|yellow|indigo|purple|pink)-\d{2,3}\b/
      );
    }
  );
});

// ---------------------------------------------------------------------------
// 3. Removal is explicit, quiet and reachable
// ---------------------------------------------------------------------------

describe("removal affordance", () => {
  const fileCard = stripComments(read(FILE_CARD));

  test("is an Opal Button, not a hand-rolled element", () => {
    expect(fileCard).toMatch(/function AttachmentRemoveButton\(/);
    expect(fileCard).toContain("<Button");
    expect(fileCard).not.toMatch(/<button[\s\S]{0,400}SvgX/);
  });

  test("is revealed by Hoverable, which stays visible on touch", () => {
    // Hoverable gates its hiding behind `@media (hover: hover)` and reveals on
    // group focus, so this is the touch and keyboard guarantee.
    expect(fileCard).toMatch(
      /<Hoverable\.Item[\s\S]{0,120}variant="appear-on-hover"/
    );
    expect(fileCard).toContain('Hoverable.Root group="attachmentRow"');
    expect(fileCard).toContain('Hoverable.Root group="attachmentTile"');
  });

  test("names the file it removes", () => {
    expect(fileCard).toContain(
      't("file.remove.ariaLabel", { name: fileName })'
    );
    expect(fileCard).toContain("aria-label={label}");
  });
});

// ---------------------------------------------------------------------------
// 4. State language describes real state
// ---------------------------------------------------------------------------

describe("state language", () => {
  test("the four states come from the shared derivation", () => {
    const utils = stripComments(read("src/lib/projects/utils.ts"));

    expect(utils).toContain("export enum AttachmentState");
    for (const state of [
      "UPLOADING",
      "PROCESSING",
      "READY",
      "FAILED",
      "DELETING",
    ]) {
      expect(utils).toContain(`${state} = "${state}"`);
    }
  });

  test("no surface invents a percentage", () => {
    for (const file of ATTACHMENT_SOURCES) {
      expect(stripComments(read(file))).not.toMatch(
        /progress|percent|\bpct\b|\d+%/i
      );
    }
  });

  test("the copy exists in the catalog for every state and category", () => {
    const file = en.cards.file;

    expect(file.uploading.description).toBeTruthy();
    expect(file.processing.description).toBeTruthy();
    expect(file.failed.description).toBeTruthy();
    expect(file.deleting.description).toBeTruthy();
    expect(file.remove.ariaLabel).toContain("{name}");
    expect(file.status.announcement).toContain("{status}");
    expect(Object.keys(file.category).sort()).toEqual([
      "archive",
      "audio",
      "document",
      "image",
      "other",
      "presentation",
      "spreadsheet",
      "video",
    ]);
  });
});

// ---------------------------------------------------------------------------
// 5. The failed file stays, and the send gate stays honest
// ---------------------------------------------------------------------------

describe("failed-file visibility", () => {
  test("the poller no longer drops failed files from currentMessageFiles", () => {
    const providers = stripComments(read(PROVIDERS));
    const merge =
      /setCurrentMessageFiles\(\(prev\) => \{[\s\S]*?\n {8}\}\);/.exec(
        providers
      )?.[0];

    expect(merge).toBeTruthy();
    expect(merge).not.toContain('=== "failed"');
  });

  test("the send gate is still keyed on uploading and indexing only", () => {
    const inputBar = stripComments(read(APP_INPUT_BAR));

    expect(inputBar).toContain("file.status === UserFileStatus.UPLOADING");
    expect(inputBar).toContain("file.status === UserFileStatus.PROCESSING");
    expect(inputBar).not.toContain("UserFileStatus.FAILED");
  });

  test("the transport boundary drops the failure instead of the UI hiding it", () => {
    const projectUtils = stripComments(read("src/lib/projects/utils.ts"));

    expect(projectUtils).toMatch(
      /projectFilesToFileDescriptors[\s\S]*?filter\(\(file\) => !isFailedAttachment\(file\.status\)\)/
    );
  });
});

// ---------------------------------------------------------------------------
// 6. Upload infrastructure preserved
// ---------------------------------------------------------------------------

describe("upload infrastructure", () => {
  const providers = stripComments(read(PROVIDERS));

  test("keeps the temp_<uuid> contract", () => {
    // AgentEditorPage is a second consumer of this prefix.
    expect(providers).toContain("`temp_${crypto.randomUUID()}`");
    expect(providers).toContain("temp_id: tempId");
  });

  test("keeps the optimistic insert, reconciliation and rollback", () => {
    expect(providers).toContain("createOptimisticFile");
    expect(providers).toContain("tempIdToUploadedFileMap");
    expect(providers).toContain("removeOptimisticFilesByTempIds");
  });

  test("keeps the size precheck and the 3s poll", () => {
    expect(providers).toContain("rawMax * 1024 * 1024");
    expect(providers).toContain("window.setInterval(poll, 3000)");
  });
});

// ---------------------------------------------------------------------------
// 7. Chat-wide drag feedback
// ---------------------------------------------------------------------------

describe("chat drag overlay", () => {
  const appPage = stripComments(read(APP_PAGE));
  const overlay = /function ChatDropOverlay\([\s\S]*?\n\}/.exec(appPage)?.[0];

  test("reads the Dropzone's own isDragActive", () => {
    expect(overlay).toBeTruthy();
    expect(appPage).toContain("{({ getRootProps, isDragActive }) => (");
    expect(appPage).toContain("<ChatDropOverlay active={isDragActive} />");
  });

  test("renders nothing when no drag is active, so drag-leave clears it", () => {
    expect(overlay).toContain("if (!active) return null;");
  });

  test("cannot shift layout or steal the drop", () => {
    expect(overlay).toContain("pointer-events-none");
    expect(overlay).toContain("absolute inset-0");
  });

  test("is a restrained veil with a dashed edge, not glass", () => {
    expect(overlay).toContain("bg-mask-02");
    expect(overlay).toContain("border border-dashed border-border-selected");
    expect(overlay).not.toMatch(/backdrop-blur|shadow-/);
  });

  test("respects reduced motion", () => {
    expect(overlay).toMatch(/motion-safe:animate-in/);
    expect(overlay).not.toMatch(/(?<!motion-safe:)\banimate-in\b/);
  });

  test("stays quiet for assistive technology", () => {
    // It narrates a pointer gesture AT is not performing; the accessible route
    // to attaching a file is the composer's file picker.
    expect(overlay).toContain("aria-hidden");
  });

  test("uses next-intl rather than hard-coded copy", () => {
    expect(overlay).toContain('t("dropzone.instruction")');
    expect(en.chat.app.dropzone.instruction).toBeTruthy();
    expect(en.chat.app.dropzone.description).toBeTruthy();
  });

  test("the project panel drag target speaks the same language", () => {
    const panel = stripComments(read(PROJECT_CONTEXT));

    expect(panel).toContain("border border-dashed border-border-selected");
    expect(panel).not.toContain("border-2 border-dashed");
  });
});

// ---------------------------------------------------------------------------
// 8. Empty states use the standard primitive
// ---------------------------------------------------------------------------

describe("empty states", () => {
  test.each([PROJECT_CONTEXT, USER_FILES_MODAL])(
    "%s uses IllustrationContent",
    (file) => {
      expect(stripComments(read(file))).toContain("<IllustrationContent");
    }
  );

  test.each([PROJECT_CONTEXT, USER_FILES_MODAL])(
    "%s adds no decorative illustration",
    (file) => {
      expect(stripComments(read(file))).not.toContain("illustration=");
    }
  );
});
