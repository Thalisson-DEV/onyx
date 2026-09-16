import React, { useEffect, useMemo } from "react";
import { useTranslations } from "next-intl";
import {
  PacketType,
  CustomToolPacket,
  CustomToolStart,
  CustomToolArgs,
  CustomToolDelta,
  CustomToolErrorInfo,
  SectionEnd,
} from "../../../services/streamingModels";
import { MessageRenderer, RenderType } from "../interfaces";
import { buildImgUrl } from "../../../components/files/images/utils";
import Text from "@/refresh-components/texts/Text";
import { SvgDownload, SvgExternalLink } from "@opal/icons";
import { CodeBlock } from "@/app/app/message/CodeBlock";
import hljs from "highlight.js/lib/core";
import json from "highlight.js/lib/languages/json";
import { IoBlockLabel } from "@/app/app/message/messageComponents/IoBlockLabel";
import ActivityIndicator from "@/app/app/message/messageComponents/timeline/ActivityIndicator";
import {
  ActivityStatus,
  activityStateIcon,
  type ActivityState,
} from "@/app/app/message/messageComponents/timeline/ActivityStatus";

// Lazy registration for hljs JSON language
function ensureHljsRegistered() {
  if (!hljs.listLanguages().includes("json")) {
    hljs.registerLanguage("json", json);
  }
}

// Component to render syntax-highlighted JSON
interface HighlightedJsonCodeProps {
  code: string;
}
function HighlightedJsonCode({ code }: HighlightedJsonCodeProps) {
  const highlightedHtml = useMemo(() => {
    ensureHljsRegistered();
    try {
      return hljs.highlight(code, { language: "json" }).value;
    } catch {
      return code
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
    }
  }, [code]);

  return (
    <span
      dangerouslySetInnerHTML={{ __html: highlightedHtml }}
      className="hljs"
    />
  );
}

function constructCustomToolState(
  packets: CustomToolPacket[],
  fallbackToolName: string
) {
  const toolStart = packets.find(
    (p) => p.obj.type === PacketType.CUSTOM_TOOL_START
  )?.obj as CustomToolStart | null;
  const toolDeltas = packets
    .filter((p) => p.obj.type === PacketType.CUSTOM_TOOL_DELTA)
    .map((p) => p.obj as CustomToolDelta);
  const toolEnd = packets.find(
    (p) =>
      p.obj.type === PacketType.SECTION_END || p.obj.type === PacketType.ERROR
  )?.obj as SectionEnd | null;

  const toolName =
    toolStart?.tool_name || toolDeltas[0]?.tool_name || fallbackToolName;
  const toolArgsPacket = packets.find(
    (p) => p.obj.type === PacketType.CUSTOM_TOOL_ARGS
  )?.obj as CustomToolArgs | null;
  const toolArgs = toolArgsPacket?.tool_args ?? null;
  const latestDelta = toolDeltas[toolDeltas.length - 1] || null;
  const responseType = latestDelta?.response_type || null;
  const data = latestDelta?.data;
  const fileIds = latestDelta?.file_ids || null;
  const error = latestDelta?.error || null;

  const isRunning = Boolean(toolStart && !toolEnd);
  const isComplete = Boolean(toolStart && toolEnd);

  return {
    toolName,
    toolArgs,
    responseType,
    data,
    fileIds,
    error,
    isRunning,
    isComplete,
  };
}

