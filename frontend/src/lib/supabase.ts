import { createClient, type SupabaseClient } from "@supabase/supabase-js";

let client: SupabaseClient | null = null;

/**
 * Browser Supabase client. It uses the PUBLISHABLE (public) key only - that key is safe in the browser.
 * The privileged service-role key must never appear anywhere in this folder.
 * Created lazily so a missing variable gives a clear error when used, not at import time.
 */
export function getSupabase(): SupabaseClient {
  if (!client) {
    const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
    if (!url || !key) {
      throw new Error("Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY (see .env.example)");
    }
    client = createClient(url, key, { auth: { flowType: "pkce", persistSession: true, autoRefreshToken: true } });
  }
  return client;
}
