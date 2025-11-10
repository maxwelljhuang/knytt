"use client";

import { useEffect } from "react";
import { useAuth } from "@/lib/queries/auth";
import { useFeed } from "@/lib/queries/recommendations";
import { RecommendationCarousel } from "@/components/recommendations/RecommendationCarousel";
import { Sparkles, Loader2, TrendingUp } from "lucide-react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function FeedPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const userId = user?.id;

  const { data: feedData, isLoading: feedLoading } = useFeed(userId);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login?redirect=/feed");
    }
  }, [authLoading, isAuthenticated, router]);

  if (authLoading || feedLoading) {
    return (
      <div className="min-h-screen bg-ivory">
        <div className="container mx-auto px-4 py-12">
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2 className="w-12 h-12 text-sage animate-spin mb-4" />
            <p className="text-sage">Personalizing your feed...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-ivory">
      <div className="container mx-auto px-4 py-12">
        {/* Hero Section */}
        <div className="mb-12 text-center">
          <div className="inline-flex items-center gap-3 mb-4 px-6 py-3 bg-gradient-to-r from-sage/20 to-terracotta/20 rounded-full">
            <Sparkles className="w-5 h-5 text-evergreen" />
            <span className="text-sm font-medium text-evergreen">
              Personalized for You
            </span>
          </div>
          <h1 className="text-5xl font-bold text-evergreen mb-4">
            Your Personal Feed
          </h1>
          <p className="text-lg text-sage max-w-2xl mx-auto">
            Curated recommendations based on your unique style and preferences
          </p>
        </div>

        {/* Stats Banner */}
        {feedData && (
          <div className="mb-12 bg-white rounded-2xl p-6 shadow-sm">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-blush rounded-xl">
                  <TrendingUp className="w-6 h-6 text-evergreen" />
                </div>
                <div>
                  <p className="text-sm text-sage">Total Recommendations</p>
                  <p className="text-2xl font-bold text-evergreen">
                    {feedData.total}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="p-3 bg-blush rounded-xl">
                  <Sparkles className="w-6 h-6 text-sage" />
                </div>
                <div>
                  <p className="text-sm text-sage">Personalized</p>
                  <p className="text-2xl font-bold text-evergreen">
                    {feedData.personalized ? "Yes" : "No"}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="p-3 bg-blush rounded-xl">
                  <div className="w-6 h-6 flex items-center justify-center text-evergreen font-bold">
                    🎯
                  </div>
                </div>
                <div>
                  <p className="text-sm text-sage">Profile Active</p>
                  <p className="text-2xl font-bold text-evergreen">
                    {feedData.has_long_term_profile ? "Yes" : "No"}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="p-3 bg-blush rounded-xl">
                  <div className="w-6 h-6 flex items-center justify-center text-evergreen font-bold">
                    ⚡
                  </div>
                </div>
                <div>
                  <p className="text-sm text-sage">Response Time</p>
                  <p className="text-2xl font-bold text-evergreen">
                    {feedData.recommendation_time_ms}ms
                  </p>
                </div>
              </div>
            </div>

            {/* Blend Weights */}
            {feedData.blend_weights && (
              <div className="mt-6 pt-6 border-t border-sage/10">
                <p className="text-sm text-sage mb-3">Recommendation Blend:</p>
                <div className="flex gap-4">
                  {feedData.blend_weights.long_term && (
                    <div className="flex items-center gap-2">
                      <div
                        className="h-2 bg-sage rounded-full"
                        style={{
                          width: `${feedData.blend_weights.long_term * 100}px`,
                        }}
                      />
                      <span className="text-xs text-sage">
                        Long-term: {(feedData.blend_weights.long_term * 100).toFixed(0)}%
                      </span>
                    </div>
                  )}
                  {feedData.blend_weights.session && (
                    <div className="flex items-center gap-2">
                      <div
                        className="h-2 bg-terracotta rounded-full"
                        style={{
                          width: `${feedData.blend_weights.session * 100}px`,
                        }}
                      />
                      <span className="text-xs text-sage">
                        Session: {(feedData.blend_weights.session * 100).toFixed(0)}%
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Recommendations */}
        {feedData && feedData.results.length > 0 ? (
          <RecommendationCarousel
            title="Recommended for You"
            products={feedData.results}
            userId={userId ? Number(userId) : undefined}
            context="personalized_feed"
          />
        ) : (
          <div className="text-center py-20">
            <Sparkles className="w-16 h-16 text-sage/30 mx-auto mb-4" />
            <h2 className="text-2xl font-semibold text-evergreen mb-2">
              No recommendations yet
            </h2>
            <p className="text-sage mb-6">
              Start exploring products to get personalized recommendations
            </p>
            <Link
              href="/"
              className="inline-block px-6 py-3 bg-terracotta text-white rounded-full hover:bg-terracotta/90 transition-colors"
            >
              Discover Products
            </Link>
          </div>
        )}

        {/* CTA Section */}
        <div className="mt-16 bg-gradient-to-r from-sage/10 to-terracotta/10 rounded-2xl p-8 text-center">
          <h2 className="text-2xl font-bold text-evergreen mb-3">
            Make Your Feed Even Better
          </h2>
          <p className="text-sage mb-6">
            The more you interact with products, the better your recommendations become
          </p>
          <div className="flex justify-center gap-4">
            <Link
              href="/settings"
              className="px-6 py-3 bg-white text-evergreen rounded-full hover:bg-blush transition-colors"
            >
              Update Preferences
            </Link>
            <Link
              href="/"
              className="px-6 py-3 bg-evergreen text-white rounded-full hover:bg-sage transition-colors"
            >
              Explore More
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
