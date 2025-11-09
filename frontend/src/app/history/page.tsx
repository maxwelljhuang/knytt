"use client";

import { useState } from "react";
import { useAuth } from "@/lib/queries/auth";
import { useInteractionHistory } from "@/lib/queries/user";
import {
  History,
  Eye,
  MousePointer,
  Heart,
  ShoppingCart,
  CreditCard,
  Filter,
  Loader2,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

const INTERACTION_TYPES = [
  { value: "", label: "All", icon: History },
  { value: "view", label: "Views", icon: Eye },
  { value: "click", label: "Clicks", icon: MousePointer },
  { value: "like", label: "Likes", icon: Heart },
  { value: "add_to_cart", label: "Cart Adds", icon: ShoppingCart },
  { value: "purchase", label: "Purchases", icon: CreditCard },
];

export default function HistoryPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const userId = user?.id ? Number(user.id) : undefined;
  const [selectedType, setSelectedType] = useState("");
  const [limit] = useState(50);

  const { data: history, isLoading: historyLoading } = useInteractionHistory(
    userId,
    { offset: 0, limit }
  );

  // Filter interactions by type (client-side)
  const filteredHistory = history
    ? {
        ...history,
        interactions: selectedType
          ? history.interactions.filter((i) => i.interaction_type === selectedType)
          : history.interactions,
        total: selectedType
          ? history.interactions.filter((i) => i.interaction_type === selectedType)
              .length
          : history.total,
      }
    : null;

  // Redirect to login if not authenticated
  if (!authLoading && !isAuthenticated) {
    router.push("/login?redirect=/history");
    return null;
  }

  const getInteractionIcon = (type: string) => {
    const interaction = INTERACTION_TYPES.find((t) => t.value === type);
    const Icon = interaction?.icon || History;
    return Icon;
  };

  const getInteractionColor = (type: string) => {
    switch (type) {
      case "view":
        return "text-blue-500 bg-blue-50";
      case "click":
        return "text-purple-500 bg-purple-50";
      case "like":
        return "text-terracotta bg-red-50";
      case "add_to_cart":
        return "text-sage bg-green-50";
      case "purchase":
        return "text-yellow-600 bg-yellow-50";
      default:
        return "text-gray-500 bg-gray-50";
    }
  };

  if (authLoading || historyLoading) {
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

  return (
    <div className="min-h-screen bg-ivory">
      <div className="container mx-auto px-4 py-12">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <History className="w-8 h-8 text-evergreen" />
            <h1 className="text-4xl font-bold text-evergreen">
              Interaction History
            </h1>
          </div>
          <p className="text-sage">
            {filteredHistory?.total || 0} total interactions
          </p>
        </div>

        {/* Filter Tabs */}
        <div className="mb-6 flex items-center gap-2 overflow-x-auto pb-2">
          <Filter className="w-5 h-5 text-sage flex-shrink-0" />
          {INTERACTION_TYPES.map((type) => {
            const Icon = type.icon;
            return (
              <button
                key={type.value}
                onClick={() => setSelectedType(type.value)}
                className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-colors whitespace-nowrap ${
                  selectedType === type.value
                    ? "bg-evergreen text-white"
                    : "bg-white text-evergreen hover:bg-blush"
                }`}
              >
                <Icon className="w-4 h-4" />
                {type.label}
              </button>
            );
          })}
        </div>

        {/* Empty State */}
        {(!filteredHistory || filteredHistory.total === 0) && (
          <div className="text-center py-20">
            <History className="w-16 h-16 text-sage/30 mx-auto mb-4" />
            <h2 className="text-2xl font-semibold text-evergreen mb-2">
              No interactions yet
            </h2>
            <p className="text-sage mb-6">
              Start exploring products to see your activity here
            </p>
            <Link
              href="/"
              className="inline-block px-6 py-3 bg-terracotta text-white rounded-full hover:bg-terracotta/90 transition-colors"
            >
              Discover Products
            </Link>
          </div>
        )}

        {/* History Timeline */}
        {filteredHistory && filteredHistory.total > 0 && (
          <div className="space-y-4">
            {filteredHistory.interactions.map((interaction) => {
              const Icon = getInteractionIcon(interaction.interaction_type);
              const colorClass = getInteractionColor(interaction.interaction_type);

              return (
                <Link
                  key={interaction.interaction_id}
                  href={`/products/${interaction.product_id}`}
                  className="block bg-white rounded-xl p-4 hover:shadow-md transition-all"
                >
                  <div className="flex items-start gap-4">
                    {/* Icon */}
                    <div className={`p-3 rounded-full ${colorClass} flex-shrink-0`}>
                      <Icon className="w-5 h-5" />
                    </div>

                    {/* Product Image */}
                    <div className="flex-shrink-0">
                      {interaction.product_image_url ? (
                        <img
                          src={interaction.product_image_url}
                          alt={interaction.product_title || "Product"}
                          className="w-20 h-20 object-cover rounded-lg"
                        />
                      ) : (
                        <div className="w-20 h-20 bg-blush rounded-lg flex items-center justify-center">
                          <span className="text-xs text-sage">No image</span>
                        </div>
                      )}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-4 mb-2">
                        <div className="flex-1 min-w-0">
                          <h3 className="font-semibold text-evergreen truncate">
                            {interaction.product_title || interaction.product_id}
                          </h3>
                          <p className="text-sm text-sage capitalize">
                            {interaction.interaction_type.replace("_", " ")}
                          </p>
                        </div>
                        {interaction.product_price && (
                          <p className="text-lg font-bold text-evergreen whitespace-nowrap">
                            ${interaction.product_price.toFixed(2)}
                          </p>
                        )}
                      </div>

                      {/* Metadata */}
                      <div className="flex flex-wrap items-center gap-3 text-xs text-sage/60">
                        <span>
                          {new Date(interaction.created_at).toLocaleDateString(
                            "en-US",
                            {
                              month: "short",
                              day: "numeric",
                              year: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            }
                          )}
                        </span>
                        {interaction.context && (
                          <>
                            <span>•</span>
                            <span className="capitalize">{interaction.context}</span>
                          </>
                        )}
                        {interaction.query && (
                          <>
                            <span>•</span>
                            <span>Query: "{interaction.query}"</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        )}

        {/* Load More (Future Enhancement) */}
        {filteredHistory && filteredHistory.total > filteredHistory.interactions.length && (
          <div className="mt-8 text-center">
            <button className="px-6 py-3 bg-white text-evergreen rounded-full hover:bg-blush transition-colors">
              Load More
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
