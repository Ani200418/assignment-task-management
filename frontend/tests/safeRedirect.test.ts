import { describe, expect, it } from "vitest";
import { safeRedirectPath } from "@/lib/safeRedirect";

describe("safeRedirectPath (open-redirect protection)", () => {
  it("allows normal in-app paths", () => {
    expect(safeRedirectPath("/tasks/123")).toBe("/tasks/123");
    expect(safeRedirectPath("/dashboard?x=1")).toBe("/dashboard?x=1");
  });
  it.each(["https://evil.example", "//evil.example", "/\\evil.example", "javascript:alert(1)", "evil", "", null, undefined, "/login", "/auth/callback", "/a\nb"])(
    "rejects %j", (bad) => expect(safeRedirectPath(bad as string)).toBe("/dashboard"));
});
