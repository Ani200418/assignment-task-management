"use client";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { Button, Card } from "@/components/ui";

// Fixed messages only: we never print text taken from the URL, so nobody can inject content here.
export const LOGIN_ERRORS: Record<string, string> = {
  cancelled: "Sign-in was cancelled. You can try again whenever you are ready.",
  failed: "Sign-in failed. Please try again.",
  session_expired: "Your session has expired. Please sign in again.",
};

function LoginContent() {
  const { loading, session, signInWithGoogle } = useAuth();
  const router = useRouter();
  const code = useSearchParams().get("error");
  const [busy, setBusy] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const urlError = code ? LOGIN_ERRORS[code] ?? LOGIN_ERRORS.failed : null;

  useEffect(() => { if (!loading && session) router.replace("/dashboard"); }, [loading, session, router]);

  async function onClick() {
    setBusy(true); setLocalError(null);
    try { await signInWithGoogle(); } // the browser leaves for Google here
    catch { setLocalError(LOGIN_ERRORS.failed); setBusy(false); }
  }

  const error = localError ?? urlError;
  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-sm text-center">
        <h1 className="text-2xl font-bold text-indigo-600">TaskFlow</h1>
        <p className="mt-2 text-sm text-slate-600">Create tasks, assign them to teammates and get notified by email when work is done.</p>
        {error && <div role="alert" className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</div>}
        <Button className="mt-6 w-full" onClick={onClick} disabled={busy || loading}>
          {busy ? "Redirecting to Google..." : "Continue with Google"}
        </Button>
        <p className="mt-4 text-xs text-slate-500">We use Google to sign you in. We never see or store your Google password.</p>
      </Card>
    </main>
  );
}

export default function LoginPage() {
  return <Suspense><LoginContent /></Suspense>;
}
