/** Prevents "open redirect" attacks: only same-site relative paths are allowed after login. */
export const REDIRECT_KEY = "postLoginRedirect";

export function safeRedirectPath(value: string | null | undefined, fallback = "/dashboard"): string {
  if (!value || !value.startsWith("/")) return fallback; // must be a relative path
  if (value.startsWith("//") || value.startsWith("/\\")) return fallback; // "//evil.com" is protocol-relative
  if (/[\u0000-\u001f]/.test(value)) return fallback; // no control characters
  if (value.startsWith("/login") || value.startsWith("/auth")) return fallback; // avoid loops
  return value;
}

export function rememberRedirect(path: string) {
  try { sessionStorage.setItem(REDIRECT_KEY, path); } catch { /* storage may be blocked; fall back to dashboard */ }
}

export function consumeRedirect(): string {
  try {
    const value = sessionStorage.getItem(REDIRECT_KEY);
    sessionStorage.removeItem(REDIRECT_KEY);
    return safeRedirectPath(value);
  } catch { return "/dashboard"; }
}
