import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { TaskList } from "@/components/TaskList";
import { ALICE, BOB, makeTask } from "./fixtures";

describe("TaskList", () => {
  it("renders titles, statuses and who-is-who relative to the current user", () => {
    render(<TaskList currentUserId={ALICE.id} tasks={[
      makeTask({ id: "1", title: "Mine to Bob" }),
      makeTask({ id: "2", title: "From Bob", created_by: BOB.id, creator: BOB, assigned_to: ALICE.id, assignee: ALICE, status: "completed" }),
    ]} />);
    expect(screen.getByRole("link", { name: /Mine to Bob/ })).toHaveAttribute("href", "/tasks/1");
    expect(screen.getByText(/Created by you/)).toBeInTheDocument();
    expect(screen.getByText(/Assigned to you/)).toBeInTheDocument();
    expect(screen.getByText("Completed")).toBeInTheDocument();
    expect(screen.getByText("Pending")).toBeInTheDocument();
  });
});
