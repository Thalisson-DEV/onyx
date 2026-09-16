import React, { PropsWithChildren } from "react";
import { act, renderHook } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import englishMessages from "@/i18n/messages/en.json";
import { ProjectsProvider, useProjectsContext } from "@/lib/projects/providers";
import { UserFileStatus, type ProjectFile } from "@/lib/projects/types";
import {
  AttachmentState,
  attachmentState,
  projectFilesToFileDescriptors,
} from "@/lib/projects/utils";

const mockUploadFiles = jest.fn();
const mockGetRecentFiles = jest.fn();
const mockGetUserFileStatuses = jest.fn();
const mockToastWarning = jest.fn();

jest.mock("next/navigation", () => ({
  useSearchParams: () => ({
    get: () => null,
  }),
}));

jest.mock("@/lib/position/hooks", () => ({
  useAppPosition: () => ({ openNewSession: jest.fn() }),
}));

jest.mock("@/lib/projects/hooks", () => ({
  useProjects: () => ({
    projects: [],
    refreshProjects: jest.fn().mockResolvedValue([]),
  }),
}));

jest.mock("@/lib/settings/hooks", () => ({
  useSettings: () => ({
    user_file_max_upload_size_mb: 1,
    enterprise: null,
    appName: "Onyx",
    vectorDbEnabled: true,
    isLoading: false,
    error: undefined,
  }),
}));

jest.mock("@opal/layouts/toast/store", () => ({
  toast: {
    warning: (...args: unknown[]) => mockToastWarning(...args),
    error: jest.fn(),
    success: jest.fn(),
  },
}));

jest.mock("@/lib/projects/svc", () => {
  const actual = jest.requireActual("@/lib/projects/svc");
  return {
    ...actual,
    fetchProjects: jest.fn().mockResolvedValue([]),
    createProject: jest.fn(),
    uploadFiles: (...args: unknown[]) => mockUploadFiles(...args),
    getRecentFiles: (...args: unknown[]) => mockGetRecentFiles(...args),
    getFilesInProject: jest.fn().mockResolvedValue([]),
    getProject: jest.fn(),
    getProjectInstructions: jest.fn(),
    upsertProjectInstructions: jest.fn(),
    getProjectDetails: jest.fn(),
    renameProject: jest.fn(),
    deleteProject: jest.fn(),
    deleteUserFile: jest.fn(),
    getUserFileStatuses: (...args: unknown[]) =>
      mockGetUserFileStatuses(...args),
    unlinkFileFromProject: jest.fn(),
    linkFileToProject: jest.fn(),
  };
});

const wrapper = ({ children }: PropsWithChildren) => (
  <NextIntlClientProvider locale="en" messages={englishMessages}>
    <ProjectsProvider>{children}</ProjectsProvider>
  </NextIntlClientProvider>
);

