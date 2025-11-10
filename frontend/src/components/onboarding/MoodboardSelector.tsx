"use client";

import { useState, useEffect } from "react";
import { useOnboardingProducts } from "@/lib/queries/onboarding";
import { Check, Loader2, ChevronRight } from "lucide-react";
import Image from "next/image";

interface MoodboardSelectorProps {
  onComplete: (selectedProducts: string[]) => void;
  minSelection?: number;
  maxSelection?: number;
}

export function MoodboardSelector({
  onComplete,
  minSelection = 3,
  maxSelection = 5,
}: MoodboardSelectorProps) {
  const { data, isLoading, error } = useOnboardingProducts();
  const [selectedProducts, setSelectedProducts] = useState<Set<string>>(
    new Set()
  );

  const handleProductToggle = (productId: string) => {
    const newSelection = new Set(selectedProducts);

    if (newSelection.has(productId)) {
      newSelection.delete(productId);
    } else {
      // Only add if we haven't reached max selection
      if (newSelection.size < maxSelection) {
        newSelection.add(productId);
      }
    }

    setSelectedProducts(newSelection);
  };

  const handleContinue = () => {
    if (selectedProducts.size >= minSelection) {
      onComplete(Array.from(selectedProducts));
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-pinterest-red animate-spin mx-auto mb-4" />
          <p className="text-gray">Loading style options...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-20">
        <p className="text-red-500 mb-4">Failed to load products</p>
        <button
          onClick={() => window.location.reload()}
          className="px-6 py-2 bg-pinterest-red text-white rounded-full hover:bg-dark-red transition-colors"
        >
          Try Again
        </button>
      </div>
    );
  }

  if (!data || data.products.length === 0) {
    return (
      <div className="text-center py-20">
        <p className="text-gray">No products available</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* Selection counter */}
      <div className="flex justify-between items-center mb-6">
        <div className="text-sm text-gray">
          Selected: {selectedProducts.size} / {maxSelection}
          {selectedProducts.size < minSelection && (
            <span className="ml-2 text-pinterest-red">
              (Select at least {minSelection - selectedProducts.size} more)
            </span>
          )}
        </div>
        <button
          onClick={handleContinue}
          disabled={selectedProducts.size < minSelection}
          className={`px-6 py-3 rounded-full font-medium flex items-center gap-2 transition-all ${
            selectedProducts.size >= minSelection
              ? "bg-pinterest-red text-white hover:bg-dark-red active:scale-95"
              : "bg-light-gray text-gray cursor-not-allowed"
          }`}
        >
          Continue
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>

      {/* Product Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
        {data.products.map((product) => {
          const isSelected = selectedProducts.has(product.product_id);
          const isDisabled =
            !isSelected && selectedProducts.size >= maxSelection;

          return (
            <div
              key={product.product_id}
              onClick={() => !isDisabled && handleProductToggle(product.product_id)}
              className={`relative group cursor-pointer transition-all duration-200 ${
                isDisabled ? "opacity-50 cursor-not-allowed" : ""
              }`}
            >
              {/* Product Image */}
              <div
                className={`relative rounded-2xl overflow-hidden bg-light-gray ${
                  isSelected ? "ring-4 ring-pinterest-red" : ""
                }`}
              >
                {product.image_url ? (
                  <div className="relative aspect-[3/4]">
                    <Image
                      src={product.image_url}
                      alt={product.title}
                      fill
                      className="object-cover"
                      sizes="(max-width: 640px) 50vw, (max-width: 768px) 33vw, (max-width: 1024px) 25vw, 20vw"
                    />
                  </div>
                ) : (
                  <div className="aspect-[3/4] flex items-center justify-center bg-light-gray">
                    <span className="text-gray text-4xl">?</span>
                  </div>
                )}

                {/* Selection Overlay */}
                {isSelected && (
                  <div className="absolute inset-0 bg-pinterest-red/20 flex items-center justify-center">
                    <div className="bg-pinterest-red text-white rounded-full p-3">
                      <Check className="w-6 h-6" strokeWidth={3} />
                    </div>
                  </div>
                )}

                {/* Hover Overlay (when not selected and not disabled) */}
                {!isSelected && !isDisabled && (
                  <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100">
                    <div className="bg-white/90 text-charcoal rounded-full px-4 py-2 font-medium">
                      Select
                    </div>
                  </div>
                )}
              </div>

              {/* Product Info */}
              <div className="mt-2">
                <p className="text-sm font-medium text-charcoal line-clamp-2">
                  {product.title}
                </p>
                {product.brand && (
                  <p className="text-xs text-gray mt-1">{product.brand}</p>
                )}
                <p className="text-sm font-semibold text-charcoal mt-1">
                  ${product.price.toFixed(2)}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Mobile Continue Button */}
      <div className="mt-8 md:hidden">
        <button
          onClick={handleContinue}
          disabled={selectedProducts.size < minSelection}
          className={`w-full px-6 py-4 rounded-full font-medium flex items-center justify-center gap-2 transition-all ${
            selectedProducts.size >= minSelection
              ? "bg-pinterest-red text-white hover:bg-dark-red active:scale-95"
              : "bg-light-gray text-gray cursor-not-allowed"
          }`}
        >
          Continue
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}