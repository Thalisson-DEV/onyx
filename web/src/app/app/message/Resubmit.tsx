import { useEffect, useMemo, useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { SvgChevronDown, SvgChevronRight } from "@opal/icons";
import { Button } from "@opal/components";
import { CopyButton } from "@opal/components";
import Text from "@/refresh-components/texts/Text";
import { getErrorIcon, getErrorTitle } from "./errorHelpers";
import {
  RateLimitDetails,
  RATE_LIMITED_ERROR_CODE,
} from "@/app/app/interfaces";
import { useFormatter, useTranslations } from "next-intl";

const COUNTDOWN_TICK_MS = 1_000;

// The countdown as data, so the component owns both the translated sentence and
// the locale formatting. `at` stays a Date here: formatting it belongs to
// next-intl's `useFormatter`, not to a bare `toLocale*String` with an implicit
// locale.
type RateLimitReset =
  | { unit: "now" }
  | { unit: "minutes" | "hours" | "days"; count: number; at: Date };

function describeRateLimitReset(
  resetMs: number,
  nowMs: number
): RateLimitReset {
  const remainingMs = resetMs - nowMs;
  if (remainingMs <= 0) return { unit: "now" };

  const minutes = Math.ceil(remainingMs / 60_000);
  const hours = Math.ceil(remainingMs / 3_600_000);
  const days = Math.ceil(remainingMs / 86_400_000);
  const at = new Date(resetMs);

  if (minutes < 60) return { unit: "minutes", count: minutes, at };
  if (hours < 48) return { unit: "hours", count: hours, at };
  return { unit: "days", count: days, at };
}

function resolveResetMs(
  resetAt?: string,
  retryAfterSeconds?: number
): number | null {
  if (resetAt) {
    const parsed = Date.parse(resetAt);
    if (!Number.isNaN(parsed)) return parsed;
  }
  if (typeof retryAfterSeconds === "number") {
    return Date.now() + retryAfterSeconds * 1_000;
  }
  return null;
}

interface RateLimitBannerProps {
  error: string;
  errorCode: string;
  title: string;
  details: RateLimitDetails;
}

function RateLimitBanner({
  error,
  errorCode,
  title,
  details,
}: RateLimitBannerProps) {
  const t = useTranslations("chat.messages");
  const format = useFormatter();
  const [nowMs, setNowMs] = useState(Date.now());
  const resetMs = useMemo(
    () => resolveResetMs(details.reset_at, details.retry_after_seconds),
    [details.reset_at, details.retry_after_seconds]
  );

  useEffect(() => {
    if (resetMs === null) return;

    setNowMs(Date.now());
    const interval = window.setInterval(
      () => setNowMs(Date.now()),
      COUNTDOWN_TICK_MS
    );
    return () => window.clearInterval(interval);
  }, [resetMs]);

  function resetLineFor(reset: RateLimitReset): string {
    if (reset.unit === "now") return t("rateLimitBanner.tryAgainNow.text");

    // A reset two or more days out reads better as a date than a clock time.
    const at =
      reset.unit === "days"
        ? format.dateTime(reset.at, { month: "short", day: "numeric" })
        : format.dateTime(reset.at, { hour: "numeric", minute: "2-digit" });

    switch (reset.unit) {
      case "minutes":
        return t("rateLimitBanner.resetsInMinutes.text", {
          count: reset.count,
          at,
        });
      case "hours":
        return t("rateLimitBanner.resetsInHours.text", {
          count: reset.count,
          at,
        });
      case "days":
        return t("rateLimitBanner.resetsInDays.text", {
          count: reset.count,
          at,
        });
    }
  }

  const resetLine =
    resetMs === null
      ? null
      : resetLineFor(describeRateLimitReset(resetMs, nowMs));
  return (
    <div className="mt-4 my-auto">
      <Alert variant="broken">
        {getErrorIcon(errorCode)}
        <AlertTitle>{title}</AlertTitle>
        <AlertDescription className="flex flex-col gap-y-1">
          <Text as="span" secondaryBody text04>
            {error || t("rateLimitBanner.defaultError.text")}
          </Text>
          {resetLine && (
            <Text as="span" secondaryBody text03>
              {resetLine}
            </Text>
          )}
        </AlertDescription>
      </Alert>
    </div>
  );
}

interface ResubmitProps {
  resubmit: () => void;
}

export const Resubmit: React.FC<ResubmitProps> = ({ resubmit }) => {
  const t = useTranslations("chat.messages");
  return (
    <div className="flex flex-col items-center justify-center gap-y-2 mt-4">
      <Text as="p" secondaryBody text03>
        {t("resubmit.responseError.text")}
      </Text>
      <Button onClick={resubmit}>{t("resubmit.regenerateButton.label")}</Button>
    </div>
  );
};

export const ErrorBanner = ({
  error,
  errorCode,
  isRetryable = true,
  details,
  stackTrace,
  resubmit,
}: {
  error: string;
  errorCode?: string;
  isRetryable?: boolean;
  details?: Record<string, any>;
  stackTrace?: string | null;
  resubmit?: () => void;
}) => {
  const t = useTranslations("chat.messages");
  const [isStackTraceExpanded, setIsStackTraceExpanded] = useState(false);

  const title = getErrorTitle(errorCode, {
    RATE_LIMIT: t("errorBanner.rateLimitExceeded.title"),
    RATE_LIMITED: t("errorBanner.usageLimitReached.title"),
    AUTH_ERROR: t("errorBanner.authError.title"),
    PERMISSION_DENIED: t("errorBanner.permissionDenied.title"),
    CONTEXT_TOO_LONG: t("errorBanner.messageTooLong.title"),
    TOOL_CALL_FAILED: t("errorBanner.toolError.title"),
    CONNECTION_ERROR: t("errorBanner.connectionError.title"),
    SERVICE_UNAVAILABLE: t("errorBanner.serviceUnavailable.title"),
    INIT_FAILED: t("errorBanner.initializationError.title"),
    VALIDATION_ERROR: t("errorBanner.validationError.title"),
    BUDGET_EXCEEDED: t("errorBanner.budgetExceeded.title"),
    MODEL_REFUSAL: t("errorBanner.modelRefusal.title"),
    CONTENT_POLICY: t("errorBanner.contentPolicy.title"),
    BAD_REQUEST: t("errorBanner.badRequest.title"),
    NOT_FOUND: t("errorBanner.resourceNotFound.title"),
    API_ERROR: t("errorBanner.apiError.title"),
    default: t("errorBanner.genericError.title"),
  });

  if (errorCode === RATE_LIMITED_ERROR_CODE) {
    return (
      <RateLimitBanner
        error={error}
        errorCode={errorCode}
        title={title}
        details={(details as RateLimitDetails) ?? {}}
      />
    );
  }

  return (
    <div className="mt-4 my-auto">
      <Alert variant="broken">
        {getErrorIcon(errorCode)}
        <AlertTitle>{title}</AlertTitle>
        <AlertDescription className="flex flex-col gap-y-1">
          <Text as="span" secondaryBody text04>
            {error}
          </Text>
          {details?.model && (
            <Text as="span" secondaryBody text03>
              {details.provider
                ? t("errorBanner.modelWithProvider.label", {
                    model: details.model,
                    provider: details.provider,
                  })
                : t("errorBanner.model.label", { model: details.model })}
            </Text>
          )}
          {details?.tool_name && (
            <Text as="span" secondaryBody text03>
              {t("errorBanner.tool.label", { tool: details.tool_name })}
            </Text>
          )}
          {/* Technical detail stays available but secondary: collapsed by
              default, and only rendered when the server actually sent one. */}
          {stackTrace && (
            <div className="mt-2 border-t border-border-subtle pt-2">
              <div className="flex flex-1 items-center justify-between">
                <Button
                  prominence="tertiary"
                  icon={isStackTraceExpanded ? SvgChevronDown : SvgChevronRight}
                  onClick={() => setIsStackTraceExpanded(!isStackTraceExpanded)}
                >
                  {t("errorBanner.stackTraceButton.label")}
                </Button>
                <CopyButton
                  prominence="tertiary"
                  getCopyText={() => stackTrace}
                />
              </div>
              {isStackTraceExpanded && (
                <pre className="mt-2 p-3 bg-background-code-01 border border-border-subtle rounded-04 text-xs text-text-03 overflow-auto max-h-48 whitespace-pre-wrap font-secondary-mono">
                  {stackTrace}
                </pre>
              )}
            </div>
          )}
        </AlertDescription>
      </Alert>
      {isRetryable && resubmit && <Resubmit resubmit={resubmit} />}
    </div>
  );
};
