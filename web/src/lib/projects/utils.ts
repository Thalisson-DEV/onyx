import type { FileDescriptor } from "@/app/app/interfaces";
import { UserFileStatus, type ProjectFile } from "@/lib/projects/types";

/**
 * What an attachment is doing, reduced to the four states a user can act on.
 *
 * `UserFileStatus` has seven members and arrives in either case from the
 * server, which is why every surface used to re-derive "is this still busy?"
 * with its own string comparisons. This is that derivation, once.
 */
export enum AttachmentState {
  /** Bytes are still going up. Client-side only. */
  UPLOADING = "UPLOADING",
  /** Uploaded; the server is still indexing it. Not yet queryable. */
  PROCESSING = "PROCESSING",
  /** Indexed and usable. */
  READY = "READY",
  /** Terminal failure. Stays on screen so the user can see and remove it. */
  FAILED = "FAILED",
  /** Deletion in flight. */
  DELETING = "DELETING",
}

/**
 * The attachment state for a file status.
 *
 * Case-insensitive on purpose: the status endpoint returns lowercase members
 * while the optimistic client-side file uses the uppercase enum.
 */
export function attachmentState(
  status: UserFileStatus | string | null | undefined
): AttachmentState {
  switch (String(status ?? "").toUpperCase()) {
    case UserFileStatus.UPLOADING:
      return AttachmentState.UPLOADING;
    case UserFileStatus.PROCESSING:
      return AttachmentState.PROCESSING;
    case UserFileStatus.FAILED:
    case UserFileStatus.CANCELED:
      return AttachmentState.FAILED;
    case UserFileStatus.DELETING:
      return AttachmentState.DELETING;
    default:
      return AttachmentState.READY;
  }
}

/** True when the file failed terminally and can only be removed. */
export function isFailedAttachment(
  status: UserFileStatus | string | null | undefined
): boolean {
  return attachmentState(status) === AttachmentState.FAILED;
}

export function projectsFileToFileDescriptor(
  file: ProjectFile
): FileDescriptor {
  return {
    id: file.file_id,
    type: file.chat_file_type,
    name: file.name,
    user_file_id: file.id,
  };
}

/**
 * Descriptors for the files a message should actually carry.
 *
 * Failed attachments stay in `currentMessageFiles` so the composer can show
 * what went wrong (TON-VIS-005), but they have nothing on the server to attach
 * — so they are dropped here, at the transport boundary, rather than by hiding
 * them from the user.
 */
export function projectFilesToFileDescriptors(
  files: ProjectFile[]
): FileDescriptor[] {
  return files
    .filter((file) => !isFailedAttachment(file.status))
    .map(projectsFileToFileDescriptor);
}
