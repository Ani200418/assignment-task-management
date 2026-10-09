import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

const replace = vi.fn();
let auth: { loading: boolean; session: unknown } = { loading: false, session: null };
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace }), usePathname: () => "/tasks/abc" }));
vi.mock("@/hooks/useAuth", () => ({ useAuth: () => auth }));
import { RequireAuth } from "@/components/RequireAuth";

beforeEach(() => { replace.mockReset(); sessionStorage.clear(); });

describe("RequireAuth route guard", () => {
  it("redirects signed-out visitors to /login and remembers where they were going", () => {
    auth = { loading: false, session: null };
    render(<RequireAuth><p>secret page</p></RequireAuth>);
    expect(replace).toHaveBeenCalledWith("/login");
    expect(sessionStorage.getItem("postLoginRedirect")).toBe("/tasks/abc");
    expect(screen.queryByText("secret page")).toBeNull();
  });
  it("shows a loading state (not the page, not a redirect) while the session is loading", () => {
    auth = { loading: true, session: null };
    render(<RequireAuth><p>secret page</p></RequireAuth>);
    expect(screen.getByLabelText("Loading")).toBeInTheDocument();
    expect(replace).not.toHaveBeenCalled();
  });
  it("renders the page for a signed-in user", () => {
    auth = { loading: false, session: { user: { id: "1" } } };
    render(<RequireAuth><p>secret page</p></RequireAuth>);
    expect(screen.getByText("secret page")).toBeInTheDocument();
  });
});
