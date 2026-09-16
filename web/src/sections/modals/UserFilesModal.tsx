"use client";

import React, { useRef, useState, useEffect, useMemo } from "react";
import { InputTypeIn } from "@opal/components";
import { ProjectFile } from "@/lib/projects/providers";
import Text from "@/refresh-components/texts/Text";
import type { IconFunctionComponent } from "@opal/types";
import {
  FILE_CATEGORY_LABEL_KEYS,
  fileCategory,
  fileCategoryIcon,
} from "@/lib/utils";
import { AttachmentState, attachmentState } from "@/lib/projects/utils";
import { Modal } from "@opal/components";
import { useModal } from "@opal/components";
import TextSeparator from "@/refresh-components/TextSeparator";
import { IllustrationContent } from "@opal/layouts";
import {
  SvgAlertCircle,
  SvgExternalLink,
  SvgEye,
  SvgFiles,
  SvgPlusCircle,
  SvgTrash,
  SvgXCircle,
  SvgSimpleLoader,
} from "@opal/icons";
import { Hoverable } from "@opal/core";
import { AttachmentItemButton, Text as OpalText } from "@opal/components";
import { Section } from "@/layouts/general-layouts";
import useFilter from "@/hooks/useFilter";
import { Button } from "@opal/components";
import ScrollIndicatorDiv from "@/refresh-components/ScrollIndicatorDiv";
import { timeAgo } from "@opal/time";
import { useLocale, useTranslations } from "next-intl";

/**
 * The row's glyph: the state while the file is busy or failed, the category
 * otherwise. Same rule as the composer card and the file picker.
 */
function getIcon(
  file: ProjectFile,
  state: AttachmentState
): IconFunctionComponent {
  if (state === AttachmentState.FAILED) return SvgAlertCircle;
  if (state !== AttachmentState.READY) return SvgSimpleLoader;
  return fileCategoryIcon(fileCategory(file.name, file.file_type));
}

/** Translated state, or the file's category once it is ready. */
interface FileStatusLabels {
  processing: string;
  uploading: string;
  deleting: string;
  failed: string;
}

function getDescription(
  state: AttachmentState,
  categoryLabel: string,
  labels: FileStatusLabels
): string {
  switch (state) {
    case AttachmentState.PROCESSING:
      return labels.processing;
    case AttachmentState.UPLOADING:
      return labels.uploading;
    case AttachmentState.DELETING:
      return labels.deleting;
    case AttachmentState.FAILED:
      return labels.failed;
    case AttachmentState.READY:
      return categoryLabel;
  }
}

interface FileAttachmentProps {
  file: ProjectFile;
  isSelected: boolean;
  onClick?: () => void;
  onView?: () => void;
  onDelete?: () => void;
}

function FileAttachment({
  file,
  isSelected,
  onClick,
  onView,
  onDelete,
}: FileAttachmentProps) {
  const t = useTranslations("chat.modals.userFiles");
  const tCards = useTranslations("cards");
  const locale = useLocale();
  const state = attachmentState(file.status);

  const Icon = getIcon(file, state);
  const description = getDescription(
    state,
    tCards(
      `file.category.${
        FILE_CATEGORY_LABEL_KEYS[fileCategory(file.name, file.file_type)]
      }`
    ),
    {
      processing: t("fileStatus.processing.label"),
      uploading: t("fileStatus.uploading.label"),
      deleting: t("fileStatus.deleting.label"),
      failed: tCards("file.failed.description"),
    }
  );
  const rightText = file.last_accessed_at
    ? (timeAgo(file.last_accessed_at, locale) ?? "")
    : "";

  return (
    <Hoverable.Root group="user-file-row">
      <AttachmentItemButton
        prominence="primary"
        onClick={onClick}
        icon={Icon}
        title={file.name}
        description={description}
        state={isSelected ? "selected" : undefined}
        centerChildren={
          rightText ? (
            <Section alignItems="end">
              <OpalText font="secondary-body" color="text-03" maxLines={1}>
                {rightText}
              </OpalText>
            </Section>
          ) : undefined
        }
        rightChildren={
          <Hoverable.Item group="user-file-row">
            <Section flexDirection="row" gap={0} padding={1.5}>
              {onView && (
                <Button
                  icon={SvgExternalLink}
                  onClick={onView}
                  prominence="internal"
                  size="sm"
                  tooltip={t("fileRow.viewButton.ariaLabel")}
                />
              )}
              {onDelete && (
                <Button
                  icon={SvgTrash}
                  onClick={onDelete}
                  prominence="internal"
                  size="sm"
                  tooltip={t("fileRow.deleteButton.ariaLabel")}
                />
              )}
            </Section>
          </Hoverable.Item>
        }
      />
    </Hoverable.Root>
  );
}

export interface UserFilesModalProps {
  // Modal content
  title: string;
  description: string;
  recentFiles: ProjectFile[];
  handleUploadChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  selectedFileIds?: string[];

  // FileAttachment related
  onView?: (file: ProjectFile) => void;
  onDelete?: (file: ProjectFile) => void;
  onPickRecent?: (file: ProjectFile) => void;
  onUnpickRecent?: (file: ProjectFile) => void;
}

