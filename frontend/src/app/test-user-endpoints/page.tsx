"use client";

import { useAuth } from "@/lib/queries/auth";
import {
  useFavorites,
  useUserStats,
  useInteractionHistory,
  useUpdatePreferences,
  useRemoveFavorite,
} from "@/lib/queries/user";
import { useState } from "react";

export default function TestUserEndpointsPage() {
  const { user, isAuthenticated } = useAuth();
  const { data: favorites, isLoading: favoritesLoading } = useFavorites(user?.id);
  const { data: stats, isLoading: statsLoading } = useUserStats(user?.id);
  const { data: history, isLoading: historyLoading } = useInteractionHistory(user?.id);

  const updatePreferences = useUpdatePreferences();
  const removeFavorite = useRemoveFavorite();

  const [testCategory, setTestCategory] = useState("clothing");

  if (!isAuthenticated) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold mb-4">Test User Endpoints</h1>
        <p className="text-red-600">Please log in to test user endpoints</p>
      </div>
    );
  }

  const handleUpdatePreferences = () => {
    updatePreferences.mutate({
      preferred_categories: [testCategory, "accessories"],
      price_band_min: 10,
      price_band_max: 500,
    });
  };

  const handleRemoveFavorite = (productId: string) => {
    removeFavorite.mutate(productId);
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6 text-evergreen">Test User Endpoints</h1>

      {/* User Info */}
      <div className="mb-8 p-6 bg-white rounded-lg shadow">
        <h2 className="text-xl font-semibold mb-4 text-sage">Current User</h2>
        <pre className="bg-gray-100 p-4 rounded overflow-auto">
          {JSON.stringify(user, null, 2)}
        </pre>
      </div>

      {/* Favorites */}
      <div className="mb-8 p-6 bg-white rounded-lg shadow">
        <h2 className="text-xl font-semibold mb-4 text-sage">
          User Favorites (GET /users/me/favorites)
        </h2>
        {favoritesLoading ? (
          <p>Loading...</p>
        ) : favorites ? (
          <div>
            <p className="mb-2">Total: {favorites.total}</p>
            <div className="bg-gray-100 p-4 rounded overflow-auto max-h-96">
              {favorites.favorites.length > 0 ? (
                favorites.favorites.map((fav) => (
                  <div key={fav.product_id} className="mb-4 p-3 bg-white rounded">
                    <p className="font-semibold">{fav.title}</p>
                    <p className="text-sm text-gray-600">
                      {fav.currency}{fav.price} - {fav.brand}
                    </p>
                    <p className="text-xs text-gray-500">
                      Liked at: {new Date(fav.liked_at).toLocaleString()}
                    </p>
                    <button
                      onClick={() => handleRemoveFavorite(fav.product_id)}
                      className="mt-2 px-3 py-1 bg-red-500 text-white rounded text-sm"
                    >
                      Remove
                    </button>
                  </div>
                ))
              ) : (
                <p>No favorites yet</p>
              )}
            </div>
          </div>
        ) : (
          <p className="text-red-600">Error loading favorites</p>
        )}
      </div>

      {/* User Stats */}
      <div className="mb-8 p-6 bg-white rounded-lg shadow">
        <h2 className="text-xl font-semibold mb-4 text-sage">
          User Statistics (GET /users/me/stats)
        </h2>
        {statsLoading ? (
          <p>Loading...</p>
        ) : stats ? (
          <div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-4">
              <div className="p-3 bg-blush rounded">
                <p className="text-sm text-gray-600">Total Interactions</p>
                <p className="text-2xl font-bold text-evergreen">{stats.total_interactions}</p>
              </div>
              <div className="p-3 bg-blush rounded">
                <p className="text-sm text-gray-600">Views</p>
                <p className="text-2xl font-bold text-evergreen">{stats.total_views}</p>
              </div>
              <div className="p-3 bg-blush rounded">
                <p className="text-sm text-gray-600">Clicks</p>
                <p className="text-2xl font-bold text-evergreen">{stats.total_clicks}</p>
              </div>
              <div className="p-3 bg-blush rounded">
                <p className="text-sm text-gray-600">Likes</p>
                <p className="text-2xl font-bold text-evergreen">{stats.total_likes}</p>
              </div>
              <div className="p-3 bg-blush rounded">
                <p className="text-sm text-gray-600">Cart Adds</p>
                <p className="text-2xl font-bold text-evergreen">{stats.total_cart_adds}</p>
              </div>
              <div className="p-3 bg-blush rounded">
                <p className="text-sm text-gray-600">Purchases</p>
                <p className="text-2xl font-bold text-evergreen">{stats.total_purchases}</p>
              </div>
            </div>
            <div className="bg-gray-100 p-4 rounded overflow-auto max-h-96">
              <pre>{JSON.stringify(stats, null, 2)}</pre>
            </div>
          </div>
        ) : (
          <p className="text-red-600">Error loading stats</p>
        )}
      </div>

      {/* Interaction History */}
      <div className="mb-8 p-6 bg-white rounded-lg shadow">
        <h2 className="text-xl font-semibold mb-4 text-sage">
          Interaction History (GET /users/me/history)
        </h2>
        {historyLoading ? (
          <p>Loading...</p>
        ) : history ? (
          <div>
            <p className="mb-2">Total: {history.total}</p>
            <div className="bg-gray-100 p-4 rounded overflow-auto max-h-96">
              {history.interactions.length > 0 ? (
                history.interactions.map((item) => (
                  <div key={item.interaction_id} className="mb-3 p-3 bg-white rounded">
                    <p className="font-semibold">{item.product_title || item.product_id}</p>
                    <p className="text-sm text-gray-600">
                      Type: {item.interaction_type}
                    </p>
                    <p className="text-xs text-gray-500">
                      {new Date(item.created_at).toLocaleString()}
                    </p>
                    {item.query && (
                      <p className="text-xs text-gray-500">Query: {item.query}</p>
                    )}
                  </div>
                ))
              ) : (
                <p>No interactions yet</p>
              )}
            </div>
          </div>
        ) : (
          <p className="text-red-600">Error loading history</p>
        )}
      </div>

      {/* Update Preferences */}
      <div className="mb-8 p-6 bg-white rounded-lg shadow">
        <h2 className="text-xl font-semibold mb-4 text-sage">
          Update Preferences (PUT /users/me/preferences)
        </h2>
        <div className="flex gap-4 items-end">
          <div>
            <label className="block text-sm mb-1">Test Category:</label>
            <input
              type="text"
              value={testCategory}
              onChange={(e) => setTestCategory(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded"
            />
          </div>
          <button
            onClick={handleUpdatePreferences}
            disabled={updatePreferences.isPending}
            className="px-4 py-2 bg-sage text-white rounded hover:bg-evergreen disabled:opacity-50"
          >
            {updatePreferences.isPending ? "Updating..." : "Update Preferences"}
          </button>
        </div>
        {updatePreferences.isSuccess && (
          <p className="mt-2 text-green-600">Preferences updated successfully!</p>
        )}
        {updatePreferences.isError && (
          <p className="mt-2 text-red-600">Error updating preferences</p>
        )}
      </div>
    </div>
  );
}
