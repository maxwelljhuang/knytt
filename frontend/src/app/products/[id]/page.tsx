"use client";

import { useParams, useRouter, useSearchParams } from "next/navigation";
import { ChevronLeft, Share2, Loader2, AlertCircle } from "lucide-react";
import { useTrackInteraction } from "@/lib/queries/feedback";
import { InteractionType } from "@/types/enums";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ProductImageGallery,
  ProductInfo,
  ProductPricing,
  ProductActions,
  SimilarProducts,
} from "@/components/product";
import { useSearch } from "@/lib/queries/search";
import { useAuth } from "@/lib/queries/auth";
import type { ProductResult } from "@/types/api";

// Required for Cloudflare Pages deployment
export const runtime = "edge";

export default function ProductDetailPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const productId = params.id as string;
  const feedbackMutation = useTrackInteraction();
  const [product, setProduct] = useState<ProductResult | null>(null);
  const { user } = useAuth();
  const userId = user?.id ? Number(user.id) : undefined;

  // Try to fetch product via search (temporary solution)
  // We search with a very specific query to try to get this product
  const productTitle = searchParams.get("title");
  const { data: searchData, isLoading } = useSearch(
    {
      query: productTitle || productId.substring(0, 8), // Use title or part of ID
      limit: 50,
    },
    {
      enabled: !product && !!productId, // Only search if we don't have product data
    }
  );

  // Track product view on page load
  useEffect(() => {
    if (productId && user?.id) {
      feedbackMutation.mutate({
        user_id: user.id,
        product_id: productId,
        interaction_type: InteractionType.VIEW,
      });
    }
  }, [productId, user]);

  // Try to find the product in search results
  useEffect(() => {
    if (searchData && searchData.results.length > 0 && !product) {
      // Try to find exact match by ID
      const exactMatch = searchData.results.find(
        (p) => p.product_id === productId
      );
      if (exactMatch) {
        setProduct(exactMatch);
      } else {
        // Use first result as fallback
        setProduct(searchData.results[0]);
      }
    }
  }, [searchData, productId, product]);

  const handleShare = async () => {
    const url = window.location.href;
    if (navigator.share) {
      try {
        await navigator.share({
          title: product?.title || "Check out this product",
          text: product?.description || "",
          url: url,
        });
      } catch (err) {
        // User cancelled or share failed
        console.log("Share cancelled");
      }
    } else {
      // Fallback: copy to clipboard
      await navigator.clipboard.writeText(url);
      alert("Link copied to clipboard!");
    }
  };

  return (
    <div className="min-h-screen bg-ivory">
      {/* Breadcrumb & Navigation */}
      <div className="bg-white border-b border-blush">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => router.back()}
                className="flex items-center gap-2 text-evergreen hover:text-sage transition-colors"
              >
                <ChevronLeft className="w-5 h-5" />
                <span className="text-sm font-medium">Back</span>
              </button>

              <nav className="hidden md:flex items-center gap-2 text-sm text-evergreen/60">
                <Link href="/" className="hover:text-sage transition-colors">
                  Discover
                </Link>
                <span>/</span>
                <span className="text-evergreen font-medium">
                  {product?.title || "Product"}
                </span>
              </nav>
            </div>

            <button
              onClick={handleShare}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-evergreen hover:text-sage border border-blush rounded-full hover:border-sage transition-all"
            >
              <Share2 className="w-4 h-4" />
              <span className="hidden sm:inline">Share</span>
            </button>
          </div>
        </div>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="container mx-auto px-4 py-20">
          <div className="flex flex-col items-center justify-center">
            <Loader2 className="w-12 h-12 text-sage animate-spin mb-4" />
            <p className="text-evergreen/60">Loading product details...</p>
          </div>
        </div>
      )}

      {/* Error State */}
      {!isLoading && !product && (
        <div className="container mx-auto px-4 py-20">
          <div className="flex flex-col items-center justify-center text-center max-w-md mx-auto">
            <AlertCircle className="w-16 h-16 text-sage mb-4" />
            <h2 className="text-2xl font-bold text-evergreen mb-2">
              Product Not Found
            </h2>
            <p className="text-evergreen/60 mb-6">
              We couldn't find the product you're looking for. It may have been
              removed or the link might be incorrect.
            </p>
            <Link
              href="/"
              className="px-6 py-3 bg-gradient-to-r from-sage to-evergreen text-white rounded-full font-semibold hover:shadow-lg transition-all"
            >
              Back to Home
            </Link>
          </div>
        </div>
      )}

      {/* Main Content */}
      {product && !isLoading && (
        <main className="container mx-auto px-4 py-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-12">
            {/* Left Column - Image Gallery */}
            <div className="lg:sticky lg:top-24 self-start">
              <ProductImageGallery
                mainImage={product.image_url || null}
                additionalImages={[]}
                productTitle={product.title}
              />
            </div>

            {/* Right Column - Product Info */}
            <div className="space-y-8">
              {/* Product Info */}
              <ProductInfo product={product} />

              {/* Pricing & Stock */}
              <ProductPricing product={product} />

              {/* Actions */}
              <ProductActions
                productId={product.product_id}
                userId={userId}
                inStock={product.in_stock}
              />
            </div>
          </div>

          {/* Similar Products */}
          <SimilarProducts productId={product.product_id} userId={userId} />
        </main>
      )}
    </div>
  );
}
