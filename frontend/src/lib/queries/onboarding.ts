/**
 * Onboarding Query Hooks
 */

import { useQuery, useMutation, UseQueryOptions, UseMutationOptions } from "@tanstack/react-query";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

/**
 * Product for onboarding moodboard
 */
export interface OnboardingProduct {
  product_id: string;
  title: string;
  image_url: string | null;
  price: number;
  brand: string | null;
  category: string | null;
}

/**
 * Response from onboarding products endpoint
 */
export interface OnboardingProductsResponse {
  products: OnboardingProduct[];
  total: number;
}

/**
 * Request to complete onboarding
 */
export interface OnboardingCompleteRequest {
  selected_product_ids: string[];
  price_min: number | null;
  price_max: number | null;
}

/**
 * Response from complete onboarding endpoint
 */
export interface OnboardingCompleteResponse {
  success: boolean;
  user_id: string;
  onboarded: boolean;
  embedding_created: boolean;
  preferences_saved: boolean;
  selected_products_count: number;
  message: string;
  next_step: string;
  embedding_metadata?: {
    confidence: number;
    method: string;
    products_used: number;
  };
}

/**
 * Hook to get products for onboarding moodboard
 */
export function useOnboardingProducts(
  options?: Omit<UseQueryOptions<OnboardingProductsResponse>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: ["onboarding", "products"],
    queryFn: async (): Promise<OnboardingProductsResponse> => {
      const response = await fetch(
        `${API_URL}/api/v1/onboarding/products?limit=20&diverse=true`,
        {
          method: "GET",
          credentials: "include",
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || "Failed to load onboarding products");
      }

      return response.json();
    },
    staleTime: 1000 * 60 * 10, // 10 minutes
    ...options,
  });
}

/**
 * Hook to complete onboarding with style preferences
 */
export function useCompleteOnboarding(
  options?: Omit<
    UseMutationOptions<OnboardingCompleteResponse, Error, OnboardingCompleteRequest>,
    "mutationFn"
  >
) {
  return useMutation({
    mutationFn: async (
      request: OnboardingCompleteRequest
    ): Promise<OnboardingCompleteResponse> => {
      const response = await fetch(`${API_URL}/api/v1/onboarding/complete`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(request),
        credentials: "include",
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || error.message || "Failed to complete onboarding");
      }

      return response.json();
    },
    ...options,
  });
}
