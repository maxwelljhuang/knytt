"use client";

import { HeroSection, CategoryPills, MasonryGrid } from "@/components/home";
import { RecommendationCarousel } from "@/components/recommendations/RecommendationCarousel";
import { useDiscover } from "@/lib/queries/discover";
import { useFeed } from "@/lib/queries/recommendations";
import { useAuth } from "@/lib/queries/auth";
import { Loader2, Sparkles } from "lucide-react";
import Link from "next/link";

export default function HomePage() {
  const { user, isAuthenticated } = useAuth();
  const userId = user?.id;

  // Fetch personalized recommendations for authenticated users
  const { data: recommendedData, isLoading: recommendationsLoading } = useFeed(userId);

  // Fetch featured products using discover endpoint (no ML dependencies)
  const { data, isLoading } = useDiscover(
    {
      sort_by: "popular",
      limit: 40,
    },
    {
      enabled: true,
    }
  );

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <HeroSection />

      {/* Category Navigation */}
      <CategoryPills />

      {/* Personalized Recommendations (Authenticated Users Only) */}
      {isAuthenticated && (
        <section className="py-8 bg-gradient-to-b from-white to-ivory">
          <div className="container mx-auto px-4">
            {recommendationsLoading ? (
              <div className="flex items-center justify-center py-10">
                <Loader2 className="w-8 h-8 text-pinterest-red animate-spin" />
              </div>
            ) : (
              recommendedData &&
              recommendedData.results.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3">
                      <Sparkles className="w-6 h-6 text-pinterest-red" />
                      <h2 className="text-2xl font-bold text-charcoal">
                        Recommended For You
                      </h2>
                    </div>
                    <Link
                      href="/feed"
                      className="text-pinterest-red hover:text-dark-red transition-colors font-medium"
                    >
                      See All →
                    </Link>
                  </div>
                  <RecommendationCarousel
                    title=""
                    products={recommendedData.results}
                    userId={userId ? Number(userId) : undefined}
                    context="homepage_recommendations"
                  />
                </div>
              )
            )}
          </div>
        </section>
      )}

      {/* Main Content */}
      <section className="py-12 bg-ivory">
        <div className="container mx-auto px-4">
          {/* Section Header */}
          <div className="mb-8">
            <h2 className="text-3xl font-bold text-charcoal mb-2">
              Discover Products
            </h2>
            <p className="text-gray">
              Explore curated collections powered by AI
            </p>
          </div>

          {/* Loading State */}
          {isLoading && (
            <div className="flex items-center justify-center py-20">
              <div className="text-center">
                <Loader2 className="w-12 h-12 text-pinterest-red animate-spin mx-auto mb-4" />
                <p className="text-gray">Loading products...</p>
              </div>
            </div>
          )}

          {/* Products Masonry Grid */}
          {data && data.results.length > 0 && (
            <MasonryGrid products={data.results} userId={userId ? Number(userId) : undefined} />
          )}

          {/* Empty State */}
          {data && data.results.length === 0 && (
            <div className="text-center py-20">
              <p className="text-gray text-lg">
                No products available yet. Check back soon!
              </p>
            </div>
          )}
        </div>
      </section>

      {/* Call to Action */}
      <section className="py-20 bg-gradient-to-br from-pinterest-red to-dark-red">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-4xl font-bold text-white mb-4">
            Ready to Find Your Style?
          </h2>
          <p className="text-white/90 text-lg mb-8 max-w-2xl mx-auto">
            Join thousands of users discovering products they love with our
            AI-powered recommendations.
          </p>
          <button className="px-8 py-4 bg-white text-pinterest-red rounded-full font-semibold text-lg hover:bg-light-gray transition-colors shadow-xl active:scale-95">
            Get Started
          </button>
        </div>
      </section>
    </div>
  );
}
