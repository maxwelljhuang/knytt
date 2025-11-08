"use client";

import { useState } from "react";
import { useAuth } from "@/lib/queries/auth";
import { useUpdatePreferences } from "@/lib/queries/user";
import {
  User,
  Heart,
  DollarSign,
  Tag,
  Package,
  Save,
  Calendar,
  Activity,
} from "lucide-react";
import Link from "next/link";

type TabType = "profile" | "preferences";

export default function SettingsContent() {
  const { user } = useAuth();
  const updatePreferences = useUpdatePreferences();

  const [activeTab, setActiveTab] = useState<TabType>("profile");
  const [preferredCategories, setPreferredCategories] = useState<string[]>([]);
  const [priceMin, setPriceMin] = useState<string>("");
  const [priceMax, setPriceMax] = useState<string>("");

  const handleSavePreferences = () => {
    updatePreferences.mutate({
      preferred_categories: preferredCategories.length > 0 ? preferredCategories : undefined,
      price_band_min: priceMin ? parseFloat(priceMin) : undefined,
      price_band_max: priceMax ? parseFloat(priceMax) : undefined,
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

  const tabs = [
    { id: "profile" as TabType, label: "Profile", icon: User },
    { id: "preferences" as TabType, label: "Preferences", icon: Heart },
  ];

  return (
    <div className="space-y-6">
      {/* Tabs */}
      <div className="bg-white rounded-2xl shadow-sm border border-light-gray p-2">
        <div className="flex gap-2">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-6 py-3 rounded-xl font-medium transition-all duration-[var(--duration-fast)] ${
                  activeTab === tab.id
                    ? "bg-pinterest-red text-white shadow-md"
                    : "text-charcoal hover:bg-light-gray active:scale-95"
                }`}
              >
                <Icon className="w-5 h-5" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Tab Content */}
      <div>
        {/* Profile Tab */}
        {activeTab === "profile" && (
          <div className="space-y-6">
            <div className="bg-white rounded-2xl shadow-sm border border-light-gray p-6">
              <h2 className="text-xl font-semibold text-charcoal mb-4">
                Account Information
              </h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray mb-1">
                    Email
                  </label>
                  <input
                    type="email"
                    value={user?.email || ""}
                    disabled
                    className="w-full px-4 py-2 border border-light-gray rounded-lg bg-gray-50 text-gray-600"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray mb-1">
                    Display Name
                  </label>
                  <input
                    type="text"
                    value={user?.email.split('@')[0] || ""}
                    disabled
                    className="w-full px-4 py-2 border border-light-gray rounded-lg bg-gray-50 text-gray-600"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray mb-1 flex items-center gap-1">
                      <Activity className="w-4 h-4" />
                      Total Interactions
                    </label>
                    <div className="px-4 py-2 border border-light-gray rounded-lg bg-light-gray text-charcoal font-semibold">
                      {user?.total_interactions || 0}
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray mb-1 flex items-center gap-1">
                      <Calendar className="w-4 h-4" />
                      Member Since
                    </label>
                    <div className="px-4 py-2 border border-light-gray rounded-lg bg-light-gray text-charcoal font-semibold">
                      {user?.created_at
                        ? new Date(user.created_at).toLocaleDateString()
                        : "N/A"}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-2xl shadow-sm border border-light-gray p-6">
              <h2 className="text-xl font-semibold text-charcoal mb-4">
                Quick Links
              </h2>
              <div className="space-y-2">
                <Link
                  href="/favorites"
                  className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-light-gray transition-colors"
                >
                  <Heart className="w-5 h-5 text-pinterest-red" />
                  <span className="text-charcoal">My Favorites</span>
                </Link>
                <Link
                  href="/history"
                  className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-light-gray transition-colors"
                >
                  <Package className="w-5 h-5 text-gray" />
                  <span className="text-charcoal">Interaction History</span>
                </Link>
              </div>
            </div>
          </div>
        )}

        {/* Preferences Tab */}
        {activeTab === "preferences" && (
          <div className="space-y-6">
            <div className="bg-white rounded-2xl shadow-sm border border-light-gray p-6">
              <h2 className="text-xl font-semibold text-charcoal mb-4">
                Shopping Preferences
              </h2>

              {/* Price Range */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray mb-3 flex items-center gap-2">
                  <DollarSign className="w-4 h-4" />
                  Price Range
                </label>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs text-gray mb-1">
                      Minimum ($)
                    </label>
                    <input
                      type="number"
                      value={priceMin}
                      onChange={(e) => setPriceMin(e.target.value)}
                      placeholder="0"
                      min="0"
                      className="w-full px-4 py-2 border border-light-gray rounded-lg focus:outline-none focus:ring-2 focus:ring-pinterest-red/50"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray mb-1">
                      Maximum ($)
                    </label>
                    <input
                      type="number"
                      value={priceMax}
                      onChange={(e) => setPriceMax(e.target.value)}
                      placeholder="1000"
                      min="0"
                      className="w-full px-4 py-2 border border-light-gray rounded-lg focus:outline-none focus:ring-2 focus:ring-pinterest-red/50"
                    />
                  </div>
                </div>
              </div>

              {/* Preferred Categories */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray mb-3 flex items-center gap-2">
                  <Tag className="w-4 h-4" />
                  Preferred Categories
                </label>
                <div className="flex flex-wrap gap-2 mb-3">
                  {preferredCategories.map((category) => (
                    <span
                      key={category}
                      className="inline-flex items-center gap-2 px-3 py-1 bg-pinterest-red text-white rounded-full text-sm"
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
                    className="flex-1 px-4 py-2 border border-light-gray rounded-lg focus:outline-none focus:ring-2 focus:ring-pinterest-red/50"
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        addCategory((e.target as HTMLInputElement).value);
                        (e.target as HTMLInputElement).value = "";
                      }
                    }}
                  />
                </div>
                <p className="text-xs text-gray mt-2">
                  Press Enter to add a category
                </p>
              </div>

              {/* Save Button */}
              <div className="flex items-center gap-3">
                <button
                  onClick={handleSavePreferences}
                  disabled={updatePreferences.isPending}
                  className="flex items-center gap-2 px-6 py-3 bg-pinterest-red text-white rounded-lg hover:bg-dark-red transition-colors disabled:opacity-50 active:scale-95"
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
      </div>
    </div>
  );
}
