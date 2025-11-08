"use client";

import { useAuth } from "@/lib/queries/auth";
import { useUserFavorites, useRemoveFavorite } from "@/lib/queries/user";
import { Heart, ShoppingCart, Trash2, Loader2 } from "lucide-react";
import Link from "next/link";
import { useTrackInteraction } from "@/lib/queries/feedback";
import { InteractionType } from "@/types/enums";

export default function FavoritesContent() {
  const { user } = useAuth();
  const { data: favorites, isLoading } = useUserFavorites();
  const removeFavorite = useRemoveFavorite();
  const feedbackMutation = useTrackInteraction();

  const handleRemoveFavorite = (productId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    removeFavorite.mutate(productId);
  };

  const handleAddToCart = (productId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!user?.id) return;
    feedbackMutation.mutate({
      user_id: user.id,
      product_id: productId,
      interaction_type: InteractionType.ADD_TO_CART,
      context: "profile_favorites",
    });
  };

  const handleClick = (productId: string) => {
    if (!user?.id) return;
    feedbackMutation.mutate({
      user_id: user.id,
      product_id: productId,
      interaction_type: InteractionType.CLICK,
      context: "profile_favorites",
    });
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-2xl shadow-sm border border-light-gray p-12 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-pinterest-red animate-spin" />
      </div>
    );
  }

  if (!favorites || favorites.total === 0) {
    return (
      <div className="bg-white rounded-2xl shadow-sm border border-light-gray p-12 text-center">
        <Heart className="w-16 h-16 text-gray/30 mx-auto mb-4" />
        <h2 className="text-2xl font-semibold text-charcoal mb-2">
          No favorites yet
        </h2>
        <p className="text-gray mb-6">
          Start adding products to your favorites by clicking the heart icon
        </p>
        <Link
          href="/"
          className="inline-block px-6 py-3 bg-pinterest-red text-white rounded-full hover:bg-dark-red transition-colors"
        >
          Discover Products
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-white rounded-2xl shadow-sm border border-light-gray p-6">
        <p className="text-gray">
          {favorites.total} {favorites.total === 1 ? "item" : "items"} saved
        </p>
      </div>

      {/* Favorites Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {favorites.favorites.map((product) => (
          <Link
            key={product.product_id}
            href={`/products/${product.product_id}`}
            onClick={() => handleClick(product.product_id)}
            className="group relative bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-xl transition-all duration-300 border border-light-gray"
          >
            {/* Image */}
            <div className="relative aspect-[3/4] overflow-hidden bg-light-gray">
              {product.image_url ? (
                <img
                  src={product.image_url}
                  alt={product.title}
                  className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                  loading="lazy"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-gray">
                  No image
                </div>
              )}

              {/* Remove Button */}
              <button
                onClick={(e) => handleRemoveFavorite(product.product_id, e)}
                disabled={removeFavorite.isPending}
                className="absolute top-3 right-3 p-2.5 bg-white/90 backdrop-blur-sm rounded-full hover:bg-white transition-colors shadow-lg active:scale-95"
                aria-label="Remove from favorites"
              >
                <Trash2 className="w-5 h-5 text-red-500" />
              </button>

              {/* Overlay Actions */}
              <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/0 to-black/0 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                <div className="absolute bottom-4 left-4 right-4 flex justify-between items-end">
                  {/* Price */}
                  <div className="text-white">
                    <p className="text-2xl font-bold">
                      {product.currency}
                      {product.price.toFixed(2)}
                    </p>
                  </div>

                  {/* Add to Cart Button */}
                  <button
                    onClick={(e) => handleAddToCart(product.product_id, e)}
                    disabled={!product.in_stock}
                    className="p-2.5 bg-white/90 backdrop-blur-sm rounded-full hover:bg-white transition-colors disabled:opacity-50 active:scale-95"
                    aria-label="Add to cart"
                  >
                    <ShoppingCart
                      className={`w-5 h-5 ${
                        product.in_stock ? "text-pinterest-red" : "text-gray-400"
                      }`}
                    />
                  </button>
                </div>
              </div>

              {/* Stock Badge */}
              {!product.in_stock && (
                <div className="absolute top-3 left-3">
                  <span className="px-3 py-1 text-xs font-semibold bg-red-500 text-white rounded-full">
                    Out of Stock
                  </span>
                </div>
              )}
            </div>

            {/* Product Info */}
            <div className="p-4">
              {/* Brand */}
              {product.brand && (
                <p className="text-xs text-gray uppercase tracking-wide mb-1 font-medium">
                  {product.brand}
                </p>
              )}

              {/* Title */}
              <h3 className="text-sm font-semibold text-charcoal line-clamp-2 mb-2 group-hover:text-pinterest-red transition-colors">
                {product.title}
              </h3>

              {/* Liked At */}
              <p className="text-xs text-gray/60">
                Added {new Date(product.liked_at).toLocaleDateString()}
              </p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
