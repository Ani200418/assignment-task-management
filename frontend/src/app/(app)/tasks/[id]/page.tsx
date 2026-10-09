"use client";
import { useCallback, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useApi } from "@/hooks/useApi";
import { notificationMessage, useToast } from "@/hooks/useToast";
import { api, ApiRequestError } from "@/services/api";
import type { TaskStatus } from "@/types/api";
import { STATUS_LABEL, displayName, formatDate } from "@/utils/format";
import { StatusBadge } from "@/components/StatusBadge";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { Button, Card, EmptyState, ErrorBanner, Skeleton, inputClass } from "@/components/ui";

export default function TaskDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const toast = useToast();
  const { data, error, loading, reload } = useApi(useCallback(() => api.getTask(id), [id]));
  const [busy, setBusy] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  if (loading) return <div className="space-y-3" aria-busy="true" aria-label="Loading task"><Skeleton className="h-8 w-64" /><Skeleton className="h-40 w-full" /></div>;
  if (error) {
    const hidden = error instanceof ApiRequestError && (error.status === 404 || error.status === 422);
    return hidden
      ? <EmptyState title="Task not found" hint="It may have been deleted, or you do not have access to it." action={<Link href="/dashboard"><Button variant="secondary">Back to dashboard</Button></Link>} />
      : <ErrorBanner message={error.message} onRetry={reload} />;
  }
  const task = data!.task;
  const perms = task.permissions;

  async function changeStatus(status: TaskStatus) {
    if (busy) return;
    setBusy(true);
    try {
      const res = await api.setStatus(task.id, status);
      toast.push("success", `Status changed to ${STATUS_LABEL[status]}.`);
      const n = notificationMessage(res.notification?.status);
      if (n) toast.push(...n);
      reload();
    } catch (err) {
      toast.push("error", err instanceof ApiRequestError ? err.message : "Could not update the status.");
    } finally { setBusy(false); }
  }

  async function remove() {
    setBusy(true);
    try { await api.deleteTask(task.id); toast.push("success", "Task deleted."); router.push("/dashboard"); }
    catch (err) { toast.push("error", err instanceof ApiRequestError ? err.message : "Could not delete the task."); setBusy(false); setConfirmDelete(false); }
  }

  return (
    <div className="space-y-4">
      <Link href="/dashboard" className="text-sm text-indigo-600 hover:underline">← Back to dashboard</Link>
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <h1 className="text-2xl font-bold">{task.title}</h1>
          <StatusBadge status={task.status} />
        </div>
        <p className="mt-4 whitespace-pre-wrap text-slate-700">{task.description || <span className="text-slate-400">No description.</span>}</p>
        <dl className="mt-6 grid grid-cols-1 gap-4 text-sm sm:grid-cols-2">
          <div><dt className="text-slate-500">Created by</dt><dd className="font-medium">{displayName(task.creator)}</dd></div>
          <div><dt className="text-slate-500">Assigned to</dt><dd className="font-medium">{displayName(task.assignee)}</dd></div>
          <div><dt className="text-slate-500">Created</dt><dd>{formatDate(task.created_at)}</dd></div>
          <div><dt className="text-slate-500">Last updated</dt><dd>{formatDate(task.updated_at)}</dd></div>
          {task.completed_at && <div><dt className="text-slate-500">Completed</dt><dd>{formatDate(task.completed_at)}</dd></div>}
        </dl>
      </Card>

      {(perms.can_change_status || perms.can_edit || perms.can_delete) && (
        <Card className="flex flex-wrap items-end gap-3">
          {perms.can_change_status && (
            <>
              <div>
                <label htmlFor="status" className="mb-1 block text-sm font-medium text-slate-700">Status</label>
                <select id="status" className={`${inputClass} !w-auto`} value={task.status} disabled={busy} onChange={(e) => void changeStatus(e.target.value as TaskStatus)}>
                  {(Object.keys(STATUS_LABEL) as TaskStatus[]).map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
                </select>
              </div>
              {task.status !== "completed"
                ? <Button disabled={busy} onClick={() => void changeStatus("completed")}>Mark completed</Button>
                : <Button variant="secondary" disabled={busy} onClick={() => void changeStatus("in_progress")}>Reopen</Button>}
            </>
          )}
          {perms.can_edit && <Link href={`/tasks/${task.id}/edit`}><Button variant="secondary">Edit / reassign</Button></Link>}
          {perms.can_delete && <Button variant="danger" disabled={busy} onClick={() => setConfirmDelete(true)}>Delete</Button>}
        </Card>
      )}
      {confirmDelete && <ConfirmDialog title="Delete this task?" message="This permanently deletes the task. This cannot be undone." confirmLabel="Delete task" busy={busy} onConfirm={() => void remove()} onCancel={() => setConfirmDelete(false)} />}
    </div>
  );
}
