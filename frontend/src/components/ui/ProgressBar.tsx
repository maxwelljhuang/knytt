"use client";

import { useEffect, Suspense } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import NProgress from "nprogress";

// Configure NProgress
NProgress.configure({
  showSpinner: false,
  trickleSpeed: 200,
  minimum: 0.08,
});

function ProgressBarInner() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    // Route has changed, complete the progress
    NProgress.done();
  }, [pathname, searchParams]);

  useEffect(() => {
    // Listen for route changes
    const handleStart = () => NProgress.start();

    // Add event listeners for browser navigation
    window.addEventListener("popstate", handleStart);

    return () => {
      window.removeEventListener("popstate", handleStart);
      NProgress.done();
    };
  }, []);

  return null;
}

/**
 * Progress bar that shows at the top during route transitions.
 * Automatically starts when the route changes and completes when navigation finishes.
 */
export function ProgressBar() {
  return (
    <Suspense fallback={null}>
      <ProgressBarInner />
    </Suspense>
  );
}
