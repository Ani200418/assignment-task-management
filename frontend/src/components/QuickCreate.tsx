"use client";
import { useState } from "react";
import { api, ApiRequestError } from "@/services/api";
import { notificationMessage, useToast } from "@/hooks/useToast";
import type { Profile } from "@/types/api";
import { AssigneeSelect } from "./AssigneeSelect";
import { Button, Card, inputClass } from "./ui";

export function QuickCreate({ users, currentUserId, onCreated }: { users: Profile[]; currentUserId?: string; onCreated: () => void }) {
  const [title, setTitle] = useState("");
  const [assignee, setAssignee] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    if (!title.trim()) { setError("Enter a title"); return; }
    setBusy(true); setError(null);
    try {
      const res = await api.createTask({ title: title.trim(), description: "", assigned_to: assignee || null });
      toast.push("success", "Task created.");
      const n = notificationMessage(res.notification?.status);
      if (n) toast.push(...n);
      setTitle(""); setAssignee(""); onCreated();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Could not create the task.");
    } finally { setBusy(false); }
  }

  return (
    <Card>
      <form onSubmit={submit} className="flex flex-col gap-3 sm:flex-row sm:items-start" noValidate>
        <div className="flex-1">
          <label htmlFor="quick-title" className="sr-only">Quick task title</label>
          <input id="quick-title" className={inputClass} placeholder="Quick add: what needs doing?" value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} />
          {error && <p role="alert" className="mt-1 text-xs text-red-600">{error}</p>}
        </div>
        <div className="sm:w-56">
          <label htmlFor="quick-assignee" className="sr-only">Assign to</label>
          <AssigneeSelect id="quick-assignee" users={users} currentUserId={currentUserId} value={assignee} onChange={(e) => setAssignee(e.target.value)} />
        </div>
        <Button type="submit" disabled={busy}>{busy ? "Adding..." : "Add task"}</Button>
      </form>
    </Card>
  );
}
