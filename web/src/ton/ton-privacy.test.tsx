import fs from "node:fs";
import path from "node:path";
import {
  isTrustedExtensionPageChange,
  safeLoginReturnPath,
  trustedExtensionSearchParams,
} from "@/lib/ton/privacy";

const WEB_ROOT = path.resolve(__dirname, "../..");

describe("TON privacy boundaries", () => {
  it("drops query data and fragments from login return paths", () => {
    expect(
      safeLoginReturnPath(
        "/app",
        "?user-prompt=payroll&token=secret",
        "#private"
      )
    ).toBe("/app");
  });

  it("accepts only parent messages from extension origins for this app", () => {
    const parent = {} as MessageEventSource;
    const valid = {
      source: parent,
      origin: "chrome-extension://known-extension",
      data: { type: "PAGE_CHANGE", href: "https://ton.test/app?x=1" },
    } as MessageEvent;

    expect(
      isTrustedExtensionPageChange(valid, parent, "https://ton.test")
    ).toBe(true);
    expect(
      isTrustedExtensionPageChange(
        { ...valid, origin: "https://attacker.test" },
        parent,
        "https://ton.test"
      )
    ).toBe(false);
    expect(
      isTrustedExtensionPageChange(
        { ...valid, source: {} as MessageEventSource },
        parent,
        "https://ton.test"
      )
    ).toBe(false);
    expect(
      isTrustedExtensionPageChange(
        {
          ...valid,
          data: { type: "PAGE_CHANGE", href: "https://attacker.test/app" },
        },
        parent,
        "https://ton.test"
      )
    ).toBe(false);
  });

  it("keeps only supported query fields from extension messages", () => {
    expect(
      trustedExtensionSearchParams(
        "https://ton.test/app?user-prompt=review&sources=drive&token=secret",
        "https://ton.test"
      )
    ).toBe("user-prompt=review&sources=drive");
  });

  it("gates all browser analytics when TON mode is enabled", () => {
    const layout = fs.readFileSync(
      path.join(WEB_ROOT, "src/app/layout.tsx"),
      "utf8"
    );
    const providers = fs.readFileSync(
      path.join(WEB_ROOT, "src/app/providers.tsx"),
      "utf8"
    );

    expect(layout).toContain("TON_EXTERNAL_TELEMETRY_ENABLED");
    expect(layout).toContain("TON_EXTERNAL_TELEMETRY_ENABLED &&");
    expect(providers).toContain("externalTelemetryEnabled");
    expect(providers).toContain("maskAllInputs: true");
  });
});
