import type { ComponentType } from "react";
import type { IconFunctionComponent, IconProps } from "@opal/types";
import {
  SvgAudioFile,
  SvgFile,
  SvgFileBraces,
  SvgFileChartPie,
  SvgFiles,
  SvgFileText,
  SvgImage,
  SvgSpreadsheetFile,
  SvgVideoFile,
} from "@opal/icons";
import { ALLOWED_URL_PROTOCOLS } from "./constants";
import { DEFAULT_LOCALE } from "@/i18n/config";

const URI_SCHEME_REGEX = /^[a-zA-Z][a-zA-Z\d+.-]*:/;
const BARE_EMAIL_REGEX = /^[^\s@/]+@[^\s@/:]+\.[^\s@/:]+$/;

export const INTERACTIVE_SELECTOR =
  "a, button, input, textarea, select, label, [role='button'], [tabindex]:not([tabindex='-1']), [contenteditable]:not([contenteditable='false'])";

export const truncateString = (str: string, maxLength: number) => {
  return str.length > maxLength ? str.slice(0, maxLength - 1) + "..." : str;
};

/**
 * Ensures an href has a protocol, adding https:// only to bare domains.
 * Converts bare email addresses to mailto: links.
 * Preserves existing protocols, relative paths, and anchors.
 */
export function ensureHrefProtocol(
  href: string | undefined
): string | undefined {
  if (!href) return href;
  const trimmedHref = href.trim();
  if (!trimmedHref) return href;

  const needsProtocol =
    !URI_SCHEME_REGEX.test(trimmedHref) &&
    !trimmedHref.startsWith("/") &&
    !trimmedHref.startsWith("#");
  if (!needsProtocol) {
    return trimmedHref;
  }

  if (BARE_EMAIL_REGEX.test(trimmedHref)) {
    return `mailto:${trimmedHref}`;
  }

  return `https://${trimmedHref}`;
}

/**
 * Custom URL transformer function for ReactMarkdown.
 * Only allows a small, safe set of protocols and strips everything else.
 * Bare email addresses are normalized to mailto: links.
 * Returning null removes the href attribute entirely.
 */
export function transformLinkUri(href: string): string | null {
  if (!href) return null;

  const trimmedHref = href.trim();
  if (!trimmedHref) return null;

  try {
    const parsedUrl = new URL(trimmedHref);
    const protocol = parsedUrl.protocol.toLowerCase();

    if (ALLOWED_URL_PROTOCOLS.some((allowed) => allowed === protocol)) {
      return trimmedHref;
    }

    return null;
  } catch {
    if (BARE_EMAIL_REGEX.test(trimmedHref)) {
      return `mailto:${trimmedHref}`;
    }

    // Allow relative URLs, but drop anything that looks like a protocol-prefixed link
    if (URI_SCHEME_REGEX.test(trimmedHref)) {
      return null;
    }

    return trimmedHref;
  }
}

export function isSubset(parent: string[], child: string[]): boolean {
  const parentSet = new Set(parent);
  return Array.from(new Set(child)).every((item) => parentSet.has(item));
}

export function trinaryLogic<T>(
  a: boolean | undefined,
  b: boolean,
  ifTrue: T,
  ifFalse: T
): T {
  const condition = a !== undefined ? a : b;
  return condition ? ifTrue : ifFalse;
}

// A convenience function to prevent propagation of click events to items higher up in the DOM tree.
//
// # Note:
// This is a desired behaviour in MANY locations, since we have buttons nested within buttons.
// When the nested button is pressed, the click event that triggered it should (in most scenarios) NOT trigger its parent button!
export function noProp(
  f?: (event: React.MouseEvent) => void
): React.MouseEventHandler {
  return (event) => {
    event.stopPropagation();
    f?.(event);
  };
}

/**
 * Extracts the file extension from a filename and returns it in uppercase.
 * Returns an empty string if no valid extension is found.
 */
export function getFileExtension(fileName: string): string {
  const idx = fileName.lastIndexOf(".");
  if (idx === -1) return "";
  const ext = fileName.slice(idx + 1).toLowerCase();
  if (ext === "txt") return "PLAINTEXT";
  return ext.toUpperCase();
}

/**
 * Centralized list of image file extensions (lowercase, no leading dots)
 */
export const IMAGE_EXTENSIONS = [
  "png",
  "jpg",
  "jpeg",
  "gif",
  "webp",
  "svg",
  "bmp",
] as const;

export type ImageExtension = (typeof IMAGE_EXTENSIONS)[number];

