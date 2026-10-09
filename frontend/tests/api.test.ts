import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/supabase", () => ({
  getSupabase: () => ({ auth: { getSession: async () => ({ data: { session: { access_token: "test-token" } } }) } }),
}));
import { api, ApiRequestError, setUnauthorizedHandler } from "@/services/api";

const reply = (status: number, body?: unknown) => new Response(body === undefined ? null : JSON.stringify(body), { status });

beforeEach(() => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://api.test";
  vi.restoreAllMocks();
});

describe("api service", () => {
  it("sends the bearer token and returns JSON", async () => {
    const f = vi.spyOn(globalThis, "fetch").mockResolvedValue(reply(200, { user: { id: "1" } }));
    expect(await api.me()).toEqual({ user: { id: "1" } });
    const [url, init] = f.mock.calls[0];
    expect(url).toBe("http://api.test/api/me");
    expect((init!.headers as Record<string, string>).Authorization).toBe("Bearer test-token");
  });

  it("turns an expired/invalid session (401) into a sign-out via the handler", async () => {
    const handler = vi.fn();
    setUnauthorizedHandler(handler);
    vi.spyOn(globalThis, "fetch").mockResolvedValue(reply(401, { error: { code: "token_expired", message: "Your session has expired." } }));
    await expect(api.listTasks({ role: "all", status: "", page: 1 })).rejects.toMatchObject({ status: 401, code: "token_expired" });
    expect(handler).toHaveBeenCalledOnce();
  });

  it("maps server error bodies to ApiRequestError with field details", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(reply(422, { error: { code: "validation_error", message: "Invalid request data", details: [{ field: "title", message: "too short" }] } }));
    const err = await api.createTask({ title: "", description: "", assigned_to: null }).catch((e) => e);
    expect(err).toBeInstanceOf(ApiRequestError);
    expect(err.details[0].field).toBe("title");
  });

  it("reports an unreachable server clearly", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));
    await expect(api.me()).rejects.toMatchObject({ code: "network_error" });
  });

  it("handles 204 No Content (delete)", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(reply(204));
    await expect(api.deleteTask("t1")).resolves.toBeUndefined();
  });

  it("builds list query strings with filters", async () => {
    const f = vi.spyOn(globalThis, "fetch").mockResolvedValue(reply(200, { tasks: [], page: 2, page_size: 10, total: 0 }));
    await api.listTasks({ role: "assigned", status: "completed", page: 2 });
    expect(String(f.mock.calls[0][0])).toBe("http://api.test/api/tasks?role=assigned&page=2&page_size=10&status=completed");
  });
});
