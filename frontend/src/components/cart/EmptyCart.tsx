"use client";

import { ShoppingCart, Sparkles } from "lucide-react";
import Link from "next/link";

export function EmptyCart() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
      <div className="text-center max-w-md">
        {/* Icon */}
        <div className="relative mb-6">
          <div className="w-24 h-24 mx-auto bg-light-gray/50 rounded-full flex items-center justify-center">
            <ShoppingCart className="h-12 w-12 text-gray" />
          </div>
          <div className="absolute -top-1 -right-1/4">
            <Sparkles className="h-6 w-6 text-pinterest-red" />
          </div>
        </div>

        {/* Message */}
        <h2 className="text-2xl font-bold text-charcoal mb-3">
          Your Cart is Empty
        </h2>
        <p className="text-muted-foreground mb-8">
          Looks like you haven't added any items to your cart yet. Start exploring and discover amazing products!
        </p>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link
            href="/"
            className="px-6 py-3 bg-pinterest-red text-white font-semibold rounded-lg hover:bg-dark-red transition-all duration-[var(--duration-fast)] shadow-md hover:shadow-lg active:scale-95"
          >
            Explore Products
          </Link>
          <Link
            href="/feed"
            className="px-6 py-3 bg-white border-2 border-light-gray text-charcoal font-semibold rounded-lg hover:border-pinterest-red/30 transition-all duration-[var(--duration-fast)] active:scale-95"
          >
            View Personalized Feed
          </Link>
        </div>
      </div>
    </div>
  );
}