/**
 * Checks whether a provided extension string corresponds to an image extension.
 * Accepts values with any casing and without a leading dot.
 */
export function isImageExtension(
  extension: string | null | undefined
): boolean {
  if (!extension) {
    return false;
  }
  const normalized = extension.toLowerCase();
  return (IMAGE_EXTENSIONS as readonly string[]).includes(normalized);
}

/**
 * Formats bytes to human-readable file size.
 */
export function formatBytes(
  bytes: number | undefined,
  decimals: number = 2
): string {
  if (bytes == null) return "Unknown";
  if (bytes === 0) return "0 Bytes";

  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ["Bytes", "KB", "MB", "GB", "TB"];

  let unitIndex = Math.floor(Math.log(bytes) / Math.log(k));
  if (unitIndex < 0) unitIndex = 0;
  if (unitIndex >= sizes.length) unitIndex = sizes.length - 1;
  return (
    parseFloat((bytes / Math.pow(k, unitIndex)).toFixed(dm)) +
    " " +
    sizes[unitIndex]
  );
}

/**
 * Checks if a filename represents an image file based on its extension.
 */
export function isImageFile(fileName: string | null | undefined): boolean {
  if (!fileName) return false;
  const lowerFileName = String(fileName).toLowerCase();
  return IMAGE_EXTENSIONS.some((ext) => lowerFileName.endsWith(`.${ext}`));
}

// ---------------------------------------------------------------------------
// Semantic file categories
// ---------------------------------------------------------------------------

/**
 * What a file *is*, as far as the client can tell from its name and MIME type.
 *
 * One enum for the whole app: the attachment surfaces (composer, file picker,
 * user-file modal, project context) all read their icon and their type label
 * from here, so a `.xlsx` looks like a spreadsheet everywhere or nowhere.
 */
export enum FileCategory {
  SPREADSHEET = "SPREADSHEET",
  DOCUMENT = "DOCUMENT",
  IMAGE = "IMAGE",
  PRESENTATION = "PRESENTATION",
  AUDIO = "AUDIO",
  VIDEO = "VIDEO",
  ARCHIVE = "ARCHIVE",
  OTHER = "OTHER",
}

/**
 * MIME types that name a container rather than a format. They are true of far
 * too many files to decide a category, so `fileCategory` steps over them and
 * lets the extension answer instead.
 */
const UNINFORMATIVE_MIME_TYPES: ReadonlySet<string> = new Set([
  "",
  "application/octet-stream",
  "binary/octet-stream",
  "application/binary",
  "application/x-empty",
  // Servers and browsers fall back to text/plain for csv, md and tsv alike.
  "text/plain",
]);

/**
 * Spreadsheet MIME types. The first two seed from the preview modal's own list
 * (`PreviewModal/variants/xlsxVariant.tsx`), which is the knowledge this
 * function replaced rather than duplicated.
 */
export const SPREADSHEET_MIME_TYPES = [
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/vnd.ms-excel.sheet.macroenabled.12",
  "application/vnd.ms-excel",
  "application/vnd.oasis.opendocument.spreadsheet",
  "text/csv",
  "text/tab-separated-values",
] as const;

const DOCUMENT_MIME_TYPES = [
  "application/pdf",
  "application/msword",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/vnd.oasis.opendocument.text",
  "application/rtf",
  "text/rtf",
  "text/markdown",
] as const;

const PRESENTATION_MIME_TYPES = [
  "application/vnd.ms-powerpoint",
  "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  "application/vnd.oasis.opendocument.presentation",
] as const;

const ARCHIVE_MIME_TYPES = [
  "application/zip",
  "application/x-zip-compressed",
  "application/vnd.rar",
  "application/x-rar-compressed",
  "application/x-7z-compressed",
  "application/x-tar",
  "application/gzip",
  "application/x-gzip",
] as const;

/** Exact MIME type to category. Only entries that genuinely name a format. */
const MIME_TYPE_CATEGORIES: ReadonlyMap<string, FileCategory> = new Map([
  ...SPREADSHEET_MIME_TYPES.map(
    (mime) => [mime, FileCategory.SPREADSHEET] as const
  ),
  ...DOCUMENT_MIME_TYPES.map((mime) => [mime, FileCategory.DOCUMENT] as const),
  ...PRESENTATION_MIME_TYPES.map(
    (mime) => [mime, FileCategory.PRESENTATION] as const
  ),
  ...ARCHIVE_MIME_TYPES.map((mime) => [mime, FileCategory.ARCHIVE] as const),
]);

