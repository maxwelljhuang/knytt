"use client";

import { useState } from "react";
import { Heart, ShoppingCart, Check } from "lucide-react";
import { useTrackInteraction } from "@/lib/queries/feedback";
import { InteractionType } from "@/types/enums";

interface ProductActionsProps {
  productId: string;
  userId?: number;
  inStock: boolean;
}

export function ProductActions({
  productId,
  userId,
  inStock,
}: ProductActionsProps) {
  const [isLiked, setIsLiked] = useState(false);
  const [isAddedToCart, setIsAddedToCart] = useState(false);
  const feedbackMutation = useTrackInteraction();

  const handleLike = () => {
    if (!userId) return; // Skip if not authenticated
    setIsLiked(!isLiked);
    feedbackMutation.mutate({
      user_id: String(userId),
      product_id: productId,
      interaction_type: InteractionType.LIKE,
    });
  };

  const handleAddToCart = () => {
    if (!inStock) return;
    if (!userId) return; // Skip if not authenticated

    setIsAddedToCart(true);
    feedbackMutation.mutate({
      user_id: String(userId),
      product_id: productId,
      interaction_type: InteractionType.ADD_TO_CART,
    });

    // Reset after 3 seconds
    setTimeout(() => {
      setIsAddedToCart(false);
    }, 3000);
  };

  return (
    <div className="space-y-3">
      {/* Add to Cart Button */}
      <button
        onClick={handleAddToCart}
        disabled={!inStock}
        className={`w-full px-6 py-4 rounded-full font-semibold text-lg transition-all shadow-lg ${
          !inStock
            ? "bg-gray-300 text-gray-500 cursor-not-allowed"
            : isAddedToCart
            ? "bg-green-600 text-white"
            : "bg-gradient-to-r from-sage to-evergreen text-white hover:shadow-xl hover:scale-105"
        }`}
      >
        <span className="flex items-center justify-center gap-2">
          {isAddedToCart ? (
            <>
              <Check className="w-6 h-6" />
              <span>Added to Cart</span>
            </>
          ) : (
            <>
              <ShoppingCart className="w-6 h-6" />
              <span>{inStock ? "Add to Cart" : "Out of Stock"}</span>
            </>
          )}
        </span>
      </button>

      {/* Like Button */}
      <button
        onClick={handleLike}
        className={`w-full px-6 py-4 rounded-full font-semibold text-lg border-2 transition-all ${
          isLiked
            ? "border-terracotta bg-terracotta/10 text-terracotta"
            : "border-blush bg-white text-evergreen hover:border-sage hover:text-sage"
        }`}
      >
        <span className="flex items-center justify-center gap-2">
          <Heart
            className={`w-6 h-6 transition-all ${
              isLiked ? "fill-terracotta" : ""
            }`}
          />
          <span>{isLiked ? "Saved to Favorites" : "Add to Favorites"}</span>
        </span>
      </button>

      {/* Additional Info */}
      <div className="text-center">
        <p className="text-xs text-evergreen/60">
          Free returns within 30 days • Secure checkout
        </p>
      </div>
    </div>
  );
}