export const CustomToolRenderer: MessageRenderer<CustomToolPacket, {}> = ({
  packets,
  onComplete,
  renderType,
  children,
}) => {
  const t = useTranslations("chat.messages");
  const {
    toolName,
    toolArgs,
    responseType,
    data,
    fileIds,
    error,
    isRunning,
    isComplete,
  } = constructCustomToolState(packets, t("customTool.fallbackName.label"));

  useEffect(() => {
    if (isComplete) {
      onComplete();
    }
  }, [isComplete, onComplete]);

  // Custom tools are the one surface with a genuine three-state signal: the
  // delta carries an `error`, so failure is real rather than inferred.
  const activityState: ActivityState = error
    ? "failed"
    : isComplete
      ? "completed"
      : "running";

  const statusLabel = useMemo(() => {
    if (isComplete) {
      if (error) {
        return error.is_auth_error
          ? t("customTool.authFailedStatus.text", {
              toolName,
              statusCode: error.status_code,
            })
          : t("customTool.failedStatus.text", {
              toolName,
              statusCode: error.status_code,
            });
      }
      if (responseType === "image")
        return t("customTool.imagesStatus.text", { toolName });
      if (responseType === "csv")
        return t("customTool.fileStatus.text", { toolName });
      return t("customTool.completedStatus.text", { toolName });
    }
    if (isRunning) return t("customTool.runningStatus.text", { toolName });
    return null;
  }, [toolName, responseType, error, isComplete, isRunning, t]);

  const status =
    statusLabel === null ? null : (
      <ActivityStatus state={activityState} label={statusLabel} />
    );

  const icon = activityStateIcon(activityState);

  const toolArgsJson = useMemo(
    () => (toolArgs ? JSON.stringify(toolArgs, null, 2) : null),
    [toolArgs]
  );
  const dataJson = useMemo(
    () =>
      data !== undefined && data !== null && typeof data === "object"
        ? JSON.stringify(data, null, 2)
        : null,
    [data]
  );

  /**
   * What every user sees: the observable state, the failure reason, and any file
   * the tool returned. No payloads.
   */
  const humanReadable = useMemo(
    () => (
      <div className="flex flex-col gap-3">
        {isRunning &&
          !error &&
          !fileIds &&
          (data === undefined || data === null) && (
            <ActivityIndicator>
              {t("customTool.waitingIndicator.text")}
            </ActivityIndicator>
          )}

        {/* Error display */}
        {error && (
          <div className="ps-(--timeline-common-text-padding)">
            <Text text03 mainUiMuted>
              {error.message}
            </Text>
          </div>
        )}

        {/* File responses */}
        {!error && fileIds && fileIds.length > 0 && (
          <div className="text-sm text-text-03 flex flex-col gap-2">
            {fileIds.map((fid, idx) => (
              <div key={fid} className="flex items-center gap-2 flex-wrap">
                <Text text03 secondaryBody className="whitespace-nowrap">
                  {t("customTool.fileItem.label", { index: idx + 1 })}
                </Text>
                <a
                  href={buildImgUrl(fid)}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-action-selection-01 hover:underline whitespace-nowrap"
                >
                  <SvgExternalLink className="w-3 h-3" />{" "}
                  {t("customTool.openFileLink.label")}
                </a>
                <a
                  href={buildImgUrl(fid)}
                  download
                  className="inline-flex items-center gap-1 text-xs text-action-selection-01 hover:underline whitespace-nowrap"
                >
                  <SvgDownload className="w-3 h-3" />{" "}
                  {t("customTool.downloadFileLink.label")}
                </a>
              </div>
            ))}
          </div>
        )}

      </div>
    ),
    [data, fileIds, error, isRunning, t]
  );

  /**
   * The request and response payloads. Progressive disclosure: this is only
   * built for the expanded step, so a collapsed tool keeps the raw JSON out of
   * the DOM entirely rather than clipping it with CSS.
   */
  const technicalDetail = useMemo(
    () => (
      <div className="flex flex-col gap-3">
        {toolArgsJson && (
          <div>
            <IoBlockLabel label={t("customTool.requestBlock.label")} />
            <div className="prose prose-ton max-w-full">
              <CodeBlock
                className="font-secondary-mono"
                codeText={toolArgsJson}
                noPadding
              >
                <HighlightedJsonCode code={toolArgsJson} />
              </CodeBlock>
            </div>
          </div>
        )}

        {!error && data !== undefined && data !== null && (
          <div>
            <IoBlockLabel label={t("customTool.responseBlock.label")} />
            <div className="prose prose-ton max-w-full">
              {dataJson ? (
                <CodeBlock
                  className="font-secondary-mono"
                  codeText={dataJson}
                  noPadding
                >
                  <HighlightedJsonCode code={dataJson} />
                </CodeBlock>
              ) : (
                <CodeBlock
                  className="font-secondary-mono"
                  codeText={String(data)}
                  noPadding
                >
                  {String(data)}
                </CodeBlock>
              )}
            </div>
          </div>
        )}
      </div>
    ),
    [toolArgsJson, dataJson, data, error, t]
  );

  // Any failure — not just an auth failure — gets the error surface, which also
  // renders the error glyph in the step header's right slot.
  const surface = error ? { surfaceBackground: "error" as const } : {};

  // An auth failure is terminal and actionable, so it stays open.
  if (error?.is_auth_error) {
    return children([
      {
        icon,
        status,
        supportsCollapsible: false,
        noPaddingRight: true,
        ...surface,
        content: humanReadable,
      },
    ]);
  }

  // Expanded: state plus payloads.
  if (renderType === RenderType.FULL) {
    return children([
      {
        icon,
        status,
        supportsCollapsible: true,
        noPaddingRight: true,
        ...surface,
        content: (
          <div className="flex flex-col gap-3">
            {humanReadable}
            {technicalDetail}
          </div>
        ),
      },
    ]);
  }

  // Collapsed: state only. The payloads are not rendered at all.
  return children([
    {
      icon,
      status,
      supportsCollapsible: true,
      ...surface,
      content: humanReadable,
    },
  ]);
};

export default CustomToolRenderer;
