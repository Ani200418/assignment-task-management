"use client";
import { useEffect, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { rememberRedirect } from "@/lib/safeRedirect";
import { Skeleton } from "./ui";

/**
 * Client-side route guard: it is for USER EXPERIENCE only. Real protection is Flask rejecting
 * every request without a valid token, so hiding a page here never exposes data.
 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { loading, session } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !session) {
      rememberRedirect(pathname);
      router.replace("/login");
    }
  }, [loading, session, pathname, router]);

  if (loading || !session) {
    return (
      <div className="mx-auto w-full max-w-4xl space-y-4 p-6" aria-busy="true" aria-label="Loading">
        <Skeleton className="h-8 w-48" /><Skeleton className="h-24 w-full" /><Skeleton className="h-24 w-full" />
      </div>
    );
  }
  return <>{children}</>;
}
