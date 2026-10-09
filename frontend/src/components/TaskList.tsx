import Link from "next/link";
import type { Task } from "@/types/api";
import { displayName, formatDate } from "@/utils/format";
import { StatusBadge } from "./StatusBadge";

export function TaskList({ tasks, currentUserId }: { tasks: Task[]; currentUserId: string | undefined }) {
  return (
    <ul className="divide-y divide-slate-200 overflow-hidden rounded-xl border border-slate-200 bg-white">
      {tasks.map((t) => (
        <li key={t.id}>
          <Link href={`/tasks/${t.id}`} className="block px-4 py-3 hover:bg-slate-50 focus:bg-slate-50 focus:outline-none">
            <div className="flex items-start justify-between gap-3">
              <p className="font-medium text-slate-900">{t.title}</p>
              <StatusBadge status={t.status} />
            </div>
            <p className="mt-1 text-xs text-slate-500">
              {t.created_by === currentUserId ? "Created by you" : `From ${displayName(t.creator)}`}
              {" · "}
              {t.assigned_to === currentUserId ? "Assigned to you" : `Assignee: ${displayName(t.assignee)}`}
              {" · "}
              {formatDate(t.created_at)}
            </p>
          </Link>
        </li>
      ))}
    </ul>
  );
}
