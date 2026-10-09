import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const signInWithGoogle = vi.fn();
let search = "";
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn() }), useSearchParams: () => new URLSearchParams(search) }));
vi.mock("@/hooks/useAuth", () => ({ useAuth: () => ({ loading: false, session: null, signInWithGoogle }) }));
import LoginPage from "@/app/login/page";

describe("Login page", () => {
  it("renders product name and a Google button, with no password field", () => {
    search = "";
    render(<LoginPage />);
    expect(screen.getByRole("heading", { name: "TaskFlow" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /continue with google/i })).toBeEnabled();
    expect(screen.queryByLabelText(/password/i)).toBeNull();
  });

  it("starts Google sign-in and shows a loading state", async () => {
    search = "";
    signInWithGoogle.mockReturnValue(new Promise(() => {}));
    render(<LoginPage />);
    await userEvent.click(screen.getByRole("button", { name: /continue with google/i }));
    expect(signInWithGoogle).toHaveBeenCalled();
    expect(screen.getByRole("button", { name: /redirecting/i })).toBeDisabled();
  });

  it("shows an error when sign-in fails to start", async () => {
    search = "";
    signInWithGoogle.mockRejectedValue(new Error("boom"));
    render(<LoginPage />);
    await userEvent.click(screen.getByRole("button", { name: /continue with google/i }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/sign-in failed/i));
  });

  it.each([["cancelled", /cancelled/i], ["session_expired", /session has expired/i], ["whatever", /sign-in failed/i]])(
    "maps ?error=%s to a fixed friendly message", (code, text) => {
      search = `error=${code}`;
      render(<LoginPage />);
      expect(screen.getByRole("alert")).toHaveTextContent(text);
    });

  it("never echoes arbitrary URL text into the page", () => {
    search = "error=<script>alert(1)</script>";
    render(<LoginPage />);
    expect(screen.getByRole("alert")).not.toHaveTextContent("script");
  });
});
