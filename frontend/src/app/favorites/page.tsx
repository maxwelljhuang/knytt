"use client";

import { useAuth } from "@/lib/queries/auth";
import { useFavorites, useRemoveFavorite } from "@/lib/queries/user";
import { Heart, ShoppingCart, Trash2, Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTrackInteraction } from "@/lib/queries/feedback";
import { InteractionType } from "@/types/enums";

export default function FavoritesPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const userId = user?.id;
  const { data: favorites, isLoading: favoritesLoading } = useFavorites(
    userId ? Number(userId) : undefined
  );
  const removeFavorite = useRemoveFavorite();
  const feedbackMutation = useTrackInteraction();

  // Redirect to login if not authenticated
  if (!authLoading && !isAuthenticated) {
    router.push("/login?redirect=/favorites");
    return null;
  }

  const handleRemoveFavorite = (productId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!userId) return;
    removeFavorite.mutate({ userId: Number(userId), productId });
  };

  const handleAddToCart = (productId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!userId) return;
    feedbackMutation.mutate({
      user_id: userId,
      product_id: productId,
      interaction_type: InteractionType.ADD_TO_CART,
      context: "favorites",
    });
  };

  const handleClick = (productId: string) => {
    if (!userId) return;
    feedbackMutation.mutate({
      user_id: userId,
      product_id: productId,
      interaction_type: InteractionType.CLICK,
      context: "favorites",
    });
  };

  if (authLoading || favoritesLoading) {
    return (
      <div className="min-h-screen bg-ivory">
        <div className="container mx-auto px-4 py-12">
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 text-sage animate-spin" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-ivory">
      <div className="container mx-auto px-4 py-12">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <Heart className="w-8 h-8 text-terracotta fill-terracotta" />
            <h1 className="text-4xl font-bold text-evergreen">My Favorites</h1>
          </div>
          <p className="text-sage">
            {favorites?.total || 0} {favorites?.total === 1 ? "item" : "items"} saved
          </p>
        </div>

        {/* Empty State */}
        {(!favorites || favorites.total === 0) && (
          <div className="text-center py-20">
            <Heart className="w-16 h-16 text-sage/30 mx-auto mb-4" />
            <h2 className="text-2xl font-semibold text-evergreen mb-2">
              No favorites yet
            </h2>
            <p className="text-sage mb-6">
              Start adding products to your favorites by clicking the heart icon
            </p>
            <Link
              href="/"
              className="inline-block px-6 py-3 bg-terracotta text-white rounded-full hover:bg-terracotta/90 transition-colors"
            >
              Discover Products
            </Link>
          </div>
        )}

        {/* Favorites Grid */}
        {favorites && favorites.total > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {favorites.favorites.map((product) => (
              <Link
                key={product.product_id}
                href={`/products/${product.product_id}`}
                onClick={() => handleClick(product.product_id)}
                className="group relative bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-xl transition-all duration-300"
              >
                {/* Image */}
                <div className="relative aspect-[3/4] overflow-hidden bg-blush">
                  {product.image_url ? (
                    <img
                      src={product.image_url}
                      alt={product.title}
                      className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                      loading="lazy"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-sage">
                      No image
                    </div>
                  )}

                  {/* Remove Button */}
                  <button
                    onClick={(e) => handleRemoveFavorite(product.product_id, e)}
                    disabled={removeFavorite.isPending}
                    className="absolute top-3 right-3 p-2.5 bg-white/90 backdrop-blur-sm rounded-full hover:bg-white transition-colors shadow-lg"
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
                        className="p-2.5 bg-white/90 backdrop-blur-sm rounded-full hover:bg-white transition-colors disabled:opacity-50"
                        aria-label="Add to cart"
                      >
                        <ShoppingCart
                          className={`w-5 h-5 ${
                            product.in_stock ? "text-sage" : "text-gray-400"
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
                    <p className="text-xs text-sage uppercase tracking-wide mb-1 font-medium">
                      {product.brand}
                    </p>
                  )}

                  {/* Title */}
                  <h3 className="text-sm font-semibold text-evergreen line-clamp-2 mb-2 group-hover:text-sage transition-colors">
                    {product.title}
                  </h3>

                  {/* Liked At */}
                  <p className="text-xs text-sage/60">
                    Added {new Date(product.liked_at).toLocaleDateString()}
                  </p>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