describe("ProjectsContext beginUpload size precheck", () => {
  beforeEach(() => {
    mockUploadFiles.mockReset();
    mockGetRecentFiles.mockReset();
    mockToastWarning.mockReset();

    mockGetUserFileStatuses.mockReset();
    mockUploadFiles.mockResolvedValue({
      user_files: [],
      rejected_files: [],
    });
    mockGetRecentFiles.mockResolvedValue([]);
    mockGetUserFileStatuses.mockResolvedValue([]);
  });

  it("only sends valid files to the upload API when oversized files are present", async () => {
    const { result } = renderHook(() => useProjectsContext(), { wrapper });

    const valid = new File(["small"], "small.txt", { type: "text/plain" });
    const oversized = new File([new Uint8Array(2 * 1024 * 1024)], "big.txt", {
      type: "text/plain",
    });

    let optimisticFiles: ProjectFile[] = [];
    await act(async () => {
      optimisticFiles = await result.current.beginUpload(
        [valid, oversized],
        null
      );
    });

    expect(mockUploadFiles).toHaveBeenCalledTimes(1);
    const [uploadedFiles] = mockUploadFiles.mock.calls[0];
    expect((uploadedFiles as File[]).map((f) => f.name)).toEqual(["small.txt"]);
    expect(optimisticFiles.map((f) => f.name)).toEqual(["small.txt"]);
    expect(mockToastWarning).toHaveBeenCalledTimes(1);
  });

  it("uploads all files when none are oversized", async () => {
    const { result } = renderHook(() => useProjectsContext(), { wrapper });

    const first = new File(["small"], "first.txt", { type: "text/plain" });
    const second = new File(["small"], "second.txt", { type: "text/plain" });

    let optimisticFiles: ProjectFile[] = [];
    await act(async () => {
      optimisticFiles = await result.current.beginUpload([first, second], null);
    });

    expect(mockUploadFiles).toHaveBeenCalledTimes(1);
    const [uploadedFiles] = mockUploadFiles.mock.calls[0];
    expect((uploadedFiles as File[]).map((f) => f.name)).toEqual([
      "first.txt",
      "second.txt",
    ]);
    expect(mockToastWarning).not.toHaveBeenCalled();
    expect(optimisticFiles.map((f) => f.name)).toEqual([
      "first.txt",
      "second.txt",
    ]);
  });

  it("does not call upload API when all files are oversized", async () => {
    const { result } = renderHook(() => useProjectsContext(), { wrapper });

    const oversized = new File(
      [new Uint8Array(2 * 1024 * 1024)],
      "too-big.txt",
      { type: "text/plain" }
    );
    const onSuccess = jest.fn();
    const onFailure = jest.fn();

    let optimisticFiles: ProjectFile[] = [];
    await act(async () => {
      optimisticFiles = await result.current.beginUpload(
        [oversized],
        null,
        onSuccess,
        onFailure
      );
    });

    expect(mockUploadFiles).not.toHaveBeenCalled();
    expect(optimisticFiles).toEqual([]);
    expect(mockToastWarning).toHaveBeenCalledTimes(1);
    expect(onSuccess).not.toHaveBeenCalled();
    expect(onFailure).toHaveBeenCalledWith([]);
  });

  it("reports the optimistic temp id via onFailure when the server rejects a file", async () => {
    const { result } = renderHook(() => useProjectsContext(), { wrapper });

    const rejected = new File(["small"], "too-many-tokens.txt", {
      type: "text/plain",
    });
    const onSuccess = jest.fn();
    const onFailure = jest.fn();

    mockUploadFiles.mockResolvedValue({
      user_files: [],
      rejected_files: [
        { file_name: "too-many-tokens.txt", reason: "Exceeds token limit" },
      ],
    });

    let optimisticFiles: ProjectFile[] = [];
    await act(async () => {
      optimisticFiles = await result.current.beginUpload(
        [rejected],
        null,
        onSuccess,
        onFailure
      );
    });

    const tempId = optimisticFiles[0]?.temp_id;
    expect(tempId).toBeTruthy();
    expect(mockUploadFiles).toHaveBeenCalledTimes(1);
    expect(mockToastWarning).toHaveBeenCalledTimes(1);
    // AgentEditorPage relies on this callback firing with the failed temp id
    // to strip the file from user_file_ids; otherwise the submit button stays
    // disabled forever waiting on a phantom "uploading" file.
    expect(onFailure).toHaveBeenCalledWith([tempId]);
  });
});

/**
 * TON-VIS-005 — a failed attachment must not disappear.
 *
 * The status poller used to drop `failed` files from `currentMessageFiles`, so
 * the composer showed a toast and an empty attachment strip: the user could not
 * tell which file had failed, or remove it. These tests pin the new behaviour
 * and the two invariants that keep it safe.
 */
