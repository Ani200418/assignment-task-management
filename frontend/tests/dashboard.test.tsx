import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ToastProvider } from "@/hooks/useToast";
import { ApiRequestError } from "@/services/api";
import { ALICE, BOB, makeTask } from "./fixtures";

const api = vi.hoisted(() => ({ listTasks: vi.fn(), summary: vi.fn(), assignableUsers: vi.fn(), createTask: vi.fn() }));
vi.mock("@/services/api", async (orig) => ({ ...(await orig<typeof import("@/services/api")>()), api }));
vi.mock("@/hooks/useAuth", () => ({ useAuth: () => ({ profile: ALICE }) }));
import DashboardPage from "@/app/(app)/dashboard/page";

const renderPage = () => render(<ToastProvider><DashboardPage /></ToastProvider>);
const list = (tasks: ReturnType<typeof makeTask>[]) => ({ tasks, page: 1, page_size: 10, total: tasks.length });

beforeEach(() => {
  vi.resetAllMocks();
  api.summary.mockResolvedValue({ counts: { pending: 2, in_progress: 1, completed: 3 } });
  api.assignableUsers.mockResolvedValue({ users: [ALICE, BOB] });
});

describe("Dashboard", () => {
  it("shows loading skeletons first, then real counts and tasks", async () => {
    api.listTasks.mockResolvedValue(list([makeTask({ title: "Write report" })]));
    renderPage();
    expect(screen.getByLabelText("Loading tasks")).toBeInTheDocument();
    expect(await screen.findByText("Write report")).toBeInTheDocument();
    expect(screen.getByTestId("count-pending")).toHaveTextContent("2");
    expect(screen.getByTestId("count-completed")).toHaveTextContent("3");
  });

  it("shows an error banner and recovers on Retry", async () => {
    api.listTasks.mockRejectedValueOnce(new ApiRequestError(0, "network_error", "Cannot reach the server."));
    api.listTasks.mockResolvedValueOnce(list([makeTask({ title: "Back online" })]));
    renderPage();
    expect(await screen.findByRole("alert")).toHaveTextContent("Cannot reach the server.");
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("Back online")).toBeInTheDocument();
  });

  it("shows an empty state when there are no tasks", async () => {
    api.listTasks.mockResolvedValue(list([]));
    renderPage();
    expect(await screen.findByText("No tasks yet")).toBeInTheDocument();
  });

  it("re-queries with the chosen scope and status filters", async () => {
    api.listTasks.mockResolvedValue(list([]));
    renderPage();
    await screen.findByText("No tasks yet");
    await userEvent.click(screen.getByRole("tab", { name: "Assigned to me" }));
    await userEvent.selectOptions(screen.getByLabelText("Filter by status"), "completed");
    expect(api.listTasks).toHaveBeenLastCalledWith({ role: "assigned", status: "completed", page: 1 });
    expect(await screen.findByText("No tasks match these filters")).toBeInTheDocument();
  });

  it("quick-create validates, calls the API with the assignee and refreshes the list", async () => {
    api.listTasks.mockResolvedValue(list([]));
    api.createTask.mockResolvedValue({ task: makeTask(), notification: { status: "sent" } });
    renderPage();
    await screen.findByText("No tasks yet");
    await userEvent.click(screen.getByRole("button", { name: "Add task" }));
    expect(await screen.findByText("Enter a title")).toBeInTheDocument();
    expect(api.createTask).not.toHaveBeenCalled();
    await userEvent.type(screen.getByLabelText("Quick task title"), "Call client");
    await userEvent.selectOptions(screen.getByLabelText("Assign to"), BOB.id);
    await userEvent.click(screen.getByRole("button", { name: "Add task" }));
    expect(api.createTask).toHaveBeenCalledWith({ title: "Call client", description: "", assigned_to: BOB.id });
    expect(await screen.findByText("Email notification sent.")).toBeInTheDocument();
    expect(api.listTasks.mock.calls.length).toBeGreaterThan(1);
  });
});
