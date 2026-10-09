import type { TaskStatus } from "@/types/api";
import { STATUS_LABEL } from "@/utils/format";

const COLORS: Record<TaskStatus, string> = {
  pending: "bg-amber-100 text-amber-800",
  in_progress: "bg-sky-100 text-sky-800",
  completed: "bg-emerald-100 text-emerald-800",
};
export const StatusBadge = ({ status }: { status: TaskStatus }) => (
  <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${COLORS[status]}`}>{STATUS_LABEL[status]}</span>
);
