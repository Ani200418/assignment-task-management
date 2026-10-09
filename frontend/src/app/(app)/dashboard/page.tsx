"use client";
import { useCallback, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { useApi } from "@/hooks/useApi";
import { api } from "@/services/api";
import type { TaskFilters, TaskStatus } from "@/types/api";
import { STATUS_LABEL } from "@/utils/format";
import { TaskList } from "@/components/TaskList";
import { QuickCreate } from "@/components/QuickCreate";
import { Button, EmptyState, ErrorBanner, Skeleton, inputClass } from "@/components/ui";

const ROLES = [{ v: "all", l: "All" }, { v: "created", l: "Created by me" }, { v: "assigned", l: "Assigned to me" }] as const;

export default function DashboardPage() {
  const { profile } = useAuth();
  const [filters, setFilters] = useState<TaskFilters>({ role: "all", status: "", page: 1 });
  const tasks = useApi(useCallback(() => api.listTasks(filters), [filters]));
  const summary = useApi(useCallback(() => api.summary(), []));
  const users = useApi(useCallback(() => api.assignableUsers(), []));
  const refresh = () => { tasks.reload(); summary.reload(); };
  const totalPages = tasks.data ? Math.max(1, Math.ceil(tasks.data.total / tasks.data.page_size)) : 1;
  const hasFilter = filters.role !== "all" || filters.status !== "";

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      <section aria-label="Task summary" className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {(["pending", "in_progress", "completed"] as TaskStatus[]).map((s) => (
          <div key={s} className="rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-sm text-slate-500">{STATUS_LABEL[s]}</p>
            {summary.loading ? <Skeleton className="mt-2 h-8 w-12" /> : <p className="mt-1 text-3xl font-semibold" data-testid={`count-${s}`}>{summary.data?.counts[s] ?? "-"}</p>}
          </div>
        ))}
      </section>
      {summary.error && <ErrorBanner message="Could not load task counts." onRetry={summary.reload} />}

      <QuickCreate users={users.data?.users ?? []} currentUserId={profile?.id} onCreated={refresh} />

      <section aria-label="Tasks" className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <div role="tablist" aria-label="Task scope" className="flex rounded-lg bg-slate-200 p-1">
            {ROLES.map((r) => (
              <button key={r.v} role="tab" aria-selected={filters.role === r.v} onClick={() => setFilters({ ...filters, role: r.v, page: 1 })}
                className={`rounded-md px-3 py-1 text-sm ${filters.role === r.v ? "bg-white font-medium shadow-sm" : "text-slate-600"}`}>{r.l}</button>
            ))}
          </div>
          <label className="sr-only" htmlFor="status-filter">Filter by status</label>
          <select id="status-filter" className={`${inputClass} !w-auto`} value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value as TaskStatus | "", page: 1 })}>
            <option value="">Any status</option>
            {(Object.keys(STATUS_LABEL) as TaskStatus[]).map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
          </select>
        </div>

        {tasks.loading && <div className="space-y-2" aria-busy="true" aria-label="Loading tasks">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-16 w-full" />)}</div>}
        {tasks.error && <ErrorBanner message={tasks.error.message || "Could not load tasks."} onRetry={tasks.reload} />}
        {tasks.data && tasks.data.tasks.length === 0 && (
          hasFilter
            ? <EmptyState title="No tasks match these filters" hint="Try a different scope or status." />
            : <EmptyState title="No tasks yet" hint="Add your first task above, or ask a teammate to assign you one."
                action={<Link href="/tasks/new"><Button>Create a task</Button></Link>} />
        )}
        {tasks.data && tasks.data.tasks.length > 0 && (
          <>
            <TaskList tasks={tasks.data.tasks} currentUserId={profile?.id} />
            <div className="flex items-center justify-between text-sm text-slate-600">
              <span>Page {filters.page} of {totalPages} · {tasks.data.total} task{tasks.data.total === 1 ? "" : "s"}</span>
              <div className="flex gap-2">
                <Button variant="secondary" disabled={filters.page <= 1} onClick={() => setFilters({ ...filters, page: filters.page - 1 })}>Previous</Button>
                <Button variant="secondary" disabled={filters.page >= totalPages} onClick={() => setFilters({ ...filters, page: filters.page + 1 })}>Next</Button>
              </div>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