describe("ProjectsContext failed-file visibility", () => {
  const SERVER_ID = "server-file-1";

  const serverFile = (status: string): ProjectFile =>
    ({
      id: SERVER_ID,
      file_id: SERVER_ID,
      name: "resultado.xlsx",
      project_id: null,
      user_id: null,
      created_at: "2026-01-01T00:00:00.000Z",
      status,
      file_type:
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      last_accessed_at: "2026-01-01T00:00:00.000Z",
      chat_file_type: "document",
      token_count: null,
      chunk_count: null,
    }) as unknown as ProjectFile;

  beforeEach(() => {
    mockUploadFiles.mockReset();
    mockGetRecentFiles.mockReset();
    mockGetUserFileStatuses.mockReset();
    mockToastWarning.mockReset();
    mockGetRecentFiles.mockResolvedValue([]);
  });

  /**
   * Uploads one file, seeds it into `currentMessageFiles` the way the chat
   * controller does, then lets the poller report `pollStatus` for it.
   */
  async function uploadThenPoll(pollStatus: string) {
    const { result } = renderHook(() => useProjectsContext(), { wrapper });

    mockGetUserFileStatuses.mockResolvedValue([serverFile(pollStatus)]);
    mockUploadFiles.mockResolvedValue({
      user_files: [serverFile("PROCESSING")],
      rejected_files: [],
    });

    act(() => {
      result.current.setCurrentMessageFiles([serverFile("PROCESSING")]);
    });

    let optimistic: ProjectFile[] = [];
    await act(async () => {
      optimistic = await result.current.beginUpload(
        [new File(["x"], "resultado.xlsx")],
        null
      );
    });
    // Let the immediate poll kick and its state updates land.
    await act(async () => {
      await Promise.resolve();
    });

    return { result, optimistic };
  }

  it("keeps a failed file in currentMessageFiles with its failed status", async () => {
    const { result } = await uploadThenPoll("failed");

    expect(result.current.currentMessageFiles).toHaveLength(1);
    expect(result.current.currentMessageFiles[0]!.id).toBe(SERVER_ID);
    expect(String(result.current.currentMessageFiles[0]!.status)).toBe(
      "failed"
    );
  });

  it("does not leave a failed file looking like it is still uploading or indexing", async () => {
    const { result } = await uploadThenPoll("failed");

    const status = String(result.current.currentMessageFiles[0]!.status);
    expect(attachmentState(status)).toBe(AttachmentState.FAILED);
    expect(attachmentState(status)).not.toBe(AttachmentState.UPLOADING);
    expect(attachmentState(status)).not.toBe(AttachmentState.PROCESSING);
  });

  it("does not block send: the failure is neither uploading nor indexing", async () => {
    const { result } = await uploadThenPoll("failed");
    const files = result.current.currentMessageFiles;

    // Guard against passing because the file vanished, which is the very
    // behaviour this slice removed.
    expect(files).toHaveLength(1);
    // The exact predicates AppInputBar gates the send button on.
    expect(files.some((f) => f.status === UserFileStatus.UPLOADING)).toBe(
      false
    );
    expect(files.some((f) => f.status === UserFileStatus.PROCESSING)).toBe(
      false
    );
  });

  it("never attaches the visible failure to a message", async () => {
    const { result } = await uploadThenPoll("failed");

    expect(result.current.currentMessageFiles).toHaveLength(1);
    expect(
      projectFilesToFileDescriptors(result.current.currentMessageFiles)
    ).toEqual([]);
  });

  it("reports the failure so the composer can surface it", async () => {
    const { result } = await uploadThenPoll("failed");

    expect(result.current.lastFailedFiles.map((f) => f.id)).toEqual([
      SERVER_ID,
    ]);
  });

  it("lets the user remove the failed file", async () => {
    const { result } = await uploadThenPoll("failed");

    expect(result.current.currentMessageFiles).toHaveLength(1);
    // Exactly what AppInputBar's handleRemoveMessageFile does.
    act(() => {
      result.current.setCurrentMessageFiles((prev) =>
        prev.filter((f) => f.id !== SERVER_ID)
      );
    });

    expect(result.current.currentMessageFiles).toEqual([]);
  });

  it("still merges a non-failed status the same way", async () => {
    const { result } = await uploadThenPoll("completed");

    expect(result.current.currentMessageFiles).toHaveLength(1);
    expect(String(result.current.currentMessageFiles[0]!.status)).toBe(
      "completed"
    );
  });

  it("preserves the temp_<uuid> contract and the optimistic insert", async () => {
    const { optimistic } = await uploadThenPoll("failed");

    // AgentEditorPage is a second consumer of this prefix.
    expect(optimistic).toHaveLength(1);
    expect(optimistic[0]!.temp_id).toMatch(/^temp_/);
    expect(optimistic[0]!.id).toBe(optimistic[0]!.temp_id);
    expect(String(optimistic[0]!.status)).toBe(UserFileStatus.UPLOADING);
  });

  it("still polls the uploaded file id", async () => {
    await uploadThenPoll("failed");

    expect(mockGetUserFileStatuses).toHaveBeenCalled();
    expect(mockGetUserFileStatuses.mock.calls[0]![0]).toEqual([SERVER_ID]);
  });
});
