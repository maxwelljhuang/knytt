"use client";

import { useUserStats } from "@/lib/queries/user";
import { Eye, MousePointer, Heart, ShoppingCart, DollarSign, TrendingUp, Tag, Package } from "lucide-react";

export function ProfileOverview() {
  const { data: stats, isLoading } = useUserStats();

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="bg-white rounded-2xl shadow-sm border border-light-gray p-6 h-48" />
        <div className="bg-white rounded-2xl shadow-sm border border-light-gray p-6 h-64" />
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="bg-white rounded-2xl shadow-sm border border-light-gray p-12 text-center">
        <p className="text-gray">No statistics available yet.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Interaction Stats */}
      <div className="bg-white rounded-2xl shadow-sm border border-light-gray p-6">
        <h2 className="text-xl font-bold text-charcoal mb-6 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-pinterest-red" />
          Your Activity
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <StatCard
            icon={<Eye className="w-5 h-5" />}
            label="Views"
            value={stats.total_views}
            color="text-blue-600"
          />
          <StatCard
            icon={<MousePointer className="w-5 h-5" />}
            label="Clicks"
            value={stats.total_clicks}
            color="text-purple-600"
          />
          <StatCard
            icon={<Heart className="w-5 h-5" />}
            label="Likes"
            value={stats.total_likes}
            color="text-pinterest-red"
          />
          <StatCard
            icon={<ShoppingCart className="w-5 h-5" />}
            label="Cart Adds"
            value={stats.total_cart_adds}
            color="text-green-600"
          />
          <StatCard
            icon={<Package className="w-5 h-5" />}
            label="Purchases"
            value={stats.total_purchases}
            color="text-orange-600"
          />
        </div>
      </div>

      {/* Shopping Insights */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Average Price Point */}
        <div className="bg-white rounded-2xl shadow-sm border border-light-gray p-6">
          <h3 className="text-lg font-bold text-charcoal mb-4 flex items-center gap-2">
            <DollarSign className="w-5 h-5 text-pinterest-red" />
            Average Price Point
          </h3>
          <div className="text-center py-6">
            <p className="text-4xl font-bold text-pinterest-red">
              ${stats.avg_price_point?.toFixed(2) || "0.00"}
            </p>
            <p className="text-sm text-gray mt-2">Across all interactions</p>
          </div>
        </div>

        {/* Account Stats */}
        <div className="bg-white rounded-2xl shadow-sm border border-light-gray p-6">
          <h3 className="text-lg font-bold text-charcoal mb-4">Account Info</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center py-2 border-b border-light-gray">
              <span className="text-gray">Total Interactions</span>
              <span className="font-semibold text-charcoal">{stats.total_interactions}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-light-gray">
              <span className="text-gray">Days Active</span>
              <span className="font-semibold text-charcoal">{stats.account_age_days}</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-gray">Last Active</span>
              <span className="font-semibold text-charcoal">
                {stats.last_active ? new Date(stats.last_active).toLocaleDateString() : "N/A"}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Top Categories */}
      {stats.favorite_categories && stats.favorite_categories.length > 0 && (
        <div className="bg-white rounded-2xl shadow-sm border border-light-gray p-6">
          <h3 className="text-lg font-bold text-charcoal mb-4 flex items-center gap-2">
            <Tag className="w-5 h-5 text-pinterest-red" />
            Top Categories
          </h3>
          <div className="flex flex-wrap gap-2">
            {stats.favorite_categories.slice(0, 10).map((cat, index) => (
              <div
                key={index}
                className="px-4 py-2 bg-light-gray rounded-full flex items-center gap-2"
              >
                <span className="text-sm font-medium text-charcoal">{cat.category}</span>
                <span className="text-xs text-gray bg-white px-2 py-0.5 rounded-full">
                  {cat.count}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top Brands */}
      {stats.favorite_brands && stats.favorite_brands.length > 0 && (
        <div className="bg-white rounded-2xl shadow-sm border border-light-gray p-6">
          <h3 className="text-lg font-bold text-charcoal mb-4 flex items-center gap-2">
            <Package className="w-5 h-5 text-pinterest-red" />
            Favorite Brands
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {stats.favorite_brands.slice(0, 10).map((brand, index) => (
              <div
                key={index}
                className="p-4 bg-light-gray rounded-lg text-center hover:bg-gray-200 transition-colors"
              >
                <p className="font-semibold text-charcoal text-sm truncate">
                  {brand.brand}
                </p>
                <p className="text-xs text-gray mt-1">{brand.count} items</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

interface StatCardProps {
  icon: ReactNode;
  label: string;
  value: number;
  color: string;
}

function StatCard({ icon, label, value, color }: StatCardProps) {
  return (
    <div className="p-4 bg-light-gray rounded-xl hover:shadow-md transition-shadow">
      <div className={`${color} mb-2`}>{icon}</div>
      <p className="text-2xl font-bold text-charcoal">{value}</p>
      <p className="text-sm text-gray">{label}</p>
    </div>
  );
}
