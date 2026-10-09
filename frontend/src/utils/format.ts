export const STATUS_LABEL = { pending: "Pending", in_progress: "In progress", completed: "Completed" } as const;
export const displayName = (p: { full_name: string | null; email: string } | null | undefined) =>
  p ? p.full_name || p.email : "Unassigned";
export const formatDate = (iso: string | null) =>
  iso ? new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) : "-";
