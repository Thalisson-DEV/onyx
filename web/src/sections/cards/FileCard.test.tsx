/**
 * TON-VIS-005 — the attachment card.
 *
 * What matters here is what the user can see and reach: which category the file
 * is, which state it is in, and whether the failure can be removed. The visual
 * tokens are asserted at source level in `attachmentVisualContract.test.ts`.
 */
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
// The app supplies this in `layout.tsx`; the card only needs it because its
// remove control carries a tooltip.
import { TooltipProvider } from "@radix-ui/react-tooltip";
import englishMessages from "@/i18n/messages/en.json";
import { ChatFileType } from "@/app/app/interfaces";
import { UserFileStatus, type ProjectFile } from "@/lib/projects/types";
import { FileCard } from "@/sections/cards/FileCard";

function projectFile(overrides: Partial<ProjectFile> = {}): ProjectFile {
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

function renderCard(props: Parameters<typeof FileCard>[0]) {
  return render(
    <NextIntlClientProvider locale="en" messages={englishMessages}>
      <TooltipProvider>
        <FileCard {...props} />
      </TooltipProvider>
    </NextIntlClientProvider>
  );
}

describe("category identity", () => {
  test("names the category instead of echoing the raw extension", () => {
    renderCard({ file: projectFile() });

    expect(screen.getByText("Spreadsheet")).toBeInTheDocument();
    expect(screen.queryByText("XLSX")).not.toBeInTheDocument();
  });

  test("reads the category from a generic MIME type via the extension", () => {
    renderCard({
      file: projectFile({
        name: "diretoria.pptx",
        file_type: "application/octet-stream",
      }),
    });

    expect(screen.getByText("Presentation")).toBeInTheDocument();
  });

  test("does not call an unknown format a document", () => {
    renderCard({
      file: projectFile({
        name: "firmware.xyz",
        file_type: "application/octet-stream",
      }),
    });

    expect(screen.getByText("File")).toBeInTheDocument();
    expect(screen.queryByText("Document")).not.toBeInTheDocument();
  });
});

describe("states", () => {
  test("shows the uploading state", () => {
    renderCard({ file: projectFile({ status: UserFileStatus.UPLOADING }) });

    expect(screen.getByText("Uploading...")).toBeInTheDocument();
  });

  test("shows the processing state", () => {
    renderCard({ file: projectFile({ status: UserFileStatus.PROCESSING }) });

    expect(screen.getByText("Processing...")).toBeInTheDocument();
  });

  test("shows the category once ready", () => {
    renderCard({ file: projectFile({ status: UserFileStatus.COMPLETED }) });

    expect(screen.getByText("Spreadsheet")).toBeInTheDocument();
  });

  test("announces a non-resting state without narrating a ready one", () => {
    const { unmount } = renderCard({
      file: projectFile({ status: UserFileStatus.PROCESSING }),
    });
    expect(screen.getByRole("status")).toHaveTextContent(
      "resultado.xlsx: Processing..."
    );
    unmount();

    renderCard({ file: projectFile({ status: UserFileStatus.COMPLETED }) });
    expect(screen.getByRole("status")).toHaveTextContent("");
  });
});

describe("a failed attachment", () => {
  test("stays visible and says it failed", () => {
    renderCard({ file: projectFile({ status: UserFileStatus.FAILED }) });

    expect(screen.getByTitle("resultado.xlsx")).toBeInTheDocument();
    expect(screen.getByText("Upload failed")).toBeInTheDocument();
  });

  test("does not read as uploading or processing", () => {
    renderCard({ file: projectFile({ status: UserFileStatus.FAILED }) });

    expect(screen.queryByText("Uploading...")).not.toBeInTheDocument();
    expect(screen.queryByText("Processing...")).not.toBeInTheDocument();
  });

  test("announces the failure", () => {
    renderCard({ file: projectFile({ status: UserFileStatus.FAILED }) });

    expect(screen.getByRole("status")).toHaveTextContent(
      "resultado.xlsx: Upload failed"
    );
  });

  test("can be removed", async () => {
    const removeFile = jest.fn();
    renderCard({
      file: projectFile({ status: UserFileStatus.FAILED }),
      removeFile,
    });

    const remove = screen.getByRole("button", {
      name: "Remove resultado.xlsx",
    });
    remove.click();

    expect(removeFile).toHaveBeenCalledWith("file-1");
  });

  test("reports failure for a lowercase status from the poller", () => {
    renderCard({ file: projectFile({ status: "failed" as UserFileStatus }) });

    expect(screen.getByText("Upload failed")).toBeInTheDocument();
  });

  test("still shows the failure when the composer hides the processing state", () => {
    renderCard({
      file: projectFile({ status: UserFileStatus.FAILED }),
      hideProcessingState: true,
    });

    expect(screen.getByText("Upload failed")).toBeInTheDocument();
  });
});

describe("removal affordance", () => {
  test("has an accessible name that includes the file", () => {
    renderCard({ file: projectFile(), removeFile: jest.fn() });

    expect(
      screen.getByRole("button", { name: "Remove resultado.xlsx" })
    ).toBeInTheDocument();
  });

  test("is absent while bytes are still going up", () => {
    renderCard({
      file: projectFile({ status: UserFileStatus.UPLOADING }),
      removeFile: jest.fn(),
    });

    expect(screen.queryByRole("button", { name: /^Remove/ })).toBeNull();
  });

  test("is absent when the surface does not allow removal", () => {
    renderCard({ file: projectFile() });

    expect(screen.queryByRole("button", { name: /^Remove/ })).toBeNull();
  });
});

describe("long file names", () => {
  const LONG_NAME =
    "Resultado consolidado Vale Norte Construtora — obra 4471 — competência 2026-01.xlsx";

  test("truncation keeps the full name available", () => {
    renderCard({ file: projectFile({ name: LONG_NAME }) });

    // Content caps the title at one line and exposes the whole string as its
    // native tooltip, so the accessible text is never the truncated form.
    expect(screen.getByTitle(LONG_NAME)).toBeInTheDocument();
  });

  test("the remove control still names the whole file", () => {
    renderCard({
      file: projectFile({ name: LONG_NAME }),
      removeFile: jest.fn(),
    });

    expect(
      screen.getByRole("button", { name: `Remove ${LONG_NAME}` })
    ).toBeInTheDocument();
  });
});

describe("images", () => {
  const image = projectFile({ name: "captura.png", file_type: "image/png" });

  test("keep their preview", () => {
    renderCard({ file: image });

    expect(screen.getByAltText("captura.png")).toBeInTheDocument();
  });

  test("share the removal affordance", () => {
    const removeFile = jest.fn();
    renderCard({ file: image, removeFile });

    screen.getByRole("button", { name: "Remove captura.png" }).click();

    expect(removeFile).toHaveBeenCalledWith("file-1");
  });

  test("drop the preview for the failure glyph and stay removable", () => {
    renderCard({
      file: { ...image, status: UserFileStatus.FAILED },
      removeFile: jest.fn(),
    });

    expect(screen.queryByAltText("captura.png")).toBeNull();
    expect(screen.getByRole("status")).toHaveTextContent(
      "captura.png: Upload failed"
    );
    expect(
      screen.getByRole("button", { name: "Remove captura.png" })
    ).toBeInTheDocument();
  });
});
