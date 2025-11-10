"use client";

import { Suspense } from "react";
import SearchContent from "./SearchContent";

// Force dynamic rendering for search page
export const dynamic = "force-dynamic";

export default function SearchPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-ivory flex items-center justify-center">
          <div className="text-center">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-pinterest-red border-r-transparent"></div>
            <p className="mt-4 text-gray">Loading search...</p>
          </div>
        </div>
      }
    >
      <SearchContent />
    </Suspense>
  );
}
