"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import type { ProjectFile } from "@/lib/projects/types";
import { AttachmentState, attachmentState } from "@/lib/projects/utils";
import {
  FILE_CATEGORY_LABEL_KEYS,
  fileCategory,
  fileCategoryIcon,
  isImageFile,
} from "@/lib/utils";
import { cn } from "@opal/utils";
import { SvgAlertCircle, SvgSimpleLoader, SvgX } from "@opal/icons";
import type { IconFunctionComponent } from "@opal/types";
import { Interactive, Hoverable } from "@opal/core";
import { AttachmentItemButton, Button } from "@opal/components";

/**
 * TON attachment identity (TON-VIS-005).
 *
 * Every attachment in the product — composer row, image tile, project context —
 * is drawn from this one file. They differ in width, and in whether they show a
 * preview; they share the icon zone, the name and metadata hierarchy, the place
 * the status appears, the removal affordance, the border and the radius.
 *
 * Category is carried by the glyph and by the type label, never by colour
 * alone. Colour is reserved for state, the only thing here that is urgent.
 */

/** Shared radius for every attachment surface. Matches `AttachmentItemButton`. */
const ATTACHMENT_RADIUS = "rounded-12";

interface AttachmentIdentity {
  state: AttachmentState;
  /** Category glyph, or the state glyph while the file is busy or failed. */
  Icon: IconFunctionComponent;
  /** Secondary line: the state while busy or failed, the category when ready. */
  description: string;
  /** Announced status, or `null` at rest so screen readers stay quiet. */
  liveStatus: string | null;
  isFailed: boolean;
  isBusy: boolean;
  /** False only while bytes are still going up: there is nothing to remove yet. */
  isRemovable: boolean;
}

/**
 * Resolves one file into the category, state and copy every attachment surface
 * needs.
 *
 * `hideBusyState` is the composer's existing `hideProcessingState`: once it
 * knows the file already fits the context window it stops showing the indexing
 * indicator. It never hides a failure — that is the one state the user must act
 * on.
 */
function useAttachmentIdentity(
  file: ProjectFile,
  hideBusyState: boolean
): AttachmentIdentity {
  const t = useTranslations("cards");

  return useMemo(() => {
    const state = attachmentState(file.status);
    const category = fileCategory(file.name, file.file_type);
    const categoryLabel = t(
      `file.category.${FILE_CATEGORY_LABEL_KEYS[category]}`
    );

    const isFailed = state === AttachmentState.FAILED;
    const isBusy =
      !isFailed &&
      !hideBusyState &&
      (state === AttachmentState.UPLOADING ||
        state === AttachmentState.PROCESSING ||
        state === AttachmentState.DELETING);

    const stateLabel: string | null = isFailed
      ? t("file.failed.description")
      : !isBusy
        ? null
        : state === AttachmentState.UPLOADING
          ? t("file.uploading.description")
          : state === AttachmentState.PROCESSING
            ? t("file.processing.description")
            : t("file.deleting.description");

    const Icon = isFailed
      ? SvgAlertCircle
      : isBusy
        ? SvgSimpleLoader
        : fileCategoryIcon(category);

    return {
      state,
      Icon,
      description: stateLabel ?? categoryLabel,
      liveStatus: stateLabel
        ? t("file.status.announcement", { name: file.name, status: stateLabel })
        : null,
      isFailed,
      isBusy,
      isRemovable: state !== AttachmentState.UPLOADING,
    };
  }, [file.name, file.file_type, file.status, hideBusyState, t]);
}

/**
 * Announces a status change without narrating every idle attachment. Empty at
 * rest, so nothing is queued until a file starts moving or fails.
 */
function AttachmentLiveStatus({ status }: { status: string | null }) {
  return (
    <span className="sr-only" role="status" aria-live="polite">
      {status ?? ""}
    </span>
  );
}

interface AttachmentRemoveButtonProps {
  fileName: string;
  onRemove: () => void;
  /** The `Hoverable.Root` group that reveals this control. */
  group: string;
}

/**
 * Quiet until relevant, and reachable everywhere.
 *
 * `Hoverable` gates its hiding behind `@media (hover: hover)`, so the control
 * stays permanently visible on touch, and the group's `:has(:focus-visible)`
 * rule reveals it for keyboard users. No shadow: the visual language reserves
 * elevation for genuinely floating layers.
 */
function AttachmentRemoveButton({
  fileName,
  onRemove,
  group,
}: AttachmentRemoveButtonProps) {
  const t = useTranslations("cards");
  const label = t("file.remove.ariaLabel", { name: fileName });

  return (
    <Hoverable.Item group={group} variant="appear-on-hover">
      {/* `sm`, not `2xs`: the old badge was a 16px square, under the 24px
          minimum target size. */}
      <Button
        icon={SvgX}
        prominence="internal"
        size="sm"
        onClick={(e) => {
          e.stopPropagation();
          onRemove();
        }}
        aria-label={label}
        tooltip={label}
      />
    </Hoverable.Item>
  );
}

interface FileThumbnailProps {
  className: string;
  label: string;
  onClick?: () => void;
  children: React.ReactNode;
}

