/**
 * @jest-environment jsdom
 */
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import englishMessages from "@/i18n/messages/en.json";
import { Logo } from "@/lib/app/components";

jest.mock("@/lib/settings/hooks", () => ({
  useSettings: () => ({
    appName: "TON",
    enterprise: null,
    logoUrl: null,
  }),
}));

test("the existing logo fallback shows the TON product name", () => {
  render(
    <NextIntlClientProvider locale="en" messages={englishMessages}>
      <Logo />
    </NextIntlClientProvider>
  );

  expect(screen.getAllByText("TON")[0]).toBeVisible();
});
