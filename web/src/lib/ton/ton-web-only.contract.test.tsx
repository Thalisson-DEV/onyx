import fs from "node:fs";
import path from "node:path";

const WEB_ROOT = path.resolve(__dirname, "../../..");
const REPOSITORY_ROOT = path.resolve(WEB_ROOT, "..");

function readRepositoryFile(relativePath: string) {
  return fs.readFileSync(path.join(REPOSITORY_ROOT, relativePath), "utf8");
}

describe("TON web-only baseline contracts", () => {
  it("keeps the web route, design-system, token, and flag owners", () => {
    const expectedPaths = [
      "web/src/app",
      "web/src/sections/sidebar/AppSidebar.tsx",
      "web/src/lib/swr-keys.ts",
      "web/lib/opal/src",
      "web/lib/shared/tokens",
      "web/src/lib/constants.ts",
      "web/src/lib/settings/hooks.ts",
    ];

    for (const relativePath of expectedPaths) {
      expect(fs.existsSync(path.join(REPOSITORY_ROOT, relativePath))).toBe(
        true
      );
    }
  });

  it("keeps the web chat payload aligned with the backend", () => {
    const webContract = readRepositoryFile("web/src/app/app/services/lib.tsx");
    const backendContract = readRepositoryFile(
      "backend/onyx/server/query_and_chat/models.py"
    );

    expect(webContract).toContain("MessageOrigin");
    expect(webContract).toContain("additional_context: additionalContext");
    expect(webContract).toContain("/api/chat/send-chat-message");
    expect(backendContract).toContain("class MessageOrigin");
    expect(backendContract).toContain("additional_context");
  });

  it("does not add a Telegram product surface during the baseline", () => {
    expect(fs.existsSync(path.join(WEB_ROOT, "src/app/telegram"))).toBe(false);
    expect(fs.existsSync(path.join(WEB_ROOT, "src/app/app/telegram"))).toBe(
      false
    );
  });
});
