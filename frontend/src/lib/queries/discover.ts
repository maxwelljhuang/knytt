/**
 * Discover Query Hooks
 * Simple product discovery without ML dependencies
 */

import { useQuery, UseQueryOptions } from "@tanstack/react-query";
import { SearchResponse } from "@/types/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export interface DiscoverParams {
  limit?: number;
  offset?: number;
  sort_by?: "popular" | "recent" | "price_low" | "price_high";
  min_price?: number;
  max_price?: number;
}

/**
 * Hook to discover products using simple database queries (no ML required)
 */
export function useDiscover(
  params: DiscoverParams = {},
  options?: Omit<UseQueryOptions<SearchResponse>, "queryKey" | "queryFn">
) {
  const {
    limit = 20,
    offset = 0,
    sort_by = "popular",
    min_price,
    max_price,
  } = params;

  return useQuery({
    queryKey: ["discover", params],
    queryFn: async (): Promise<SearchResponse> => {
      const searchParams = new URLSearchParams({
        limit: limit.toString(),
        offset: offset.toString(),
        sort_by,
      });

      if (min_price !== undefined) {
        searchParams.append("min_price", min_price.toString());
      }
      if (max_price !== undefined) {
        searchParams.append("max_price", max_price.toString());
      }

      const response = await fetch(
        `${API_URL}/api/v1/discover?${searchParams.toString()}`,
        {
          method: "GET",
          credentials: "include",
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to discover products");
      }

      return response.json();
    },
    ...options,
  });
}
