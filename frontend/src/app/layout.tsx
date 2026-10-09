import type { Metadata } from "next";
import type { ReactNode } from "react";
import { AuthProvider } from "@/hooks/useAuth";
import { ToastProvider } from "@/hooks/useToast";
import "./globals.css";

export const metadata: Metadata = {
  title: "TaskFlow - task management",
  description: "Create, assign and complete tasks with your team.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full bg-slate-50 text-slate-900">
        <ToastProvider><AuthProvider>{children}</AuthProvider></ToastProvider>
      </body>
    </html>
  );
}