export default function UserFilesModal({
  title,
  description,
  recentFiles,
  handleUploadChange,
  selectedFileIds,

  onView,
  onDelete,
  onPickRecent,
  onUnpickRecent,
}: UserFilesModalProps) {
  const t = useTranslations("chat.modals.userFiles");
  const { isOpen, toggle } = useModal();
  const [selectedIds, setSelectedIds] = useState<Set<string>>(
    () => new Set(selectedFileIds || [])
  );
  const [showOnlySelected, setShowOnlySelected] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const searchInputRef = useRef<HTMLInputElement | null>(null);
  const triggerUploadPicker = () => fileInputRef.current?.click();

  useEffect(() => {
    if (selectedFileIds) setSelectedIds(new Set(selectedFileIds));
    else setSelectedIds(new Set());
  }, [selectedFileIds]);

  const selectedCount = selectedIds.size;

  function handleDeselectAll() {
    selectedIds.forEach((id) => {
      const file = recentFiles.find((f) => f.id === id);
      if (file) {
        onUnpickRecent?.(file);
      }
    });
    setSelectedIds(new Set());
  }

  const files = useMemo(
    () =>
      showOnlySelected
        ? recentFiles.filter((projectFile) => selectedIds.has(projectFile.id))
        : recentFiles,
    [showOnlySelected, recentFiles, selectedIds]
  );

  const { query, setQuery, filtered } = useFilter(files, (file) => file.name);

  return (
    <>
      {/* Hidden file input */}
      {handleUploadChange && (
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={handleUploadChange}
        />
      )}

      <Modal open={isOpen} onOpenChange={toggle}>
        <Modal.Content
          width="sm"
          height="lg"
          onOpenAutoFocus={(e) => {
            e.preventDefault();
            searchInputRef.current?.focus();
          }}
          preventAccidentalClose={false}
        >
          <Modal.Header icon={SvgFiles} title={title} description={description}>
            {/* Search bar section */}
            <Section flexDirection="row" gap={2}>
              <InputTypeIn
                ref={searchInputRef}
                placeholder={t("searchInput.placeholder")}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                searchIcon
                autoComplete="off"
                tabIndex={0}
                onFocus={(e) => {
                  e.target.select();
                }}
              />
              {handleUploadChange && (
                <Button
                  icon={SvgPlusCircle}
                  prominence="internal"
                  onClick={triggerUploadPicker}
                >
                  {t("addFilesButton.label")}
                </Button>
              )}
            </Section>
          </Modal.Header>

          <Modal.Body
            padding={filtered.length === 0 ? 2 : 0}
            gap={2}
            alignItems="center"
          >
            {/* File display section */}
            {filtered.length === 0 ? (
              <IllustrationContent
                title={t("emptyState.title")}
                description={t("emptyState.description")}
              />
            ) : (
              <ScrollIndicatorDiv className="p-1 gap-1 max-h-[70vh]">
                {filtered.map((projectFle) => {
                  const isSelected = selectedIds.has(projectFle.id);
                  return (
                    <FileAttachment
                      key={projectFle.id}
                      file={projectFle}
                      isSelected={isSelected}
                      onClick={
                        onPickRecent
                          ? () => {
                              if (isSelected) {
                                onUnpickRecent?.(projectFle);
                                setSelectedIds((prev) => {
                                  const next = new Set(prev);
                                  next.delete(projectFle.id);
                                  return next;
                                });
                              } else {
                                onPickRecent(projectFle);
                                setSelectedIds((prev) => {
                                  const next = new Set(prev);
                                  next.add(projectFle.id);
                                  return next;
                                });
                              }
                            }
                          : undefined
                      }
                      onView={onView ? () => onView(projectFle) : undefined}
                      onDelete={
                        onDelete ? () => onDelete(projectFle) : undefined
                      }
                    />
                  );
                })}

                {/* File count divider - only show when not searching or filtering */}
                {!query.trim() && !showOnlySelected && (
                  <TextSeparator
                    text={t("fileCount.label", { count: recentFiles.length })}
                  />
                )}
              </ScrollIndicatorDiv>
            )}
          </Modal.Body>

          <Modal.Footer>
            {/* Left side: file count and controls */}
            {onPickRecent && (
              <Section flexDirection="row" justifyContent="start" gap={2}>
                <Text as="p" text03>
                  {t("selectedCount.label", { count: selectedCount })}
                </Text>
                <Button
                  icon={SvgEye}
                  prominence="tertiary"
                  size="sm"
                  onClick={() => setShowOnlySelected(!showOnlySelected)}
                  interaction={showOnlySelected ? "hover" : "rest"}
                />
                <Button
                  disabled={selectedCount === 0}
                  icon={SvgXCircle}
                  prominence="tertiary"
                  size="sm"
                  onClick={handleDeselectAll}
                />
              </Section>
            )}

            {/* Right side: Done button */}
            <Button prominence="secondary" onClick={() => toggle(false)}>
              {t("doneButton.label")}
            </Button>
          </Modal.Footer>
        </Modal.Content>
      </Modal>
    </>
  );
}
