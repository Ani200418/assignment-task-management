"use client";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import type { Session } from "@supabase/supabase-js";
import { getSupabase } from "@/lib/supabase";
import { rememberRedirect } from "@/lib/safeRedirect";
import { api, setUnauthorizedHandler } from "@/services/api";
import type { Profile } from "@/types/api";

interface AuthContextValue {
  loading: boolean;
  session: Session | null;
  profile: Profile | null;
  signInWithGoogle: (next?: string) => Promise<void>;
  signOut: () => Promise<void>;
}
const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [{ loading, session }, setAuth] = useState<{ loading: boolean; session: Session | null }>({ loading: true, session: null });
  const [loaded, setLoaded] = useState<{ userId: string; profile: Profile } | null>(null);

  // 1) Keep React in sync with the Supabase session (login, logout, silent token refresh).
  useEffect(() => {
    const supabase = getSupabase();
    supabase.auth.getSession().then(({ data }) => setAuth({ loading: false, session: data.session }));
    const { data } = supabase.auth.onAuthStateChange((_event, s) => setAuth({ loading: false, session: s }));
    return () => data.subscription.unsubscribe();
  }, []);

  // 2) If the API ever says "401", the session is dead: clear it locally and send the user to login.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      void getSupabase().auth.signOut({ scope: "local" });
      router.replace("/login?error=session_expired");
    });
  }, [router]);

  // 3) Ask Flask who we are. This also creates the profile row on very first login if needed.
  const userId = session?.user.id ?? null;
  useEffect(() => {
    if (!userId) return;
    let cancelled = false;
    api.me().then((r) => { if (!cancelled) setLoaded({ userId, profile: r.user }); }).catch(() => {});
    return () => { cancelled = true; };
  }, [userId]);

  const signInWithGoogle = useCallback(async (next?: string) => {
    if (next) rememberRedirect(next);
    const { error } = await getSupabase().auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    });
    if (error) throw error;
  }, []);

  const signOut = useCallback(async () => {
    await getSupabase().auth.signOut();
    router.replace("/login");
  }, [router]);

  const profile = loaded && loaded.userId === userId ? loaded.profile : null;
  const value = useMemo(() => ({ loading, session, profile, signInWithGoogle, signOut }), [loading, session, profile, signInWithGoogle, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
