"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/lib/queries/auth";
import { useUserStats, useUpdatePreferences } from "@/lib/queries/user";
import {
  Settings as SettingsIcon,
  User,
  Heart,
  TrendingUp,
  DollarSign,
  Tag,
  Package,
  Loader2,
  Save,
} from "lucide-react";
import { useRouter } from "next/navigation";
import Link from "next/link";

type TabType = "profile" | "preferences" | "stats";

export default function SettingsPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const userId = user?.id;
  const { data: stats, isLoading: statsLoading } = useUserStats(userId);
  const updatePreferences = useUpdatePreferences();

  const [activeTab, setActiveTab] = useState<TabType>("profile");
  const [preferredCategories, setPreferredCategories] = useState<string[]>([]);
  const [priceMin, setPriceMin] = useState<string>("");
  const [priceMax, setPriceMax] = useState<string>("");

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login?redirect=/settings");
    }
  }, [authLoading, isAuthenticated, router]);

  const handleSavePreferences = () => {
    if (!userId) return;
    updatePreferences.mutate({
      userId,
      preferences: {
        preferred_categories: preferredCategories.length > 0 ? preferredCategories : undefined,
        price_band_min: priceMin ? parseFloat(priceMin) : undefined,
        price_band_max: priceMax ? parseFloat(priceMax) : undefined,
      },
    });
  };

  const addCategory = (category: string) => {
    if (category && !preferredCategories.includes(category)) {
      setPreferredCategories([...preferredCategories, category]);
    }
  };

  const removeCategory = (category: string) => {
    setPreferredCategories(preferredCategories.filter((c) => c !== category));
  };

  if (authLoading) {
    return (
      <div className="min-h-screen bg-ivory">
        <div className="container mx-auto px-4 py-12">
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 text-sage animate-spin" />
          </div>
        </div>
      </div>
    );
  }

  const tabs = [
    { id: "profile" as TabType, label: "Profile", icon: User },
    { id: "preferences" as TabType, label: "Preferences", icon: Heart },
    { id: "stats" as TabType, label: "Statistics", icon: TrendingUp },
  ];

  return (
    <div className="min-h-screen bg-ivory">
      <div className="container mx-auto px-4 py-12">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <SettingsIcon className="w-8 h-8 text-evergreen" />
            <h1 className="text-4xl font-bold text-evergreen">Settings</h1>
          </div>
          <p className="text-sage">Manage your account and preferences</p>
        </div>

        {/* Tabs */}
        <div className="mb-8 flex gap-2 border-b border-sage/20">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-6 py-3 font-medium transition-all ${
                  activeTab === tab.id
                    ? "text-evergreen border-b-2 border-evergreen"
                    : "text-sage hover:text-evergreen"
                }`}
              >
                <Icon className="w-5 h-5" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Tab Content */}
        <div className="max-w-4xl">
          {/* Profile Tab */}
          {activeTab === "profile" && (
            <div className="space-y-6">
              <div className="bg-white rounded-xl p-6 shadow-sm">
                <h2 className="text-xl font-semibold text-evergreen mb-4">
                  Account Information
                </h2>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-sage mb-1">
                      Email
                    </label>
                    <input
                      type="email"
                      value={user?.email || ""}
                      disabled
                      className="w-full px-4 py-2 border border-sage/20 rounded-lg bg-gray-50 text-gray-600"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-sage mb-1">
                      Full Name
                    </label>
                    <input
                      type="text"
                      value={user?.email.split('@')[0] || ""}
                      disabled
                      className="w-full px-4 py-2 border border-sage/20 rounded-lg bg-gray-50 text-gray-600"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-sage mb-1">
                        Total Interactions
                      </label>
                      <div className="px-4 py-2 border border-sage/20 rounded-lg bg-blush text-evergreen font-semibold">
                        {user?.total_interactions || 0}
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-sage mb-1">
                        Member Since
                      </label>
                      <div className="px-4 py-2 border border-sage/20 rounded-lg bg-blush text-evergreen font-semibold">
                        {user?.created_at
                          ? new Date(user.created_at).toLocaleDateString()
                          : "N/A"}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl p-6 shadow-sm">
                <h2 className="text-xl font-semibold text-evergreen mb-4">
                  Quick Links
                </h2>
                <div className="space-y-2">
                  <Link
                    href="/favorites"
                    className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-blush transition-colors"
                  >
                    <Heart className="w-5 h-5 text-terracotta" />
                    <span className="text-evergreen">My Favorites</span>
                  </Link>
                  <Link
                    href="/history"
                    className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-blush transition-colors"
                  >
                    <Package className="w-5 h-5 text-sage" />
                    <span className="text-evergreen">Interaction History</span>
                  </Link>
                </div>
              </div>
            </div>
          )}

          {/* Preferences Tab */}
          {activeTab === "preferences" && (
            <div className="space-y-6">
              <div className="bg-white rounded-xl p-6 shadow-sm">
                <h2 className="text-xl font-semibold text-evergreen mb-4">
                  Shopping Preferences
                </h2>

                {/* Price Range */}
                <div className="mb-6">
                  <label className="block text-sm font-medium text-sage mb-3 flex items-center gap-2">
                    <DollarSign className="w-4 h-4" />
                    Price Range
                  </label>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs text-sage mb-1">
                        Minimum ($)
                      </label>
                      <input
                        type="number"
                        value={priceMin}
                        onChange={(e) => setPriceMin(e.target.value)}
                        placeholder="0"
                        min="0"
                        className="w-full px-4 py-2 border border-sage/20 rounded-lg focus:outline-none focus:ring-2 focus:ring-sage/50"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-sage mb-1">
                        Maximum ($)
                      </label>
                      <input
                        type="number"
                        value={priceMax}
                        onChange={(e) => setPriceMax(e.target.value)}
                        placeholder="1000"
                        min="0"
                        className="w-full px-4 py-2 border border-sage/20 rounded-lg focus:outline-none focus:ring-2 focus:ring-sage/50"
                      />
                    </div>
                  </div>
                </div>

                {/* Preferred Categories */}
                <div className="mb-6">
                  <label className="block text-sm font-medium text-sage mb-3 flex items-center gap-2">
                    <Tag className="w-4 h-4" />
                    Preferred Categories
                  </label>
                  <div className="flex flex-wrap gap-2 mb-3">
                    {preferredCategories.map((category) => (
                      <span
                        key={category}
                        className="inline-flex items-center gap-2 px-3 py-1 bg-sage text-white rounded-full text-sm"
                      >
                        {category}
                        <button
                          onClick={() => removeCategory(category)}
                          className="hover:text-red-200 transition-colors"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="Add category (e.g., clothing, accessories)"
                      className="flex-1 px-4 py-2 border border-sage/20 rounded-lg focus:outline-none focus:ring-2 focus:ring-sage/50"
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          addCategory((e.target as HTMLInputElement).value);
                          (e.target as HTMLInputElement).value = "";
                        }
                      }}
                    />
                  </div>
                  <p className="text-xs text-sage mt-2">
                    Press Enter to add a category
                  </p>
                </div>

                {/* Save Button */}
                <div className="flex items-center gap-3">
                  <button
                    onClick={handleSavePreferences}
                    disabled={updatePreferences.isPending}
                    className="flex items-center gap-2 px-6 py-3 bg-evergreen text-white rounded-lg hover:bg-sage transition-colors disabled:opacity-50"
                  >
                    <Save className="w-5 h-5" />
                    {updatePreferences.isPending ? "Saving..." : "Save Preferences"}
                  </button>
                  {updatePreferences.isSuccess && (
                    <span className="text-green-600 text-sm">
                      Preferences saved successfully!
                    </span>
                  )}
                  {updatePreferences.isError && (
                    <span className="text-red-600 text-sm">
                      Error saving preferences
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Statistics Tab */}
          {activeTab === "stats" && (
            <div className="space-y-6">
              {statsLoading ? (
                <div className="flex items-center justify-center py-20">
                  <Loader2 className="w-8 h-8 text-sage animate-spin" />
                </div>
              ) : stats ? (
                <>
                  {/* Overview Stats */}
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                    <div className="bg-white rounded-xl p-6 shadow-sm">
                      <p className="text-sm text-sage mb-1">Total Interactions</p>
                      <p className="text-3xl font-bold text-evergreen">
                        {stats.total_interactions}
                      </p>
                    </div>
                    <div className="bg-white rounded-xl p-6 shadow-sm">
                      <p className="text-sm text-sage mb-1">Products Viewed</p>
                      <p className="text-3xl font-bold text-evergreen">
                        {stats.total_views}
                      </p>
                    </div>
                    <div className="bg-white rounded-xl p-6 shadow-sm">
                      <p className="text-sm text-sage mb-1">Products Clicked</p>
                      <p className="text-3xl font-bold text-evergreen">
                        {stats.total_clicks}
                      </p>
                    </div>
                    <div className="bg-white rounded-xl p-6 shadow-sm">
                      <p className="text-sm text-sage mb-1">Products Liked</p>
                      <p className="text-3xl font-bold text-terracotta">
                        {stats.total_likes}
                      </p>
                    </div>
                    <div className="bg-white rounded-xl p-6 shadow-sm">
                      <p className="text-sm text-sage mb-1">Cart Additions</p>
                      <p className="text-3xl font-bold text-evergreen">
                        {stats.total_cart_adds}
                      </p>
                    </div>
                    <div className="bg-white rounded-xl p-6 shadow-sm">
                      <p className="text-sm text-sage mb-1">Purchases</p>
                      <p className="text-3xl font-bold text-evergreen">
                        {stats.total_purchases}
                      </p>
                    </div>
                  </div>

                  {/* Favorite Categories */}
                  {stats.favorite_categories.length > 0 && (
                    <div className="bg-white rounded-xl p-6 shadow-sm">
                      <h2 className="text-xl font-semibold text-evergreen mb-4">
                        Favorite Categories
                      </h2>
                      <div className="space-y-3">
                        {stats.favorite_categories.map((cat, index) => (
                          <div key={cat.category} className="flex items-center gap-3">
                            <span className="text-sm font-medium text-sage w-8">
                              #{index + 1}
                            </span>
                            <div className="flex-1 bg-blush rounded-lg p-3">
                              <div className="flex justify-between items-center">
                                <span className="font-medium text-evergreen">
                                  {cat.category}
                                </span>
                                <span className="text-sm text-sage">
                                  {cat.count} interactions
                                </span>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Favorite Brands */}
                  {stats.favorite_brands.length > 0 && (
                    <div className="bg-white rounded-xl p-6 shadow-sm">
                      <h2 className="text-xl font-semibold text-evergreen mb-4">
                        Favorite Brands
                      </h2>
                      <div className="space-y-3">
                        {stats.favorite_brands.map((brand, index) => (
                          <div key={brand.brand} className="flex items-center gap-3">
                            <span className="text-sm font-medium text-sage w-8">
                              #{index + 1}
                            </span>
                            <div className="flex-1 bg-blush rounded-lg p-3">
                              <div className="flex justify-between items-center">
                                <span className="font-medium text-evergreen">
                                  {brand.brand}
                                </span>
                                <span className="text-sm text-sage">
                                  {brand.count} interactions
                                </span>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Additional Insights */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-white rounded-xl p-6 shadow-sm">
                      <p className="text-sm text-sage mb-1">Average Price Point</p>
                      <p className="text-2xl font-bold text-evergreen">
                        {stats.avg_price_point
                          ? `$${stats.avg_price_point.toFixed(2)}`
                          : "N/A"}
                      </p>
                    </div>
                    <div className="bg-white rounded-xl p-6 shadow-sm">
                      <p className="text-sm text-sage mb-1">Account Age</p>
                      <p className="text-2xl font-bold text-evergreen">
                        {stats.account_age_days} days
                      </p>
                    </div>
                  </div>
                </>
              ) : (
                <div className="text-center py-20">
                  <p className="text-sage">No statistics available</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
