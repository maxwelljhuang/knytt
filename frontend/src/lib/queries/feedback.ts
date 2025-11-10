/**
 * Feedback Query Hooks
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FeedbackRequest, FeedbackResponse } from "@/types/api";
import { InteractionType } from "@/types/enums";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

/**
 * Hook to track user interactions with products
 */
export function useTrackInteraction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (
      request: FeedbackRequest
    ): Promise<FeedbackResponse> => {
      const response = await fetch(`${API_URL}/api/v1/feedback`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(request),
        credentials: "include",
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || "Failed to track interaction");
      }

      return response.json();
    },
    onSuccess: (data) => {
      // Invalidate relevant queries
      if (data.embeddings_updated) {
        queryClient.invalidateQueries({
          queryKey: ["recommendations", "feed", data.user_id],
        });
      }

      // Invalidate favorites if it's a like/unlike interaction
      if (data.interaction_type === "like" || data.interaction_type === "unlike") {
        queryClient.invalidateQueries({
          queryKey: ["user", "favorites", data.user_id],
        });
      }

      // Invalidate history
      queryClient.invalidateQueries({
        queryKey: ["user", "history", data.user_id],
      });
    },
  });
}

/**
 * Helper to track a view interaction
 */
export function useTrackView() {
  const trackInteraction = useTrackInteraction();

  return (userId: number, productId: string, context?: string) => {
    return trackInteraction.mutate({
      user_id: String(userId),
      product_id: productId,
      interaction_type: InteractionType.VIEW,
      context,
      update_embeddings: false, // Don't update embeddings for views
      update_session: true,
    });
  };
}

/**
 * Helper to track a click interaction
 */
export function useTrackClick() {
  const trackInteraction = useTrackInteraction();

  return (userId: number, productId: string, context?: string, position?: number) => {
    return trackInteraction.mutate({
      user_id: String(userId),
      product_id: productId,
      interaction_type: InteractionType.CLICK,
      context,
      position,
      update_embeddings: true,
      update_session: true,
    });
  };
}

/**
 * Helper to track a like interaction
 */
export function useTrackLike() {
  const trackInteraction = useTrackInteraction();

  return (userId: number, productId: string, context?: string) => {
    return trackInteraction.mutate({
      user_id: String(userId),
      product_id: productId,
      interaction_type: InteractionType.LIKE,
      context,
      update_embeddings: true,
      update_session: true,
    });
  };
}
