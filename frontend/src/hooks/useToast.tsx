"use client";
import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

type Toast = { id: number; kind: "success" | "error" | "info"; message: string };
const ToastContext = createContext<{ push: (kind: Toast["kind"], message: string) => void }>({ push: () => {} });

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((kind: Toast["kind"], message: string) => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, kind, message }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 6000);
  }, []);
  const colors = { success: "bg-emerald-600", error: "bg-red-600", info: "bg-slate-800" };
  return (
    <ToastContext.Provider value={{ push }}>
      {children}
      <div aria-live="polite" role="status" className="fixed bottom-4 right-4 z-50 flex w-80 max-w-[calc(100vw-2rem)] flex-col gap-2">
        {toasts.map((t) => (
          <div key={t.id} className={`rounded-lg px-4 py-3 text-sm text-white shadow-lg ${colors[t.kind]}`}>{t.message}</div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
export const useToast = () => useContext(ToastContext);

/** Turns the backend's notification info into an honest message. */
export function notificationMessage(status: string | undefined): [Toast["kind"], string] | null {
  if (status === "sent") return ["success", "Email notification sent."];
  if (status === "queued") return ["info", "Saved. The email notification is queued and will be retried."];
  if (status === "failed") return ["error", "Saved, but the email notification could not be sent."];
  return null;
}
