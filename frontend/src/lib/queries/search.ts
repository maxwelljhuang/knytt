/**
 * Search Query Hooks
 */

import {
  useQuery,
  useInfiniteQuery,
  UseQueryOptions,
  UseInfiniteQueryOptions,
} from "@tanstack/react-query";
import { SearchRequest, SearchResponse } from "@/types/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

/**
 * Hook to search for products
 */
export function useSearch(
  request: SearchRequest,
  options?: Omit<UseQueryOptions<SearchResponse>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: ["search", request],
    queryFn: async (): Promise<SearchResponse> => {
      const response = await fetch(`${API_URL}/api/v1/search`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(request),
        credentials: "include",
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || "Search failed");
      }

      return response.json();
    },
    enabled: !!request.query, // Only run if query is not empty
    ...options,
  });
}

/**
 * Hook for infinite scroll search
 */
export function useInfiniteSearch(
  baseRequest: Omit<SearchRequest, "offset">,
  options?: Omit<
    UseInfiniteQueryOptions<SearchResponse>,
    "queryKey" | "queryFn" | "initialPageParam" | "getNextPageParam"
  >
) {
  return useInfiniteQuery({
    queryKey: ["search", "infinite", baseRequest],
    queryFn: async ({ pageParam = 0 }): Promise<SearchResponse> => {
      const request: SearchRequest = {
        ...baseRequest,
        offset: pageParam,
      };

      const response = await fetch(`${API_URL}/api/v1/search`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(request),
        credentials: "include",
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || "Search failed");
      }

      return response.json();
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage) => {
      const nextOffset = lastPage.offset + lastPage.limit;
      return nextOffset < lastPage.total ? nextOffset : undefined;
    },
    enabled: !!baseRequest.query,
    ...options,
  });
}