/**
 * The `type/` half of a MIME type, for the families where the top-level type
 * alone already carries the category. Consulted only after the extension, so
 * it catches the long tail (`image/heic`, `audio/flac`) without overriding a
 * name the user can see.
 */
const MIME_FAMILY_CATEGORIES: ReadonlyMap<string, FileCategory> = new Map([
  ["image", FileCategory.IMAGE],
  ["audio", FileCategory.AUDIO],
  ["video", FileCategory.VIDEO],
  ["text", FileCategory.DOCUMENT],
]);

const SPREADSHEET_EXTENSIONS = ["xlsx", "xlsm", "xls", "csv", "tsv", "ods"];
const DOCUMENT_EXTENSIONS = [
  "pdf",
  "doc",
  "docx",
  "odt",
  "rtf",
  "txt",
  "md",
  "markdown",
];
const PRESENTATION_EXTENSIONS = ["ppt", "pptx", "odp"];
const AUDIO_EXTENSIONS = ["mp3", "wav", "m4a", "ogg", "oga", "flac", "aac"];
const VIDEO_EXTENSIONS = ["mp4", "mov", "webm", "avi", "mkv", "m4v"];
const ARCHIVE_EXTENSIONS = ["zip", "rar", "7z", "tar", "gz", "tgz", "bz2"];

/** Extension (lowercase, no dot) to category. */
const EXTENSION_CATEGORIES: ReadonlyMap<string, FileCategory> = new Map([
  ...SPREADSHEET_EXTENSIONS.map(
    (ext) => [ext, FileCategory.SPREADSHEET] as const
  ),
  ...DOCUMENT_EXTENSIONS.map((ext) => [ext, FileCategory.DOCUMENT] as const),
  // Seeded from IMAGE_EXTENSIONS so `isImageFile` and `fileCategory` cannot
  // disagree about what an image is.
  ...IMAGE_EXTENSIONS.map((ext) => [ext, FileCategory.IMAGE] as const),
  ...PRESENTATION_EXTENSIONS.map(
    (ext) => [ext, FileCategory.PRESENTATION] as const
  ),
  ...AUDIO_EXTENSIONS.map((ext) => [ext, FileCategory.AUDIO] as const),
  ...VIDEO_EXTENSIONS.map((ext) => [ext, FileCategory.VIDEO] as const),
  ...ARCHIVE_EXTENSIONS.map((ext) => [ext, FileCategory.ARCHIVE] as const),
]);

/** Lowercase extension without the dot, or `""` when the name carries none. */
function normalizeExtension(fileName: string | null | undefined): string {
  if (!fileName) return "";
  const name = String(fileName).trim();
  const lastDot = name.lastIndexOf(".");
  if (lastDot <= 0 || lastDot === name.length - 1) return "";
  return name.slice(lastDot + 1).toLowerCase();
}

/** MIME type without parameters, lowercased. */
function normalizeMimeType(mimeType: string | null | undefined): string {
  if (!mimeType) return "";
  return String(mimeType).split(";")[0]?.trim().toLowerCase() ?? "";
}

/**
 * The category of a file, from its name and MIME type.
 *
 * Precedence, in order:
 *
 * 1. **Exact MIME type**, when it names a format. `application/pdf` is a
 *    stronger signal than any extension, because the extension can lie.
 * 2. **Extension**, lowercased. This is what catches the common case of a
 *    server handing back `application/octet-stream` or `text/plain` for a
 *    `.xlsx` or a `.csv`.
 * 3. **MIME family** (`image/`, `audio/`, `video/`, `text/`), for formats too
 *    new or too rare to enumerate.
 * 4. `OTHER`.
 *
 * A file is never `DOCUMENT` merely because it has a name: an unrecognised
 * extension with an uninformative MIME type is `OTHER`.
 */
export function fileCategory(
  fileName: string | null | undefined,
  mimeType?: string | null | undefined
): FileCategory {
  const mime = normalizeMimeType(mimeType);

  if (!UNINFORMATIVE_MIME_TYPES.has(mime)) {
    const byMimeType = MIME_TYPE_CATEGORIES.get(mime);
    if (byMimeType) return byMimeType;
  }

  const byExtension = EXTENSION_CATEGORIES.get(normalizeExtension(fileName));
  if (byExtension) return byExtension;

  if (!UNINFORMATIVE_MIME_TYPES.has(mime)) {
    const family = mime.split("/")[0] ?? "";
    const byFamily = MIME_FAMILY_CATEGORIES.get(family);
    if (byFamily) return byFamily;
  }

  return FileCategory.OTHER;
}

