import { SUBMIT_MESSAGE_TYPES } from "@/lib/extension/constants";

const LOGIN_RETURN_QUERY_ALLOWLIST = new Set<string>();
const EXTENSION_ORIGIN_PREFIXES = [
  "chrome-extension://",
  "moz-extension://",
] as const;
const EXTENSION_QUERY_ALLOWLIST = new Set([
  "user-prompt",
  "send-on-load",
  "sources",
  "documentSets",
  "tags",
  "from",
  "to",
]);

export function safeLoginReturnPath(
  pathname: string,
  search = "",
  _hash = ""
): string {
  const safePathname =
    pathname.startsWith("/") && !pathname.startsWith("//") ? pathname : "/app";
  const safeSearchParams = new URLSearchParams();
  new URLSearchParams(search).forEach((value, key) => {
    if (LOGIN_RETURN_QUERY_ALLOWLIST.has(key)) {
      safeSearchParams.append(key, value);
    }
  });
  const safeSearch = safeSearchParams.toString();
  return safeSearch ? `${safePathname}?${safeSearch}` : safePathname;
}

export function isTrustedExtensionPageChange(
  event: MessageEvent,
  expectedSource: MessageEventSource | null,
  appOrigin: string
): boolean {
  if (event.source !== expectedSource) return false;
  if (
    !EXTENSION_ORIGIN_PREFIXES.some((prefix) => event.origin.startsWith(prefix))
  ) {
    return false;
  }
  if (
    typeof event.data !== "object" ||
    event.data === null ||
    event.data.type !== SUBMIT_MESSAGE_TYPES.PAGE_CHANGE ||
    typeof event.data.href !== "string"
  ) {
    return false;
  }

  try {
    return new URL(event.data.href, appOrigin).origin === appOrigin;
  } catch {
    return false;
  }
}

export function trustedExtensionSearchParams(
  href: string,
  appOrigin: string
): string {
  const source = new URL(href, appOrigin).searchParams;
  const trusted = new URLSearchParams();
  source.forEach((value, key) => {
    if (EXTENSION_QUERY_ALLOWLIST.has(key)) trusted.append(key, value);
  });
  return trusted.toString();
}
