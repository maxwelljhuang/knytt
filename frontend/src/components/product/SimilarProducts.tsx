"use client";

import { useSimilarProducts } from "@/lib/queries/recommendations";
import { ProductCard } from "@/components/products";
import { Loader2, Sparkles } from "lucide-react";

interface SimilarProductsProps {
  productId: string;
  userId?: number;
}

export function SimilarProducts({ productId, userId }: SimilarProductsProps) {
  // Only fetch if userId is available
  const { data, isLoading, error } = useSimilarProducts(productId, userId, {
    limit: 12,
  });

  if (isLoading) {
    return (
      <section className="py-12">
        <div className="container mx-auto px-4">
          <h2 className="text-2xl md:text-3xl font-bold text-evergreen mb-8">
            You Might Also Like
          </h2>
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 text-sage animate-spin" />
          </div>
        </div>
      </section>
    );
  }

  if (error || !data || data.results.length === 0) {
    return null; // Don't show section if there's an error or no results
  }

  return (
    <section className="py-12 bg-gradient-to-br from-ivory via-blush/20 to-white">
      <div className="container mx-auto px-4">
        {/* Section Header */}
        <div className="flex items-center gap-3 mb-8">
          <div className="p-2 bg-gradient-to-br from-sage to-evergreen rounded-lg">
            <Sparkles className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="text-2xl md:text-3xl font-bold text-evergreen">
              You Might Also Like
            </h2>
            <p className="text-sm text-evergreen/60">
              Personalized recommendations based on this product
            </p>
          </div>
        </div>

        {/* Products Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4">
          {data.results.slice(0, 12).map((product) => (
            <ProductCard
              key={product.product_id}
              product={product}
              userId={userId}
            />
          ))}
        </div>

        {/* Recommendation Info */}
        {data.personalized && (
          <div className="mt-6 text-center">
            <p className="text-xs text-evergreen/60">
              <span className="inline-flex items-center gap-1">
                <Sparkles className="w-3 h-3" />
                These recommendations are personalized for you
              </span>
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