/**
 * The category glyph. Eight distinct shapes, so category never rides on colour
 * alone — see `plans/ton/frontend/005-attachments-context.md`.
 */
export function fileCategoryIcon(
  category: FileCategory
): IconFunctionComponent {
  switch (category) {
    case FileCategory.SPREADSHEET:
      return SvgSpreadsheetFile;
    case FileCategory.DOCUMENT:
      return SvgFileText;
    case FileCategory.IMAGE:
      return SvgImage;
    case FileCategory.PRESENTATION:
      return SvgFileChartPie;
    case FileCategory.AUDIO:
      return SvgAudioFile;
    case FileCategory.VIDEO:
      return SvgVideoFile;
    case FileCategory.ARCHIVE:
      return SvgFiles;
    case FileCategory.OTHER:
      return SvgFile;
  }
}

/**
 * The `cards.file.category.*` catalog segment for a category, so every surface
 * spells the same category the same way.
 */
export const FILE_CATEGORY_LABEL_KEYS = {
  [FileCategory.SPREADSHEET]: "spreadsheet",
  [FileCategory.DOCUMENT]: "document",
  [FileCategory.IMAGE]: "image",
  [FileCategory.PRESENTATION]: "presentation",
  [FileCategory.AUDIO]: "audio",
  [FileCategory.VIDEO]: "video",
  [FileCategory.ARCHIVE]: "archive",
  [FileCategory.OTHER]: "other",
} as const satisfies Record<FileCategory, string>;

export type FileCategoryLabelKey =
  (typeof FILE_CATEGORY_LABEL_KEYS)[FileCategory];

/**
 * Typical code/config file extensions (lowercase, no leading dots)
 */
export const CODE_EXTENSIONS = [
  "ts",
  "tsx",
  "js",
  "jsx",
  "mjs",
  "cjs",
  "py",
  "pyw",
  "java",
  "kt",
  "kts",
  "c",
  "h",
  "cpp",
  "cc",
  "cxx",
  "hpp",
  "cs",
  "go",
  "rs",
  "rb",
  "php",
  "swift",
  "scala",
  "r",
  "sql",
  "sh",
  "bash",
  "zsh",
  "yaml",
  "yml",
  "json",
  "xml",
  "html",
  "htm",
  "css",
  "scss",
  "sass",
  "less",
  "lua",
  "pl",
  "vue",
  "svelte",
  "m",
  "mm",
  "md",
  "markdown",
] as const;

/**
 * Checks if a filename represents a code/config file based on its extension.
 */
export function isCodeFile(fileName: string | null | undefined): boolean {
  if (!fileName) return false;
  const lowerFileName = String(fileName).toLowerCase();
  return CODE_EXTENSIONS.some((ext) => lowerFileName.endsWith(`.${ext}`));
}

/**
 * Returns the icon component for a file based on its name/path.
 * Used for file tree and preview tab icons.
 *
 * Defers to `fileCategory` for the type, then keeps the one distinction the
 * category enum does not draw: source files get the braces glyph rather than
 * the generic document glyph, because these call sites list code.
 */
export function getFileIcon(
  fileName: string | null | undefined
): ComponentType<IconProps> {
  if (!fileName) return SvgFileText;
  if (isCodeFile(fileName)) return SvgFileBraces;
  const category = fileCategory(fileName);
  if (category === FileCategory.OTHER) return SvgFileText;
  return fileCategoryIcon(category);
}

/**
 * Checks if a collection of files contains any non-image files.
 * Useful for determining whether image previews should be compact.
 */
export function hasNonImageFiles(
  files: Array<{ name?: string | null }>
): boolean {
  return files.some((file) => !isImageFile(file.name));
}

/**
 * Merges multiple refs into a single callback ref.
 * Useful when a component needs both an internal ref and a forwarded ref.
 */
export function mergeRefs<T>(
  ...refs: (React.Ref<T> | undefined)[]
): React.RefCallback<T> {
  return (node: T | null) => {
    refs.forEach((ref) => {
      if (typeof ref === "function") {
        ref(node);
      } else if (ref) {
        (ref as React.MutableRefObject<T | null>).current = node;
      }
    });
  };
}

export function formatCost(
  cents: number,
  locale: string = DEFAULT_LOCALE
): string {
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency: "USD",
  }).format(cents / 100);
}

export function formatTokens(
  value: number,
  locale: string = DEFAULT_LOCALE
): string {
  return value.toLocaleString(locale);
}
