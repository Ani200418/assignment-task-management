"use client";
import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { useApi } from "@/hooks/useApi";
import { notificationMessage, useToast } from "@/hooks/useToast";
import { api, ApiRequestError } from "@/services/api";
import { TaskForm } from "@/components/TaskForm";
import { Card, ErrorBanner, Skeleton } from "@/components/ui";

export default function NewTaskPage() {
  const router = useRouter();
  const toast = useToast();
  const { profile } = useAuth();
  const users = useApi(useCallback(() => api.assignableUsers(), []));

  async function onSubmit(v: { title: string; description: string; assigned_to: string }) {
    try {
      const res = await api.createTask({ title: v.title, description: v.description, assigned_to: v.assigned_to || null });
      toast.push("success", "Task created.");
      const n = notificationMessage(res.notification?.status);
      if (n) toast.push(...n);
      router.push(`/tasks/${res.task.id}`);
    } catch (err) {
      toast.push("error", err instanceof ApiRequestError ? err.message : "Could not create the task.");
    }
  }

  return (
    <div className="mx-auto max-w-xl space-y-4">
      <h1 className="text-2xl font-bold">New task</h1>
      <Card>
        {users.loading && <Skeleton className="h-40 w-full" />}
        {users.error && <ErrorBanner message="Could not load the list of users." onRetry={users.reload} />}
        {users.data && <TaskForm users={users.data.users} currentUserId={profile?.id} submitLabel="Create task" onSubmit={onSubmit} onCancel={() => router.push("/dashboard")} />}
      </Card>
    </div>
  );
}
