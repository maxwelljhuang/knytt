"use client";

import { useState, useRef, useEffect } from "react";
import Image from "next/image";
import { ProductResult } from "@/types/api";
import { Heart, ShoppingCart, ChevronLeft, ChevronRight } from "lucide-react";
import { useTrackInteraction } from "@/lib/queries/feedback";
import { InteractionType } from "@/types/enums";
import Link from "next/link";

interface CarouselCardProps {
  product: ProductResult;
  userId?: number;
  context: string;
  onLike: (productId: string, e: React.MouseEvent) => void;
  onAddToCart: (productId: string, e: React.MouseEvent) => void;
  onClick: (productId: string) => void;
}

function CarouselCard({ product, userId, context, onLike, onAddToCart, onClick }: CarouselCardProps) {
  const [imageError, setImageError] = useState(false);

  // Don't render card if image failed to load
  if (imageError) {
    return null;
  }

  return (
    <Link
      href={`/products/${product.product_id}`}
      onClick={() => onClick(product.product_id)}
      className="flex-none w-64 group relative bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-xl transition-all duration-300 cursor-pointer"
    >
      {/* Image */}
      <div className="relative aspect-[3/4] overflow-hidden bg-blush">
        <Image
          src={product.image_url!}
          alt={product.title}
          fill
          sizes="256px"
          className="object-cover group-hover:scale-110 transition-transform duration-500"
          loading="lazy"
          onError={() => setImageError(true)}
        />

        {/* Overlay Actions */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/0 to-black/0 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
          <div className="absolute bottom-4 left-4 right-4 flex justify-between items-end">
            {/* Price */}
            <div className="text-white">
              <p className="text-xl font-bold">
                {product.currency || "$"}
                {product.price?.toFixed(2) || "0.00"}
              </p>
              {product.rrp_price && product.rrp_price > product.price && (
                <p className="text-sm line-through opacity-75">
                  {product.currency || "$"}
                  {product.rrp_price.toFixed(2)}
                </p>
              )}
            </div>

            {/* Action Buttons */}
            <div className="flex gap-2">
              <button
                onClick={(e) => onLike(product.product_id, e)}
                className="p-2 bg-white/90 backdrop-blur-sm rounded-full hover:bg-white transition-colors"
                aria-label="Like product"
              >
                <Heart className="w-4 h-4 text-terracotta" />
              </button>
              <button
                onClick={(e) => onAddToCart(product.product_id, e)}
                className="p-2 bg-white/90 backdrop-blur-sm rounded-full hover:bg-white transition-colors"
                disabled={!product.in_stock}
                aria-label="Add to cart"
              >
                <ShoppingCart
                  className={`w-4 h-4 ${
                    product.in_stock ? "text-sage" : "text-gray-400"
                  }`}
                />
              </button>
            </div>
          </div>
        </div>

        {/* Stock Badge */}
        {!product.in_stock && (
          <div className="absolute top-3 left-3">
            <span className="px-2 py-1 text-xs font-semibold bg-red-500 text-white rounded-full">
              Out of Stock
            </span>
          </div>
        )}
      </div>

      {/* Product Info */}
      <div className="p-4">
        {/* Brand */}
        {product.brand && (
          <p className="text-xs text-sage uppercase tracking-wide mb-1 font-medium">
            {product.brand}
          </p>
        )}

        {/* Title */}
        <h3 className="text-sm font-semibold text-evergreen line-clamp-2 group-hover:text-sage transition-colors">
          {product.title}
        </h3>
      </div>
    </Link>
  );
}

interface RecommendationCarouselProps {
  title: string;
  products: ProductResult[];
  userId?: number;
  context?: string;
  isLoading?: boolean;
}

export function RecommendationCarousel({
  title,
  products,
  userId,
  context = "recommendation",
  isLoading = false,
}: RecommendationCarouselProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);
  const feedbackMutation = useTrackInteraction();

  // Check scroll position
  const updateScrollButtons = () => {
    if (!scrollContainerRef.current) return;

    const { scrollLeft, scrollWidth, clientWidth } = scrollContainerRef.current;
    setCanScrollLeft(scrollLeft > 0);
    setCanScrollRight(scrollLeft < scrollWidth - clientWidth - 10);
  };

  useEffect(() => {
    updateScrollButtons();
    window.addEventListener("resize", updateScrollButtons);
    return () => window.removeEventListener("resize", updateScrollButtons);
  }, [products]);

  const scroll = (direction: "left" | "right") => {
    if (!scrollContainerRef.current) return;

    const scrollAmount = scrollContainerRef.current.clientWidth * 0.8;
    const newScrollPosition =
      scrollContainerRef.current.scrollLeft +
      (direction === "left" ? -scrollAmount : scrollAmount);

    scrollContainerRef.current.scrollTo({
      left: newScrollPosition,
      behavior: "smooth",
    });

    setTimeout(updateScrollButtons, 300);
  };

  const handleLike = (productId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!userId) return;
    feedbackMutation.mutate({
      user_id: String(userId),
      product_id: productId,
      interaction_type: InteractionType.LIKE,
      context,
    });
  };

  const handleAddToCart = (productId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!userId) return;
    feedbackMutation.mutate({
      user_id: String(userId),
      product_id: productId,
      interaction_type: InteractionType.ADD_TO_CART,
      context,
    });
  };

  const handleClick = (productId: string) => {
    if (!userId) return;
    feedbackMutation.mutate({
      user_id: String(userId),
      product_id: productId,
      interaction_type: InteractionType.CLICK,
      context,
    });
  };

  if (isLoading) {
    return (
      <div className="mb-12">
        <h2 className="text-2xl font-bold text-evergreen mb-6">{title}</h2>
        <div className="flex gap-4 overflow-hidden">
          {[...Array(5)].map((_, i) => (
            <div
              key={i}
              className="flex-none w-64 h-96 bg-blush rounded-2xl animate-pulse"
            />
          ))}
        </div>
      </div>
    );
  }

  // Filter out products without valid images (safety net)
  const validProducts = products?.filter(p => p.image_url?.trim()) || [];

  if (validProducts.length === 0) {
    return null;
  }

  return (
    <div className="mb-12 relative">
      {/* Title */}
      <h2 className="text-2xl font-bold text-evergreen mb-6">{title}</h2>

      {/* Scroll Buttons */}
      {canScrollLeft && (
        <button
          onClick={() => scroll("left")}
          className="absolute left-0 top-1/2 -translate-y-1/2 z-10 p-3 bg-white/90 backdrop-blur-sm rounded-full shadow-lg hover:bg-white transition-all"
          aria-label="Scroll left"
        >
          <ChevronLeft className="w-6 h-6 text-evergreen" />
        </button>
      )}

      {canScrollRight && (
        <button
          onClick={() => scroll("right")}
          className="absolute right-0 top-1/2 -translate-y-1/2 z-10 p-3 bg-white/90 backdrop-blur-sm rounded-full shadow-lg hover:bg-white transition-all"
          aria-label="Scroll right"
        >
          <ChevronRight className="w-6 h-6 text-evergreen" />
        </button>
      )}

      {/* Products Container */}
      <div
        ref={scrollContainerRef}
        onScroll={updateScrollButtons}
        className="flex gap-4 overflow-x-auto scrollbar-hide scroll-smooth"
        style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}
      >
        {validProducts.map((product) => (
          <CarouselCard
            key={product.product_id}
            product={product}
            userId={userId}
            context={context}
            onLike={handleLike}
            onAddToCart={handleAddToCart}
            onClick={handleClick}
          />
        ))}
      </div>

      {/* Hide scrollbar */}
      <style jsx>{`
        .scrollbar-hide::-webkit-scrollbar {
          display: none;
        }
      `}</style>
    </div>
  );
}
