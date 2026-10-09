"use client";
import { useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { useApi } from "@/hooks/useApi";
import { notificationMessage, useToast } from "@/hooks/useToast";
import { api, ApiRequestError } from "@/services/api";
import { TaskForm, type TaskFormValues } from "@/components/TaskForm";
import { Card, EmptyState, ErrorBanner, Skeleton } from "@/components/ui";

export default function EditTaskPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const toast = useToast();
  const { profile } = useAuth();
  const task = useApi(useCallback(() => api.getTask(id), [id]));
  const users = useApi(useCallback(() => api.assignableUsers(), []));

  if (task.loading || users.loading) return <Skeleton className="mx-auto h-64 max-w-xl" />;
  if (task.error || users.error) return <ErrorBanner message={(task.error ?? users.error)!.message} onRetry={() => { task.reload(); users.reload(); }} />;
  const t = task.data!.task;
  if (!t.permissions.can_edit) return <EmptyState title="Only the creator can edit this task" />;

  async function onSubmit(v: TaskFormValues) {
    try {
      if (v.title !== t.title || v.description !== t.description) await api.updateTask(t.id, { title: v.title, description: v.description });
      if (v.assigned_to !== (t.assigned_to ?? "")) {
        const res = await api.setAssignee(t.id, v.assigned_to || null);
        const n = notificationMessage(res.notification?.status);
        if (n) toast.push(...n);
      }
      toast.push("success", "Task updated.");
      router.push(`/tasks/${t.id}`);
    } catch (err) {
      toast.push("error", err instanceof ApiRequestError ? err.message : "Could not update the task.");
    }
  }

  return (
    <div className="mx-auto max-w-xl space-y-4">
      <h1 className="text-2xl font-bold">Edit task</h1>
      <Card>
        <TaskForm users={users.data!.users} currentUserId={profile?.id} submitLabel="Save changes" onSubmit={onSubmit} onCancel={() => router.push(`/tasks/${t.id}`)}
          initial={{ title: t.title, description: t.description, assigned_to: t.assigned_to ?? "" }} />
      </Card>
    </div>
  );
}
