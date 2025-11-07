"use client";

import { ProductResult } from "@/types/api";
import { ProductCard } from "./ProductCard";
import { ProductSkeleton } from "./ProductSkeleton";

interface ProductGridProps {
  products: ProductResult[];
  userId?: number;
  isLoading?: boolean;
  onProductClick?: (productId: string) => void;
  columns?: 2 | 3 | 4;
}

export function ProductGrid({
  products,
  userId,
  isLoading = false,
  onProductClick,
  columns = 4,
}: ProductGridProps) {
  const gridCols = {
    2: "grid-cols-1 sm:grid-cols-2",
    3: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
    4: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4",
  };

  if (isLoading) {
    return (
      <div className={`grid ${gridCols[columns]} gap-6`}>
        {[...Array(8)].map((_, i) => (
          <ProductSkeleton key={i} />
        ))}
      </div>
    );
  }

  // Filter out products without valid images (safety net)
  const validProducts = products.filter(p => p.image_url?.trim());

  if (validProducts.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground text-lg">No products found</p>
      </div>
    );
  }

  return (
    <div className={`grid ${gridCols[columns]} gap-6`}>
      {validProducts.map((product) => (
        <ProductCard
          key={product.product_id}
          product={product}
          userId={userId}
          onProductClick={onProductClick}
        />
      ))}
    </div>
  );
}
