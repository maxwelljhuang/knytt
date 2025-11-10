"use client";

import { useState, useEffect } from "react";
import { useInView } from "react-intersection-observer";
import { SearchBar } from "@/components/search";
import { ProductGrid } from "@/components/products";
import { useInfiniteSearch } from "@/lib/queries/search";
import { useAuth } from "@/lib/queries/auth";

// Force dynamic rendering for search page
export const dynamic = "force-dynamic";

export default function SearchPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [hasSearched, setHasSearched] = useState(false);
  const { user } = useAuth();
  const userId = user?.id ? Number(user.id) : undefined;
  const { ref: loadMoreRef, inView } = useInView({
    threshold: 0,
  });

  // Use infinite search hook for pagination
  const {
    data,
    isLoading,
    error,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteSearch(
    {
      query: searchQuery,
      limit: 20,
    },
    {
      enabled: hasSearched && searchQuery.length > 0,
    }
  );

  // Auto-fetch next page when in view
  useEffect(() => {
    if (inView && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [inView, hasNextPage, isFetchingNextPage, fetchNextPage]);

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    setHasSearched(true);
  };

  // Flatten all pages into single array
  const allProducts = (data as any)?.pages?.flatMap((page: any) => page.results) ?? [];
  const totalResults = (data as any)?.pages?.[0]?.total ?? 0;
  const searchTime = (data as any)?.pages?.[0]?.search_time_ms ?? 0;
  const isPersonalized = (data as any)?.pages?.[0]?.personalized ?? false;

  return (
    <div className="min-h-screen bg-ivory">
      {/* Search Header */}
      <section className="bg-gradient-to-br from-white via-light-gray to-pinterest-red/5 border-b border-light-gray">
        <div className="container mx-auto px-4 py-8">
          <h1 className="text-4xl font-bold text-charcoal mb-6">
            Search Products
          </h1>
          <SearchBar
            onSearch={handleSearch}
            isLoading={isLoading}
            className="max-w-3xl"
          />
        </div>
      </section>

      {/* Results */}
      <main className="container mx-auto px-4 py-8">
        {/* Loading State */}
        {isLoading && (
          <div className="text-center py-12">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-pinterest-red border-r-transparent"></div>
            <p className="mt-4 text-gray">Searching...</p>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="bg-red-50 border-2 border-red-200 rounded-lg p-6 text-center">
            <p className="text-red-600 font-medium">
              Error: {error.message}
            </p>
          </div>
        )}

        {/* Empty State - Before Search */}
        {!hasSearched && !isLoading && (
          <div className="text-center py-12">
            <p className="text-gray text-lg">
              Enter a search query to find products
            </p>
          </div>
        )}

        {/* No Results */}
        {hasSearched && !isLoading && !error && allProducts.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray text-lg">
              No products found for &quot;{searchQuery}&quot;
            </p>
          </div>
        )}

        {/* Results */}
        {allProducts.length > 0 && (
          <div>
            <div className="mb-6">
              <p className="text-gray">
                Found {totalResults} results in {searchTime.toFixed(0)}ms
                {isPersonalized && " (personalized)"}
              </p>
            </div>

            <ProductGrid
              products={allProducts}
              userId={userId}
              columns={4}
              onProductClick={(productId) => {
                console.log("Product clicked:", productId);
              }}
            />

            {/* Load More Trigger */}
            {hasNextPage && (
              <div ref={loadMoreRef} className="py-8 text-center">
                {isFetchingNextPage ? (
                  <div className="inline-block">
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-solid border-pinterest-red border-r-transparent"></div>
                    <p className="mt-2 text-gray text-sm">Loading more...</p>
                  </div>
                ) : (
                  <button
                    onClick={() => fetchNextPage()}
                    className="px-6 py-3 bg-pinterest-red text-white rounded-full hover:bg-dark-red transition-colors"
                  >
                    Load More
                  </button>
                )}
              </div>
            )}

            {/* End of Results */}
            {!hasNextPage && allProducts.length > 0 && (
              <div className="py-8 text-center">
                <p className="text-gray text-sm">
                  You've reached the end of the results
                </p>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
