/**
 * Recommendations Query Hooks
 */

import { useQuery, UseQueryOptions } from "@tanstack/react-query";
import { RecommendRequest, RecommendResponse } from "@/types/api";
import { RecommendationContext } from "@/types/enums";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

/**
 * Hook to get personalized feed recommendations
 */
export function useFeed(
  userId: string | undefined,
  options?: Omit<UseQueryOptions<RecommendResponse>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: ["recommendations", "feed", userId],
    queryFn: async (): Promise<RecommendResponse> => {
      const request: RecommendRequest = {
        user_id: userId!,
        context: RecommendationContext.FEED,
        limit: 20,
      };

      const response = await fetch(`${API_URL}/api/v1/recommend`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(request),
        credentials: "include",
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || "Failed to load recommendations");
      }

      return response.json();
    },
    enabled: !!userId,
    staleTime: 1000 * 60 * 5, // 5 minutes
    ...options,
  });
}

/**
 * Hook to get similar product recommendations
 */
export function useSimilarProducts(
  productId: string | undefined,
  userId?: string,
  options?: Omit<UseQueryOptions<RecommendResponse>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: ["recommendations", "similar", productId, userId],
    queryFn: async (): Promise<RecommendResponse> => {
      const request: RecommendRequest = {
        user_id: userId!,
        context: RecommendationContext.SIMILAR,
        product_id: productId!,
        limit: 12,
      };

      const response = await fetch(`${API_URL}/api/v1/recommend`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(request),
        credentials: "include",
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || "Failed to load similar products");
      }

      return response.json();
    },
    enabled: !!productId && !!userId,
    staleTime: 1000 * 60 * 10, // 10 minutes
    ...options,
  });
}
