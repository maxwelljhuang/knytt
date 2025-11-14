"use client";

import { useCartStore } from "@/lib/stores/cartStore";
import { ShoppingBag, Info } from "lucide-react";

export function CartSummary() {
  const { items, getItemCount, getTotalPrice } = useCartStore();

  const itemCount = getItemCount();
  const subtotal = getTotalPrice();

  // Get currency from first item (assuming all items have same currency)
  const currency = items[0]?.currency || "$";

  return (
    <div className="sticky top-24 bg-white border-2 border-light-gray rounded-xl p-6 shadow-lg">
      <div className="flex items-center gap-2 mb-6">
        <ShoppingBag className="h-5 w-5 text-pinterest-red" />
        <h2 className="text-xl font-bold text-charcoal">Cart Summary</h2>
      </div>

      <div className="space-y-3 mb-6">
        {/* Total Items */}
        <div className="flex justify-between items-center">
          <span className="text-muted-foreground">Total Items</span>
          <span className="font-semibold text-charcoal">{itemCount}</span>
        </div>

        {/* Subtotal */}
        <div className="flex justify-between items-center pt-3 border-t border-border">
          <span className="text-lg font-semibold text-charcoal">Subtotal</span>
          <span className="text-2xl font-bold text-pinterest-red">
            {currency}{subtotal.toFixed(2)}
          </span>
        </div>
      </div>

      {/* Affiliate Notice */}
      <div className="bg-light-gray/50 rounded-lg p-4 mb-6">
        <div className="flex items-start gap-2">
          <Info className="h-4 w-4 text-charcoal flex-shrink-0 mt-0.5" />
          <p className="text-xs text-muted-foreground leading-relaxed">
            Items are purchased from external merchants. Click "Buy Now" on each item to complete your purchase.
          </p>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="space-y-3">
        <button
          onClick={() => {
            // Scroll to first item
            const firstItem = document.querySelector('[data-cart-item]');
            firstItem?.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }}
          className="w-full py-3 px-4 bg-pinterest-red text-white font-semibold rounded-lg hover:bg-dark-red transition-all duration-[var(--duration-fast)] shadow-md hover:shadow-lg active:scale-95"
        >
          Purchase Items ({itemCount})
        </button>

        <button
          onClick={() => window.location.href = '/'}
          className="w-full py-3 px-4 bg-white border-2 border-light-gray text-charcoal font-semibold rounded-lg hover:border-pinterest-red/30 transition-all duration-[var(--duration-fast)] active:scale-95"
        >
          Continue Shopping
        </button>
      </div>
    </div>
  );
}
