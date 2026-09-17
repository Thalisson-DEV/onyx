import { fireEvent, render, screen } from "@testing-library/react";

import { ChatFileType } from "@/app/app/interfaces";
import { UserFileStatus } from "@/lib/projects/types";
import Suggestions from "@/sections/Suggestions";

const translations: Record<string, string> = {
  contextLabel: "Start with",
  "analyzeFile.label": "Analyze a file",
  "analyzeFile.prompt": "Analyze the attached file.",
  "reviewContract.label": "Review a contract",
  "reviewContract.prompt": "Review the supplied contract.",
  "investigateDifference.label": "Investigate a difference",
  "investigateDifference.prompt": "Investigate the supplied difference.",
  "analyzeResult.label": "Analyze a result",
  "analyzeResult.prompt": "Analyze the supplied result.",
};

jest.mock("next-intl", () => ({
  useTranslations: () => (key: string) => translations[key] ?? key,
}));

jest.mock("@/lib/agents/hooks", () => ({
  useActiveAgent: () => ({ starter_messages: [] }),
}));

describe("Suggestions", () => {
  test("renders default actions in deterministic order", () => {
    render(<Suggestions onSubmit={jest.fn()} isDefaultAgent />);

    expect(screen.getByText("Start with")).toBeInTheDocument();
    expect(
      screen.getAllByRole("button").map((button) => button.textContent),
    ).toEqual([
      "Analyze a file",
      "Review a contract",
      "Investigate a difference",
      "Analyze a result",
    ]);
  });

  test("sends the selected prompt through the existing submit contract", () => {
    const onSubmit = jest.fn();
    render(<Suggestions onSubmit={onSubmit} isDefaultAgent />);

    fireEvent.click(screen.getByRole("button", { name: "Review a contract" }));

    expect(onSubmit).toHaveBeenCalledWith({
      message: "Review the supplied contract.",
      currentMessageFiles: [],
      deepResearch: false,
    });
  });

  test("keeps attached files when an action starts the conversation", () => {
    const onSubmit = jest.fn();
    const currentMessageFiles = [
      {
        id: "file-1",
        file_id: "file-1",
        name: "result.xlsx",
        project_id: null,
        user_id: "user-1",
        created_at: "2026-09-16T12:00:00Z",
        status: UserFileStatus.COMPLETED,
        file_type: "application/vnd.ms-excel",
        last_accessed_at: "2026-09-16T12:00:00Z",
        chat_file_type: ChatFileType.DOCUMENT,
        token_count: 120,
        chunk_count: 2,
      },
    ];
    render(
      <Suggestions
        onSubmit={onSubmit}
        isDefaultAgent
        currentMessageFiles={currentMessageFiles}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Analyze a file" }));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ currentMessageFiles }),
    );
  });
});
