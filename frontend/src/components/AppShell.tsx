"use client";
import { useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { displayName } from "@/utils/format";

const LINKS = [{ href: "/dashboard", label: "Dashboard" }, { href: "/tasks/new", label: "New task" }];

export function AppShell({ children }: { children: ReactNode }) {
  const { profile, session, signOut } = useAuth();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const name = profile ? displayName(profile) : session?.user.email ?? "";
  const avatar = profile?.avatar_url;

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-3">
          <Link href="/dashboard" className="text-lg font-semibold text-indigo-600">TaskFlow</Link>
          <nav aria-label="Main" className="hidden items-center gap-6 sm:flex">
            {LINKS.map((l) => (
              <Link key={l.href} href={l.href} aria-current={pathname === l.href ? "page" : undefined}
                className={`text-sm ${pathname === l.href ? "font-semibold text-indigo-600" : "text-slate-600 hover:text-slate-900"}`}>{l.label}</Link>
            ))}
            <div className="flex items-center gap-2 border-l border-slate-200 pl-6">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              {avatar ? <img src={avatar} alt="" referrerPolicy="no-referrer" className="h-8 w-8 rounded-full" />
                : <span className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-100 text-sm font-medium text-indigo-700">{name.charAt(0).toUpperCase()}</span>}
              <div className="leading-tight"><p className="text-sm font-medium text-slate-800">{name}</p>{profile && <p className="text-xs text-slate-500">{profile.email}</p>}</div>
              <button onClick={() => void signOut()} className="ml-2 rounded-lg px-3 py-1.5 text-sm text-slate-600 ring-1 ring-slate-300 hover:bg-slate-50">Log out</button>
            </div>
          </nav>
          <button className="rounded-lg p-2 ring-1 ring-slate-300 sm:hidden" aria-expanded={open} aria-controls="mobile-nav" aria-label="Toggle menu" onClick={() => setOpen((o) => !o)}>
            <span aria-hidden>{open ? "✕" : "☰"}</span>
          </button>
        </div>
        {open && (
          <nav id="mobile-nav" aria-label="Mobile" className="space-y-1 border-t border-slate-200 px-4 py-3 sm:hidden">
            {LINKS.map((l) => <Link key={l.href} href={l.href} onClick={() => setOpen(false)} className="block rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-slate-50">{l.label}</Link>)}
            <p className="px-3 pt-2 text-xs text-slate-500">{name}{profile ? ` · ${profile.email}` : ""}</p>
            <button onClick={() => void signOut()} className="w-full rounded-lg px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50">Log out</button>
          </nav>
        )}
      </header>
      <main className="mx-auto max-w-4xl px-4 py-6">{children}</main>
    </div>
  );
}
