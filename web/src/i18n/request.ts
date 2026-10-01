import { getRequestConfig } from "next-intl/server";

import { DEFAULT_LOCALE, runtimeLocale, type Locale } from "@/i18n/config";
import { TON_LOCALE } from "@/lib/ton/product-surface";
import englishMessages from "@/i18n/messages/en.json";

type MessageTree = { [key: string]: string | MessageTree };

// Overlay a target-locale catalog on top of the English one. Keys the target
// catalog does not have yet (the lag window before the translation pipeline
// runs) render in English instead of as raw key paths.
function withEnglishFallback(base: MessageTree, overlay: MessageTree) {
  const merged = { ...base };
  for (const [key, value] of Object.entries(overlay)) {
    const baseValue = merged[key];
    merged[key] =
      typeof value === "object" &&
      value !== null &&
      typeof baseValue === "object" &&
      baseValue !== null
        ? withEnglishFallback(baseValue, value)
        : value;
  }
  return merged;
}

// SAFETY: catalog files are JSON objects whose values are strings or nested
// objects of the same shape; the i18n catalog test enforces this.
const english = englishMessages as MessageTree;

export default getRequestConfig(async () => {
  // TON is Brazilian Portuguese only; the stored preference is ignored.
  const locale: Locale = TON_LOCALE;

  const messages =
    locale === DEFAULT_LOCALE
      ? english
      : withEnglishFallback(
          english,
          // SAFETY: same catalog shape as en.json, enforced by the i18n catalog test.
          (await import(`@/i18n/messages/${locale}.json`))
            .default as MessageTree
        );
  return { locale: runtimeLocale(locale), messages };
});
