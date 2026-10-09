import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ToastProvider } from "@/hooks/useToast";
import { ApiRequestError } from "@/services/api";
import { makeTask } from "./fixtures";

const api = vi.hoisted(() => ({ getTask: vi.fn(), setStatus: vi.fn(), deleteTask: vi.fn() }));
const push = vi.hoisted(() => vi.fn());
vi.mock("@/services/api", async (orig) => ({ ...(await orig<typeof import("@/services/api")>()), api }));
vi.mock("next/navigation", () => ({ useParams: () => ({ id: "t1" }), useRouter: () => ({ push }) }));
import TaskDetailPage from "@/app/(app)/tasks/[id]/page";

const renderPage = () => render(<ToastProvider><TaskDetailPage /></ToastProvider>);
beforeEach(() => vi.resetAllMocks());

describe("Task detail", () => {
  it("lets an authorised user complete a task and reports the email outcome", async () => {
    api.getTask.mockResolvedValue({ task: makeTask() });
    api.setStatus.mockResolvedValue({ task: makeTask({ status: "completed" }), notification: { status: "sent" } });
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: "Mark completed" }));
    expect(api.setStatus).toHaveBeenCalledWith("t1", "completed");
    expect(await screen.findByText("Status changed to Completed.")).toBeInTheDocument();
    expect(screen.getByText("Email notification sent.")).toBeInTheDocument();
  });

  it("does not claim success when the email failed", async () => {
    api.getTask.mockResolvedValue({ task: makeTask() });
    api.setStatus.mockResolvedValue({ task: makeTask({ status: "completed" }), notification: { status: "failed" } });
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: "Mark completed" }));
    expect(await screen.findByText(/email notification could not be sent/i)).toBeInTheDocument();
  });

  it("shows only status controls to an assignee (no edit / delete)", async () => {
    api.getTask.mockResolvedValue({ task: makeTask({ permissions: { can_edit: false, can_reassign: false, can_delete: false, can_change_status: true } }) });
    renderPage();
    expect(await screen.findByRole("button", { name: "Mark completed" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete" })).toBeNull();
    expect(screen.queryByRole("link", { name: /Edit/ })).toBeNull();
  });

  it("offers Reopen for a completed task", async () => {
    api.getTask.mockResolvedValue({ task: makeTask({ status: "completed", completed_at: "2026-01-02T00:00:00Z" }) });
    renderPage();
    expect(await screen.findByRole("button", { name: "Reopen" })).toBeInTheDocument();
  });

  it("shows 'not found' for a missing or forbidden task (backend answers 404 for both)", async () => {
    api.getTask.mockRejectedValue(new ApiRequestError(404, "not_found", "Task not found"));
    renderPage();
    expect(await screen.findByText("Task not found")).toBeInTheDocument();
  });

  it("asks for confirmation before deleting", async () => {
    api.getTask.mockResolvedValue({ task: makeTask() });
    api.deleteTask.mockResolvedValue(undefined);
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: "Delete" }));
    expect(api.deleteTask).not.toHaveBeenCalled();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Delete task" }));
    expect(api.deleteTask).toHaveBeenCalledWith("t1");
  });
});
