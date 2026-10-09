"use client";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import type { Profile } from "@/types/api";
import { AssigneeSelect } from "./AssigneeSelect";
import { Button, FieldError, inputClass } from "./ui";

export const taskSchema = z.object({
  title: z.string().trim().min(1, "Title is required").max(200, "Title must be 200 characters or fewer"),
  description: z.string().max(5000, "Description must be 5000 characters or fewer"),
  assigned_to: z.string(), // "" = unassigned
});
export type TaskFormValues = z.infer<typeof taskSchema>;

interface Props {
  users: Profile[];
  currentUserId?: string;
  initial?: Partial<TaskFormValues>;
  submitLabel: string;
  onSubmit: (values: TaskFormValues) => Promise<void>;
  onCancel: () => void;
}

export function TaskForm({ users, currentUserId, initial, submitLabel, onSubmit, onCancel }: Props) {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<TaskFormValues>({
    resolver: zodResolver(taskSchema),
    defaultValues: { title: "", description: "", assigned_to: "", ...initial },
  });
  // isSubmitting stays true until onSubmit's promise settles, so the button stays disabled: no duplicate submits.
  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
      <div>
        <label htmlFor="title" className="mb-1 block text-sm font-medium text-slate-700">Title</label>
        <input id="title" className={inputClass} aria-invalid={!!errors.title} {...register("title")} />
        <FieldError message={errors.title?.message} />
      </div>
      <div>
        <label htmlFor="description" className="mb-1 block text-sm font-medium text-slate-700">Description</label>
        <textarea id="description" rows={5} className={inputClass} aria-invalid={!!errors.description} {...register("description")} />
        <FieldError message={errors.description?.message} />
      </div>
      <div>
        <label htmlFor="assigned_to" className="mb-1 block text-sm font-medium text-slate-700">Assign to</label>
        <AssigneeSelect id="assigned_to" users={users} currentUserId={currentUserId} {...register("assigned_to")} />
      </div>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onCancel}>Cancel</Button>
        <Button type="submit" disabled={isSubmitting}>{isSubmitting ? "Saving..." : submitLabel}</Button>
      </div>
    </form>
  );
}
