import { Suspense, type ReactNode } from "react";
import { AppShell } from "@/components/AppShell";
import { RequireAuth } from "@/components/RequireAuth";
import { Skeleton } from "@/components/ui";

function PageFallback() {
  return (
    <div className="mx-auto w-full max-w-4xl space-y-4 p-6" aria-busy="true" aria-label="Loading">
      <Skeleton className="h-8 w-48" /><Skeleton className="h-24 w-full" /><Skeleton className="h-24 w-full" />
    </div>
  );
}

// Every page inside the (app) folder is protected and wrapped in the navigation shell.
// Suspense: the shell reads the current URL (a runtime-only value), which Next must stream in after prerendering.
export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <Suspense fallback={<PageFallback />}>
      <RequireAuth><AppShell>{children}</AppShell></RequireAuth>
    </Suspense>
  );
}
