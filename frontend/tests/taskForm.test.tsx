import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TaskForm } from "@/components/TaskForm";
import { ALICE, BOB } from "./fixtures";

const setup = (onSubmit = vi.fn().mockResolvedValue(undefined)) => {
  render(<TaskForm users={[ALICE, BOB]} currentUserId={ALICE.id} submitLabel="Create task" onSubmit={onSubmit} onCancel={vi.fn()} />);
  return onSubmit;
};

describe("TaskForm", () => {
  it("shows a validation message and does not submit an empty title", async () => {
    const onSubmit = setup();
    await userEvent.click(screen.getByRole("button", { name: "Create task" }));
    expect(await screen.findByText("Title is required")).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("rejects a title over 200 characters", async () => {
    const onSubmit = setup();
    await userEvent.type(screen.getByLabelText("Title"), "x".repeat(201));
    await userEvent.click(screen.getByRole("button", { name: "Create task" }));
    expect(await screen.findByText(/200 characters/)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("lists registered users with name and email, and submits the chosen assignee", async () => {
    const onSubmit = setup();
    expect(screen.getByRole("option", { name: "Bob (bob@example.com)" })).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Title"), "  Ship it  ");
    await userEvent.selectOptions(screen.getByLabelText("Assign to"), BOB.id);
    await userEvent.click(screen.getByRole("button", { name: "Create task" }));
    await waitFor(() => expect(onSubmit).toHaveBeenCalledOnce());
    expect(onSubmit.mock.calls[0][0]).toMatchObject({ title: "Ship it", assigned_to: BOB.id });
  });

  it("prevents duplicate submissions while the request is in flight", async () => {
    let finish!: () => void;
    const onSubmit = vi.fn(() => new Promise<void>((r) => { finish = r; }));
    setup(onSubmit);
    await userEvent.type(screen.getByLabelText("Title"), "Once only");
    await userEvent.click(screen.getByRole("button", { name: "Create task" }));
    const busy = await screen.findByRole("button", { name: "Saving..." });
    expect(busy).toBeDisabled();
    await userEvent.click(busy);
    expect(onSubmit).toHaveBeenCalledTimes(1);
    finish();
  });
});
