"use client";

import { useState } from "react";
import Image from "next/image";
import { Minus, Plus, Trash2, ExternalLink } from "lucide-react";
import { CartItem as CartItemType } from "@/lib/stores/cartStore";
import { useCartStore } from "@/lib/stores/cartStore";
import Tooltip from "@/components/ui/Tooltip";

interface CartItemProps {
  item: CartItemType;
}

export function CartItem({ item }: CartItemProps) {
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);
  const { updateQuantity, removeItem } = useCartStore();

  const handleQuantityChange = (newQuantity: number) => {
    if (newQuantity < 1) {
      removeItem(item.productId);
    } else {
      updateQuantity(item.productId, newQuantity);
    }
  };

  const handleRemove = () => {
    removeItem(item.productId);
  };

  const handleBuyNow = () => {
    if (item.productUrl) {
      window.open(item.productUrl, "_blank", "noopener,noreferrer");
    }
  };

  const itemTotal = item.price * item.quantity;

  return (
    <div className="flex gap-4 p-4 bg-white border-2 border-light-gray rounded-xl hover:border-pinterest-red/30 transition-all duration-[var(--duration-fast)]">
      {/* Product Image */}
      <div className="relative w-24 h-24 flex-shrink-0 bg-light-gray/50 rounded-lg overflow-hidden">
        {!imageLoaded && !imageError && (
          <div className="absolute inset-0 bg-light-gray animate-shimmer" />
        )}
        {item.imageUrl && !imageError ? (
          <Image
            src={item.imageUrl}
            alt={item.title}
            fill
            sizes="96px"
            className={`object-cover ${imageLoaded ? "opacity-100" : "opacity-0"} transition-opacity`}
            onLoad={() => setImageLoaded(true)}
            onError={() => setImageError(true)}
          />
        ) : (
          <div className="flex items-center justify-center h-full text-gray text-xs">
            No image
          </div>
        )}
      </div>

      {/* Product Details */}
      <div className="flex-1 min-w-0">
        {/* Title */}
        <h3 className="text-base font-bold text-charcoal mb-1 line-clamp-2">
          {item.title}
        </h3>

        {/* Price */}
        <p className="text-lg font-semibold text-pinterest-red mb-3">
          {item.currency}{item.price.toFixed(2)}
        </p>

        {/* Quantity Controls & Remove Button */}
        <div className="flex items-center gap-3">
          {/* Quantity Controls */}
          <div className="flex items-center gap-2 bg-light-gray/50 rounded-lg px-2 py-1">
            <Tooltip content="Decrease quantity">
              <button
                onClick={() => handleQuantityChange(item.quantity - 1)}
                className="p-1 hover:bg-white rounded transition-colors"
                aria-label="Decrease quantity"
              >
                <Minus className="h-4 w-4 text-charcoal" />
              </button>
            </Tooltip>

            <span className="min-w-[2rem] text-center font-semibold text-charcoal">
              {item.quantity}
            </span>

            <Tooltip content="Increase quantity">
              <button
                onClick={() => handleQuantityChange(item.quantity + 1)}
                className="p-1 hover:bg-white rounded transition-colors"
                aria-label="Increase quantity"
              >
                <Plus className="h-4 w-4 text-charcoal" />
              </button>
            </Tooltip>
          </div>

          {/* Remove Button */}
          <Tooltip content="Remove from cart">
            <button
              onClick={handleRemove}
              className="p-2 text-gray hover:text-pinterest-red hover:bg-light-gray/50 rounded-lg transition-all"
              aria-label="Remove item"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </Tooltip>
        </div>
      </div>

      {/* Buy Now & Total */}
      <div className="flex flex-col items-end justify-between">
        {/* Item Total */}
        <div className="text-right">
          <p className="text-xs text-muted-foreground mb-1">Total</p>
          <p className="text-xl font-bold text-charcoal">
            {item.currency}{itemTotal.toFixed(2)}
          </p>
        </div>

        {/* Buy Now Button */}
        {item.productUrl ? (
          <button
            onClick={handleBuyNow}
            className="flex items-center gap-2 px-4 py-2 bg-pinterest-red text-white font-semibold rounded-lg hover:bg-dark-red transition-all duration-[var(--duration-fast)] shadow-md hover:shadow-lg active:scale-95"
          >
            <span>Buy Now</span>
            <ExternalLink className="h-4 w-4" />
          </button>
        ) : (
          <p className="text-xs text-muted-foreground italic">
            No purchase link
          </p>
        )}
      </div>
    </div>
  );
}
