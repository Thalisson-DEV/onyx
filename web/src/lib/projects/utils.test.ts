/**
 * TON-VIS-005 — attachment state model and the send boundary.
 *
 * A failed attachment now stays in `currentMessageFiles` so the composer can
 * show it. These tests hold the two invariants that make that safe: a failure
 * never reads as still-working, and it never rides along on a message.
 */
import { ChatFileType } from "@/app/app/interfaces";
import { UserFileStatus, type ProjectFile } from "@/lib/projects/types";
import {
  AttachmentState,
  attachmentState,
  isFailedAttachment,
  projectFilesToFileDescriptors,
  projectsFileToFileDescriptor,
} from "@/lib/projects/utils";

function file(overrides: Partial<ProjectFile> = {}): ProjectFile {
  return {
    id: "file-1",
    name: "resultado.xlsx",
    project_id: null,
    user_id: null,
    file_id: "server-1",
    created_at: "2026-01-01T00:00:00.000Z",
    status: UserFileStatus.COMPLETED,
    file_type:
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    last_accessed_at: "2026-01-01T00:00:00.000Z",
    chat_file_type: ChatFileType.DOCUMENT,
    token_count: 10,
    chunk_count: 1,
    ...overrides,
  };
}

describe("attachmentState", () => {
  test("preserves the uploading state", () => {
    expect(attachmentState(UserFileStatus.UPLOADING)).toBe(
      AttachmentState.UPLOADING
    );
  });

  test("preserves the processing/indexing state", () => {
    expect(attachmentState(UserFileStatus.PROCESSING)).toBe(
      AttachmentState.PROCESSING
    );
  });

  test("preserves the ready state", () => {
    expect(attachmentState(UserFileStatus.COMPLETED)).toBe(
      AttachmentState.READY
    );
    // A skipped file is indexed as far as the user is concerned.
    expect(attachmentState(UserFileStatus.SKIPPED)).toBe(AttachmentState.READY);
  });

  test("reports failure for both terminal statuses", () => {
    expect(attachmentState(UserFileStatus.FAILED)).toBe(AttachmentState.FAILED);
    expect(attachmentState(UserFileStatus.CANCELED)).toBe(
      AttachmentState.FAILED
    );
  });

  test("keeps deleting distinct from failure", () => {
    expect(attachmentState(UserFileStatus.DELETING)).toBe(
      AttachmentState.DELETING
    );
  });

  test("reads the lowercase statuses the status endpoint returns", () => {
    // /api/user/projects/file/statuses answers in lowercase; the optimistic
    // client-side file uses the uppercase enum. Both must resolve the same.
    expect(attachmentState("failed")).toBe(AttachmentState.FAILED);
    expect(attachmentState("uploading")).toBe(AttachmentState.UPLOADING);
    expect(attachmentState("processing")).toBe(AttachmentState.PROCESSING);
    expect(attachmentState("completed")).toBe(AttachmentState.READY);
  });

  test("treats an unknown or absent status as ready, not as failed", () => {
    expect(attachmentState(undefined)).toBe(AttachmentState.READY);
    expect(attachmentState(null)).toBe(AttachmentState.READY);
    expect(attachmentState("something-new")).toBe(AttachmentState.READY);
  });
});

describe("a failed attachment", () => {
  test("does not masquerade as uploading", () => {
    expect(attachmentState(UserFileStatus.FAILED)).not.toBe(
      AttachmentState.UPLOADING
    );
  });

  test("does not masquerade as processing/indexing", () => {
    expect(attachmentState(UserFileStatus.FAILED)).not.toBe(
      AttachmentState.PROCESSING
    );
  });

  test("is reported by isFailedAttachment for both terminal statuses", () => {
    expect(isFailedAttachment(UserFileStatus.FAILED)).toBe(true);
    expect(isFailedAttachment("failed")).toBe(true);
    expect(isFailedAttachment(UserFileStatus.CANCELED)).toBe(true);
    expect(isFailedAttachment(UserFileStatus.PROCESSING)).toBe(false);
    expect(isFailedAttachment(UserFileStatus.UPLOADING)).toBe(false);
    expect(isFailedAttachment(UserFileStatus.COMPLETED)).toBe(false);
  });
});

describe("the send gate that consumes these states", () => {
  // AppInputBar blocks send on UPLOADING and on PROCESSING. Since a failure is
  // neither, keeping a failed file on screen cannot wedge the composer.
  const blocksSend = (status: UserFileStatus | string) =>
    attachmentState(status) === AttachmentState.UPLOADING ||
    attachmentState(status) === AttachmentState.PROCESSING;

  test("blocks while the file is uploading or indexing", () => {
    expect(blocksSend(UserFileStatus.UPLOADING)).toBe(true);
    expect(blocksSend(UserFileStatus.PROCESSING)).toBe(true);
  });

  test("does not block on a failed file", () => {
    expect(blocksSend(UserFileStatus.FAILED)).toBe(false);
    expect(blocksSend("failed")).toBe(false);
    expect(blocksSend(UserFileStatus.CANCELED)).toBe(false);
  });

  test("does not block on a ready file", () => {
    expect(blocksSend(UserFileStatus.COMPLETED)).toBe(false);
  });
});

describe("projectFilesToFileDescriptors", () => {
  test("maps a ready file unchanged", () => {
    const ready = file();
    expect(projectFilesToFileDescriptors([ready])).toEqual([
      projectsFileToFileDescriptor(ready),
    ]);
  });

  test("drops a failed file, so a visible failure is never attached", () => {
    const ready = file({ id: "ok", file_id: "ok-server" });
    const failed = file({
      id: "bad",
      file_id: "bad-server",
      status: UserFileStatus.FAILED,
    });

    const descriptors = projectFilesToFileDescriptors([ready, failed]);

    expect(descriptors.map((d) => d.user_file_id)).toEqual(["ok"]);
  });

  test("drops a lowercase failed status too", () => {
    const failed = file({ status: "failed" as UserFileStatus });
    expect(projectFilesToFileDescriptors([failed])).toEqual([]);
  });

  test("keeps an indexing file, which the send gate already waits for", () => {
    const indexing = file({ status: UserFileStatus.PROCESSING });
    expect(projectFilesToFileDescriptors([indexing])).toHaveLength(1);
  });
});
