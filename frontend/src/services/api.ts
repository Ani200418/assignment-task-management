import { getSupabase } from "@/lib/supabase";
import type { Counts, Profile, Task, TaskFilters, TaskListResponse, TaskMutationResponse, TaskStatus } from "@/types/api";

const PAGE_SIZE = 10;

export class ApiRequestError extends Error {
  constructor(public status: number, public code: string, message: string, public details?: { field: string; message: string }[]) {
    super(message);
  }
}

// AuthProvider registers what should happen when the server says our session is no longer valid.
let onUnauthorized: () => void = () => {};
export function setUnauthorizedHandler(fn: () => void) { onUnauthorized = fn; }

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!base) throw new ApiRequestError(0, "config_error", "NEXT_PUBLIC_API_BASE_URL is not set");
  const { data } = await getSupabase().auth.getSession(); // supabase-js refreshes an expiring token for us
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (data.session) headers.Authorization = `Bearer ${data.session.access_token}`;

  let res: Response;
  try {
    res = await fetch(`${base}${path}`, { ...init, headers: { ...headers, ...init.headers } });
  } catch {
    throw new ApiRequestError(0, "network_error", "Cannot reach the server. Check your connection and try again.");
  }
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const err = body?.error ?? {};
    if (res.status === 401) onUnauthorized();
    throw new ApiRequestError(res.status, err.code ?? "unknown_error", err.message ?? "Something went wrong", err.details);
  }
  return body as T;
}

const json = (method: string, body?: unknown): RequestInit => ({ method, body: body === undefined ? undefined : JSON.stringify(body) });

export const api = {
  me: () => request<{ user: Profile }>("/api/me"),
  assignableUsers: () => request<{ users: Profile[] }>("/api/users/assignable"),
  summary: () => request<{ counts: Counts }>("/api/tasks/summary"),
  listTasks: (f: TaskFilters) => {
    const q = new URLSearchParams({ role: f.role, page: String(f.page), page_size: String(PAGE_SIZE) });
    if (f.status) q.set("status", f.status);
    return request<TaskListResponse>(`/api/tasks?${q}`);
  },
  getTask: (id: string) => request<{ task: Task }>(`/api/tasks/${id}`),
  createTask: (b: { title: string; description: string; assigned_to: string | null }) =>
    request<TaskMutationResponse>("/api/tasks", json("POST", b)),
  updateTask: (id: string, b: { title?: string; description?: string }) =>
    request<TaskMutationResponse>(`/api/tasks/${id}`, json("PATCH", b)),
  setStatus: (id: string, status: TaskStatus) => request<TaskMutationResponse>(`/api/tasks/${id}/status`, json("PATCH", { status })),
  setAssignee: (id: string, assigned_to: string | null) =>
    request<TaskMutationResponse>(`/api/tasks/${id}/assignee`, json("PATCH", { assigned_to })),
  deleteTask: (id: string) => request<void>(`/api/tasks/${id}`, json("DELETE")),
};
export { PAGE_SIZE };
