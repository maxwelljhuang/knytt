"use client";

import { useState } from "react";
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

const INTERACTION_TYPES = [
  { value: "", label: "All", icon: History },
  { value: "view", label: "Views", icon: Eye },
  { value: "click", label: "Clicks", icon: MousePointer },
  { value: "like", label: "Likes", icon: Heart },
  { value: "add_to_cart", label: "Cart Adds", icon: ShoppingCart },
  { value: "purchase", label: "Purchases", icon: CreditCard },
];

export default function HistoryContent() {
  const [selectedType, setSelectedType] = useState("");
  const [limit] = useState(50);

  const { data: history, isLoading } = useInteractionHistory(
    selectedType || undefined,
    limit,
    0
  );

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
        return "text-pinterest-red bg-red-50";
      case "add_to_cart":
        return "text-green-600 bg-green-50";
      case "purchase":
        return "text-yellow-600 bg-yellow-50";
      default:
        return "text-gray-500 bg-gray-50";
    }
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-2xl shadow-sm border border-light-gray p-12 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-pinterest-red animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Filter Tabs */}
      <div className="bg-white rounded-2xl shadow-sm border border-light-gray p-4">
        <div className="flex items-center gap-2 overflow-x-auto pb-2">
          <Filter className="w-5 h-5 text-gray flex-shrink-0" />
          <div className="flex gap-2">
            {INTERACTION_TYPES.map((type) => {
              const Icon = type.icon;
              return (
                <button
                  key={type.value}
                  onClick={() => setSelectedType(type.value)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all whitespace-nowrap active:scale-95 ${
                    selectedType === type.value
                      ? "bg-pinterest-red text-white shadow-md"
                      : "bg-light-gray text-charcoal hover:bg-gray-200"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {type.label}
                </button>
              );
            })}
          </div>
        </div>
        <p className="text-gray text-sm mt-3">
          {history?.total || 0} total interactions
        </p>
      </div>

      {/* Empty State */}
      {(!history || history.total === 0) && (
        <div className="bg-white rounded-2xl shadow-sm border border-light-gray p-12 text-center">
          <History className="w-16 h-16 text-gray/30 mx-auto mb-4" />
          <h2 className="text-2xl font-semibold text-charcoal mb-2">
            No interactions yet
          </h2>
          <p className="text-gray mb-6">
            Start exploring products to see your activity here
          </p>
          <Link
            href="/"
            className="inline-block px-6 py-3 bg-pinterest-red text-white rounded-full hover:bg-dark-red transition-colors"
          >
            Discover Products
          </Link>
        </div>
      )}

      {/* History Timeline */}
      {history && history.total > 0 && (
        <div className="space-y-4">
          {history.interactions.map((interaction) => {
            const Icon = getInteractionIcon(interaction.interaction_type);
            const colorClass = getInteractionColor(interaction.interaction_type);

            return (
              <Link
                key={interaction.interaction_id}
                href={`/products/${interaction.product_id}`}
                className="block bg-white rounded-2xl shadow-sm border border-light-gray p-4 hover:shadow-md transition-all"
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
                      <div className="w-20 h-20 bg-light-gray rounded-lg flex items-center justify-center">
                        <span className="text-xs text-gray">No image</span>
                      </div>
                    )}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-4 mb-2">
                      <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-charcoal truncate">
                          {interaction.product_title || interaction.product_id}
                        </h3>
                        <p className="text-sm text-gray capitalize">
                          {interaction.interaction_type.replace("_", " ")}
                        </p>
                      </div>
                      {interaction.product_price && (
                        <p className="text-lg font-bold text-charcoal whitespace-nowrap">
                          ${interaction.product_price.toFixed(2)}
                        </p>
                      )}
                    </div>

                    {/* Metadata */}
                    <div className="flex flex-wrap items-center gap-3 text-xs text-gray/60">
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
    </div>
  );
}
