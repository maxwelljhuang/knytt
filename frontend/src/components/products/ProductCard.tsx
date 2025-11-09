"use client";

import { useState } from "react";
import Image from "next/image";
import { Heart, ShoppingCart } from "lucide-react";
import { ProductResult } from "@/types/api";
import { InteractionType } from "@/types/enums";
import { useTrackInteraction } from "@/lib/queries/feedback";
import { useCartStore } from "@/lib/stores/cartStore";
import { useToast } from "@/components/ui/Toast";
import Tooltip from "@/components/ui/Tooltip";

interface ProductCardProps {
  product: ProductResult;
  userId?: number;
  onProductClick?: (productId: string) => void;
}

export function ProductCard({ product, userId, onProductClick }: ProductCardProps) {
  const [isLiked, setIsLiked] = useState(false);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);
  const [justLiked, setJustLiked] = useState(false);
  const feedbackMutation = useTrackInteraction();
  const addToCart = useCartStore((state) => state.addItem);
  const toast = useToast();

  const handleLike = (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent card click

    if (!userId) {
      toast.warning("Please login to like products");
      return;
    }

    const newLikedState = !isLiked;
    setIsLiked(newLikedState);

    // Trigger heart animation
    if (newLikedState) {
      setJustLiked(true);
      setTimeout(() => setJustLiked(false), 300);
      toast.success("Added to favorites");
    } else {
      toast.info("Removed from favorites");
    }

    feedbackMutation.mutate({
      user_id: userId,
      product_id: product.product_id,
      interaction_type: InteractionType.LIKE,
    });
  };

  const handleAddToCart = (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent card click

    if (!userId) {
      toast.warning("Please login to add to cart");
      return;
    }

    if (!product.in_stock) {
      toast.error("This product is out of stock");
      return;
    }

    // Optimistically add to cart store
    addToCart({
      productId: product.product_id,
      title: product.title,
      price: product.price || 0,
      currency: product.currency || "$",
      imageUrl: product.image_url,
    });

    // Track interaction in background
    feedbackMutation.mutate({
      user_id: userId,
      product_id: product.product_id,
      interaction_type: InteractionType.ADD_TO_CART,
    });

    toast.success("Added to cart", product.title);
  };

  const handleCardClick = () => {
    if (userId) {
      feedbackMutation.mutate({
        user_id: userId,
        product_id: product.product_id,
        interaction_type: InteractionType.CLICK,
      });
    }

    if (onProductClick) {
      onProductClick(product.product_id);
    }
  };

  const formatPrice = () => {
    if (!product.price) return "Price not available";
    return `${product.currency || "$"}${product.price.toFixed(2)}`;
  };

  // Don't render card if image failed to load
  if (imageError) {
    return null;
  }

  return (
    <div
      onClick={handleCardClick}
      className="group relative bg-white border-2 border-light-gray rounded-xl overflow-hidden hover:border-pinterest-red/30 transition-all duration-[var(--duration-slow)] cursor-pointer hover:shadow-xl shadow-md active:scale-[0.98]"
    >
      {/* Product Image */}
      <div className="relative aspect-square bg-light-gray/50 overflow-hidden">
        {!imageLoaded && (
          <div className="absolute inset-0 bg-light-gray animate-shimmer" />
        )}
        <Image
          src={product.image_url!}
          alt={product.title}
          fill
          sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
          className={`object-cover group-hover:scale-110 transition-all duration-[var(--duration-slower)] ${
            imageLoaded ? 'opacity-100' : 'opacity-0'
          }`}
          loading="lazy"
          onLoad={() => setImageLoaded(true)}
          onError={() => setImageError(true)}
        />

        {/* Like Button Overlay */}
        <Tooltip content={isLiked ? "Unlike" : "Like"}>
          <button
            onClick={handleLike}
            className={`absolute top-3 right-3 p-2.5 rounded-full glass shadow-lg hover:shadow-xl transition-all duration-[var(--duration-fast)] active:scale-95 z-10 ${
              isLiked ? "text-pinterest-red bg-white" : "text-charcoal/70 hover:text-pinterest-red bg-white"
            } ${justLiked ? "animate-heart-pop" : ""}`}
            aria-label={isLiked ? "Unlike product" : "Like product"}
          >
            <Heart
              className={`h-5 w-5 transition-all ${isLiked ? "fill-current scale-110" : ""}`}
            />
          </button>
        </Tooltip>

        {/* Stock Badge */}
        {product.in_stock !== undefined && (
          <div className="absolute bottom-3 left-3">
            {product.in_stock ? (
              <span className="px-3 py-1.5 text-xs font-semibold bg-green-500 text-white rounded-full shadow-md">
                In Stock
              </span>
            ) : (
              <span className="px-3 py-1.5 text-xs font-semibold bg-red-500 text-white rounded-full shadow-md">
                Out of Stock
              </span>
            )}
          </div>
        )}
      </div>

      {/* Product Info */}
      <div className="p-4">
        {/* Brand */}
        {product.brand && (
          <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">
            {product.brand}
          </p>
        )}

        {/* Title */}
        <h3 className="text-base font-bold text-charcoal mb-2 line-clamp-2 group-hover:text-pinterest-red transition-colors duration-[var(--duration-fast)]">
          {product.title}
        </h3>

        {/* Description */}
        {product.description && (
          <p className="text-xs text-muted-foreground mb-3 line-clamp-2">
            {product.description}
          </p>
        )}

        {/* Rating */}
        {product.rating && product.rating > 0 && (
          <div className="flex items-center gap-1 mb-2">
            <div className="flex">
              {[...Array(5)].map((_, i) => (
                <span
                  key={i}
                  className={`text-xs ${
                    i < Math.round(product.rating!)
                      ? "text-yellow-400"
                      : "text-muted"
                  }`}
                >
                  ★
                </span>
              ))}
            </div>
            {product.review_count && product.review_count > 0 && (
              <span className="text-xs text-muted-foreground">
                ({product.review_count})
              </span>
            )}
          </div>
        )}

        {/* Price and Cart Button */}
        <div className="flex items-center justify-between mt-4">
          <div className="flex flex-col">
            <span className="text-xl font-bold text-pinterest-red">
              {formatPrice()}
            </span>
            {product.quality_score && product.quality_score < 1 && (
              <span className="text-xs text-gray">
                Quality: {(product.quality_score * 100).toFixed(0)}%
              </span>
            )}
          </div>

          <Tooltip content={product.in_stock ? "Add to cart" : "Out of stock"}>
            <button
              onClick={handleAddToCart}
              disabled={!product.in_stock}
              className={`p-3 rounded-full transition-all duration-[var(--duration-fast)] shadow-md hover:shadow-lg active:scale-95 ${
                product.in_stock
                  ? "bg-pinterest-red text-white hover:bg-dark-red"
                  : "bg-light-gray text-gray cursor-not-allowed"
              }`}
              aria-label="Add to cart"
            >
              <ShoppingCart className="h-5 w-5" />
            </button>
          </Tooltip>
        </div>

        {/* Relevance Score (for debugging/demo) */}
        {product.final_score && (
          <div className="mt-2 pt-2 border-t border-border">
            <span className="text-xs text-muted-foreground">
              Match: {(product.final_score * 100).toFixed(1)}%
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
