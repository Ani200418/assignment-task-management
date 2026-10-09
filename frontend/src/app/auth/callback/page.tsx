"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getSupabase } from "@/lib/supabase";
import { consumeRedirect } from "@/lib/safeRedirect";

/** Google -> Supabase -> here. supabase-js trades the one-time code in the URL for a session. */
export default function AuthCallback() {
  const router = useRouter();
  useEffect(() => {
    const query = new URLSearchParams(window.location.search);
    const hash = new URLSearchParams(window.location.hash.slice(1));
    const oauthError = query.get("error") ?? hash.get("error");
    if (oauthError) {
      // access_denied = the user pressed "Cancel" on Google's consent screen
      router.replace(`/login?error=${oauthError === "access_denied" ? "cancelled" : "failed"}`);
      return;
    }
    getSupabase().auth.getSession().then(({ data }) => {
      router.replace(data.session ? consumeRedirect() : "/login?error=failed");
    }).catch(() => router.replace("/login?error=failed"));
  }, [router]);
  return <p className="p-8 text-center text-sm text-slate-600" role="status">Signing you in...</p>;
}
