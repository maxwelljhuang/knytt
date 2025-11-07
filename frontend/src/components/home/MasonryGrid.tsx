"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { ProductResult } from "@/types/api";
import { Heart, ShoppingCart } from "lucide-react";
import { useTrackInteraction } from "@/lib/queries/feedback";
import { InteractionType } from "@/types/enums";
import Link from "next/link";

interface MasonryCardProps {
  product: ProductResult;
  userId?: number;
  onLike: (productId: string, e: React.MouseEvent) => void;
  onAddToCart: (productId: string, e: React.MouseEvent) => void;
  onClick: (productId: string) => void;
}

function MasonryCard({ product, userId, onLike, onAddToCart, onClick }: MasonryCardProps) {
  const [imageError, setImageError] = useState(false);

  // Don't render card if image failed to load
  if (imageError) {
    return null;
  }

  return (
    <Link
      href={`/products/${product.product_id}`}
      onClick={() => onClick(product.product_id)}
      className="group relative bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-xl transition-all duration-300 cursor-pointer"
    >
      {/* Image */}
      <div className="relative aspect-[3/4] overflow-hidden bg-blush">
        <Image
          src={product.image_url!}
          alt={product.title}
          fill
          sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, (max-width: 1536px) 25vw, 20vw"
          className="object-cover group-hover:scale-110 transition-transform duration-500"
          loading="lazy"
          onError={() => setImageError(true)}
        />

        {/* Overlay Actions */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/0 to-black/0 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
          <div className="absolute bottom-4 left-4 right-4 flex justify-between items-end">
            {/* Price */}
            <div className="text-white">
              <p className="text-2xl font-bold">
                {product.currency || "$"}{product.price?.toFixed(2) || "0.00"}
              </p>
              {product.rrp_price && product.rrp_price > product.price && (
                <p className="text-sm line-through opacity-75">
                  {product.currency || "$"}{product.rrp_price.toFixed(2)}
                </p>
              )}
            </div>

            {/* Action Buttons */}
            <div className="flex gap-2">
              <button
                onClick={(e) => onLike(product.product_id, e)}
                className="p-2.5 bg-white/90 backdrop-blur-sm rounded-full hover:bg-white transition-colors"
              >
                <Heart className="w-5 h-5 text-terracotta" />
              </button>
              <button
                onClick={(e) => onAddToCart(product.product_id, e)}
                className="p-2.5 bg-white/90 backdrop-blur-sm rounded-full hover:bg-white transition-colors"
                disabled={!product.in_stock}
              >
                <ShoppingCart className={`w-5 h-5 ${product.in_stock ? "text-sage" : "text-gray-400"}`} />
              </button>
            </div>
          </div>
        </div>

        {/* Stock Badge */}
        {!product.in_stock && (
          <div className="absolute top-4 left-4">
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

        {/* Description */}
        {product.description && (
          <p className="text-xs text-evergreen/60 line-clamp-2">
            {product.description}
          </p>
        )}
      </div>
    </Link>
  );
}

interface MasonryGridProps {
  products: ProductResult[];
  userId?: number;
}

export function MasonryGrid({ products, userId }: MasonryGridProps) {
  const [columns, setColumns] = useState(4);
  const feedbackMutation = useTrackInteraction();

  useEffect(() => {
    const updateColumns = () => {
      if (window.innerWidth < 640) setColumns(2);
      else if (window.innerWidth < 1024) setColumns(3);
      else if (window.innerWidth < 1536) setColumns(4);
      else setColumns(5);
    };

    updateColumns();
    window.addEventListener("resize", updateColumns);
    return () => window.removeEventListener("resize", updateColumns);
  }, []);

  // Filter out products without valid images (safety net)
  const validProducts = products.filter(p => p.image_url?.trim());

  // Distribute products into columns
  const columnProducts: ProductResult[][] = Array.from({ length: columns }, () => []);
  validProducts.forEach((product, index) => {
    columnProducts[index % columns].push(product);
  });

  const handleLike = (productId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!userId) return; // Skip if not authenticated
    feedbackMutation.mutate({
      user_id: userId,
      product_id: productId,
      interaction_type: InteractionType.LIKE,
    });
  };

  const handleAddToCart = (productId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!userId) return; // Skip if not authenticated
    feedbackMutation.mutate({
      user_id: userId,
      product_id: productId,
      interaction_type: InteractionType.ADD_TO_CART,
    });
  };

  const handleClick = (productId: string) => {
    if (!userId) return; // Skip if not authenticated
    feedbackMutation.mutate({
      user_id: userId,
      product_id: productId,
      interaction_type: InteractionType.CLICK,
    });
  };

  return (
    <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}>
      {columnProducts.map((column, columnIndex) => (
        <div key={columnIndex} className="flex flex-col gap-4">
          {column.map((product) => (
            <MasonryCard
              key={product.product_id}
              product={product}
              userId={userId}
              onLike={handleLike}
              onAddToCart={handleAddToCart}
              onClick={handleClick}
            />
          ))}
        </div>
      ))}
    </div>
  );
}
