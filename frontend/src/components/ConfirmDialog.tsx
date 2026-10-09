"use client";
import { useEffect, useRef } from "react";
import { Button } from "./ui";

export function ConfirmDialog({ title, message, confirmLabel, busy, onConfirm, onCancel }: {
  title: string; message: string; confirmLabel: string; busy?: boolean; onConfirm: () => void; onCancel: () => void;
}) {
  const cancelRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    cancelRef.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onCancel(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onCancel]);
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4">
      <div role="dialog" aria-modal="true" aria-labelledby="dlg-title" className="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
        <h2 id="dlg-title" className="text-lg font-semibold text-slate-900">{title}</h2>
        <p className="mt-2 text-sm text-slate-600">{message}</p>
        <div className="mt-5 flex justify-end gap-2">
          <button ref={cancelRef} onClick={onCancel} className="rounded-lg px-4 py-2 text-sm ring-1 ring-slate-300 hover:bg-slate-50">Cancel</button>
          <Button variant="danger" onClick={onConfirm} disabled={busy}>{busy ? "Deleting..." : confirmLabel}</Button>
        </div>
      </div>
    </div>
  );
}
