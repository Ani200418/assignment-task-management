export type TaskStatus = "pending" | "in_progress" | "completed";

export interface Profile { id: string; email: string; full_name: string | null; avatar_url: string | null }

export interface Permissions { can_edit: boolean; can_reassign: boolean; can_delete: boolean; can_change_status: boolean }

export interface Task {
  id: string; title: string; description: string; status: TaskStatus;
  created_by: string; assigned_to: string | null;
  created_at: string; updated_at: string; completed_at: string | null;
  creator: Profile | null; assignee: Profile | null; permissions: Permissions;
}

/** What happened to the e-mail for this change. "sent" = Gmail accepted it (not proof of inbox delivery). */
export interface NotificationInfo { status: "not_required" | "sent" | "queued" | "failed" }

export interface TaskListResponse { tasks: Task[]; page: number; page_size: number; total: number }
export interface TaskMutationResponse { task: Task; notification?: NotificationInfo }
export interface TaskFilters { role: "all" | "created" | "assigned"; status: TaskStatus | ""; page: number }
export type Counts = Record<TaskStatus, number>;