/** Renders the thumbnail as a button only when it can be opened. */
function FileThumbnail({
  className,
  label,
  onClick,
  children,
}: FileThumbnailProps) {
  if (!onClick) return <div className={className}>{children}</div>;

  return (
    <button
      type="button"
      className={className}
      aria-label={label}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

interface ImageFileCardProps {
  file: ProjectFile;
  imageUrl: string | null;
  identity: AttachmentIdentity;
  removeFile?: (fileId: string) => void;
  onFileClick?: (file: ProjectFile) => void;
  compact?: boolean;
}

/**
 * An image keeps its preview — a thumbnail says more about a screenshot than
 * any glyph could — but borrows the rest of the attachment language: the same
 * border roles, radius, status placement and removal control.
 */
function ImageFileCard({
  file,
  imageUrl,
  identity,
  removeFile,
  onFileClick,
  compact = false,
}: ImageFileCardProps) {
  const t = useTranslations("cards");
  const [imgError, setImgError] = useState(false);

  const { Icon, isFailed, isBusy, description, liveStatus, isRemovable } =
    identity;
  const sizeClass = compact ? "h-11 w-11" : "h-20 w-20";
  const glyphSize = compact ? "h-5 w-5" : "h-8 w-8";
  const showPreview = !isBusy && !isFailed && !!imageUrl && !imgError;
  const canOpen = !!onFileClick && !isBusy && !isFailed;
  const canRemove = !!removeFile && isRemovable;

  return (
    <Hoverable.Root group="attachmentTile" width="fit">
      <div className="relative">
        <FileThumbnail
          className={cn(
            sizeClass,
            ATTACHMENT_RADIUS,
            "border",
            isFailed ? "border-border-error" : "border-border-01",
            isBusy && "bg-background-neutral-02",
            isFailed && "bg-status-error-00",
            canOpen && "cursor-pointer hover:opacity-90"
          )}
          label={
            liveStatus ??
            (isFailed
              ? t("file.status.announcement", {
                  name: file.name,
                  status: description,
                })
              : file.name)
          }
          onClick={canOpen ? () => onFileClick(file) : undefined}
        >
          {showPreview ? (
            <img
              src={imageUrl}
              alt={file.name}
              className={cn("h-full w-full object-cover", ATTACHMENT_RADIUS)}
              onError={() => setImgError(true)}
            />
          ) : (
            <div className="h-full w-full flex items-center justify-center">
              <Icon
                className={cn(glyphSize, isFailed && "stroke-status-error-05")}
              />
            </div>
          )}
        </FileThumbnail>

        {canRemove && (
          <div className="absolute end-0.5 top-0.5 z-10">
            <AttachmentRemoveButton
              fileName={file.name}
              group="attachmentTile"
              onRemove={() => removeFile(file.id)}
            />
          </div>
        )}
        <AttachmentLiveStatus status={liveStatus} />
      </div>
    </Hoverable.Root>
  );
}

export interface FileCardProps {
  file: ProjectFile;
  removeFile?: (fileId: string) => void;
  hideProcessingState?: boolean;
  onFileClick?: (file: ProjectFile) => void;
  compactImages?: boolean;
}
export function FileCard({
  file,
  removeFile,
  hideProcessingState = false,
  onFileClick,
  compactImages = false,
}: FileCardProps) {
  const identity = useAttachmentIdentity(file, hideProcessingState);

  const isImage = useMemo(() => isImageFile(file.name), [file.name]);

  const imageUrl = useMemo(() => {
    if (isImage && file.file_id) {
      return `/api/chat/file/${file.file_id}`;
    }
    return null;
  }, [isImage, file.file_id]);

  // Images keep the preview layout even while processing.
  if (isImage) {
    return (
      <ImageFileCard
        file={file}
        imageUrl={imageUrl}
        identity={identity}
        removeFile={removeFile}
        onFileClick={onFileClick}
        compact={compactImages}
      />
    );
  }

  const { Icon, description, isFailed, liveStatus, isRemovable } = identity;
  const canRemove = !!removeFile && isRemovable;

  const row = (
    <div
      className={cn(
        "min-w-0 max-w-48",
        // Failure recolours the edge rather than adding one, so the geometry
        // does not move between states. The error surface comes with it: on the
        // dark canvas the error border only clears 3:1 against it.
        isFailed &&
          cn(ATTACHMENT_RADIUS, "border border-border-error bg-status-error-00")
      )}
    >
      <Interactive.Container border={!isFailed} size="fit" width="full">
        <AttachmentItemButton
          presentational
          icon={Icon}
          title={file.name}
          description={description}
          rightChildren={
            canRemove ? (
              <AttachmentRemoveButton
                fileName={file.name}
                group="attachmentRow"
                onRemove={() => removeFile(file.id)}
              />
            ) : undefined
          }
        />
      </Interactive.Container>
      <AttachmentLiveStatus status={liveStatus} />
    </div>
  );

  // Only a card that can be removed needs the hover group around it.
  if (!canRemove) return row;

  return (
    <Hoverable.Root group="attachmentRow" width="fit">
      {row}
    </Hoverable.Root>
  );
}
