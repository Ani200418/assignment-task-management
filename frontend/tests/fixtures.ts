import type { Profile, Task } from "@/types/api";

export const ALICE: Profile = { id: "a1", email: "alice@example.com", full_name: "Alice", avatar_url: null };
export const BOB: Profile = { id: "b2", email: "bob@example.com", full_name: "Bob", avatar_url: null };

export function makeTask(over: Partial<Task> = {}): Task {
  return {
    id: "t1", title: "Write report", description: "Quarterly numbers", status: "pending",
    created_by: ALICE.id, assigned_to: BOB.id, created_at: "2026-01-01T10:00:00Z", updated_at: "2026-01-01T10:00:00Z",
    completed_at: null, creator: ALICE, assignee: BOB,
    permissions: { can_edit: true, can_reassign: true, can_delete: true, can_change_status: true },
    ...over,
  };
}
