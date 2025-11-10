"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useCompleteOnboarding } from "@/lib/queries/onboarding";
import { DollarSign, Loader2 } from "lucide-react";

interface PriceRangeSelectorProps {
  selectedProducts: string[];
  onComplete: (min: number | null, max: number | null) => void;
}

export function PriceRangeSelector({
  selectedProducts,
  onComplete,
}: PriceRangeSelectorProps) {
  const router = useRouter();
  const [priceMin, setPriceMin] = useState<string>("");
  const [priceMax, setPriceMax] = useState<string>("");
  const [selectedRange, setSelectedRange] = useState<string | null>(null);

  const { mutate: completeOnboarding, isPending } = useCompleteOnboarding();

  const priceRanges = [
    { id: "budget", label: "Budget Friendly", min: 0, max: 50 },
    { id: "moderate", label: "Moderate", min: 50, max: 150 },
    { id: "premium", label: "Premium", min: 150, max: 500 },
    { id: "luxury", label: "Luxury", min: 500, max: null },
    { id: "custom", label: "Custom Range", min: null, max: null },
  ];

  const handleRangeSelect = (rangeId: string) => {
    setSelectedRange(rangeId);
    const range = priceRanges.find((r) => r.id === rangeId);
    if (range && rangeId !== "custom") {
      setPriceMin(range.min?.toString() || "");
      setPriceMax(range.max?.toString() || "");
    }
  };

  const handleComplete = () => {
    const min = priceMin ? parseFloat(priceMin) : null;
    const max = priceMax ? parseFloat(priceMax) : null;

    // Validate range
    if (min !== null && max !== null && min > max) {
      alert("Minimum price must be less than maximum price");
      return;
    }

    // Call the complete onboarding mutation
    completeOnboarding(
      {
        selected_product_ids: selectedProducts,
        price_min: min,
        price_max: max,
      },
      {
        onSuccess: (data) => {
          onComplete(min, max);
          // Redirect to feed or next step
          router.push(data.next_step || "/feed");
        },
        onError: (error) => {
          console.error("Failed to complete onboarding:", error);
          alert("Failed to complete setup. Please try again.");
        },
      }
    );
  };

  const handleSkip = () => {
    // Complete onboarding without price preferences
    completeOnboarding(
      {
        selected_product_ids: selectedProducts,
        price_min: null,
        price_max: null,
      },
      {
        onSuccess: (data) => {
          onComplete(null, null);
          router.push(data.next_step || "/feed");
        },
        onError: (error) => {
          console.error("Failed to complete onboarding:", error);
          alert("Failed to complete setup. Please try again.");
        },
      }
    );
  };

  return (
    <div className="max-w-2xl mx-auto">
      {/* Quick Select Options */}
      <div className="mb-8">
        <h3 className="text-lg font-semibold text-charcoal mb-4">
          Quick Select
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {priceRanges.map((range) => (
            <button
              key={range.id}
              onClick={() => handleRangeSelect(range.id)}
              className={`p-4 rounded-xl border-2 transition-all ${
                selectedRange === range.id
                  ? "border-pinterest-red bg-pinterest-red/5"
                  : "border-light-gray hover:border-gray"
              }`}
            >
              <div className="text-left">
                <p className="font-medium text-charcoal">{range.label}</p>
                <p className="text-sm text-gray mt-1">
                  {range.id === "custom"
                    ? "Set your own"
                    : range.max
                    ? `$${range.min} - $${range.max}`
                    : `$${range.min}+`}
                </p>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Custom Range Inputs */}
      <div className="bg-light-gray/50 rounded-2xl p-6 mb-8">
        <h3 className="text-lg font-semibold text-charcoal mb-4 flex items-center gap-2">
          <DollarSign className="w-5 h-5 text-pinterest-red" />
          Set Your Range
        </h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="min-price" className="block text-sm text-gray mb-2">
              Minimum Price
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray">
                $
              </span>
              <input
                id="min-price"
                type="number"
                value={priceMin}
                onChange={(e) => {
                  setPriceMin(e.target.value);
                  setSelectedRange("custom");
                }}
                placeholder="0"
                min="0"
                className="w-full pl-8 pr-3 py-3 rounded-xl border border-light-gray focus:border-pinterest-red focus:outline-none focus:ring-2 focus:ring-pinterest-red/20"
              />
            </div>
          </div>
          <div>
            <label htmlFor="max-price" className="block text-sm text-gray mb-2">
              Maximum Price
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray">
                $
              </span>
              <input
                id="max-price"
                type="number"
                value={priceMax}
                onChange={(e) => {
                  setPriceMax(e.target.value);
                  setSelectedRange("custom");
                }}
                placeholder="No limit"
                min="0"
                className="w-full pl-8 pr-3 py-3 rounded-xl border border-light-gray focus:border-pinterest-red focus:outline-none focus:ring-2 focus:ring-pinterest-red/20"
              />
            </div>
          </div>
        </div>
        {priceMin && priceMax && parseFloat(priceMin) > parseFloat(priceMax) && (
          <p className="text-red-500 text-sm mt-2">
            Minimum price must be less than maximum price
          </p>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row gap-3">
        <button
          onClick={handleSkip}
          disabled={isPending}
          className="flex-1 px-6 py-3 rounded-full font-medium border-2 border-light-gray text-gray hover:border-gray transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Skip for now
        </button>
        <button
          onClick={handleComplete}
          disabled={
            isPending ||
            !!(priceMin && priceMax && parseFloat(priceMin) > parseFloat(priceMax))
          }
          className="flex-1 px-6 py-3 rounded-full font-medium bg-pinterest-red text-white hover:bg-dark-red transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 active:scale-95"
        >
          {isPending ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Setting up your profile...
            </>
          ) : (
            "Complete Setup"
          )}
        </button>
      </div>

      {/* Info Text */}
      <p className="text-center text-sm text-gray mt-6">
        You can always update your preferences later in settings
      </p>
    </div>
  );
}