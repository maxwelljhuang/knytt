"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/queries/auth";
import { MoodboardSelector } from "@/components/onboarding/MoodboardSelector";
import { PriceRangeSelector } from "@/components/onboarding/PriceRangeSelector";
import { CheckCircle, ChevronRight } from "lucide-react";

export default function OnboardingPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const [currentStep, setCurrentStep] = useState(1);
  const [selectedProducts, setSelectedProducts] = useState<string[]>([]);
  const [priceRange, setPriceRange] = useState<{
    min: number | null;
    max: number | null;
  }>({ min: null, max: null });

  // Handle authentication and onboarding status
  useEffect(() => {
    // Wait for auth to load before making any decisions
    if (!authLoading) {
      if (!isAuthenticated) {
        router.push("/login");
      } else if (user?.onboarded) {
        // If user is already onboarded, redirect to feed
        router.push("/feed");
      }
    }
  }, [authLoading, isAuthenticated, user?.onboarded, router]);

  const totalSteps = 2;

  const handleMoodboardComplete = (products: string[]) => {
    setSelectedProducts(products);
    setCurrentStep(2);
  };

  const handlePriceRangeComplete = (min: number | null, max: number | null) => {
    setPriceRange({ min, max });
    // This will trigger the API call in the PriceRangeSelector component
  };

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-pulse text-pinterest-red">Loading...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null; // Will redirect
  }

  return (
    <div className="min-h-screen bg-ivory">
      {/* Header */}
      <div className="bg-white border-b border-light-gray sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-charcoal">
                Welcome to Knytt
              </h1>
              <p className="text-gray text-sm mt-1">
                Let's personalize your experience
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray">
                Step {currentStep} of {totalSteps}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="bg-white border-b border-light-gray">
        <div className="container mx-auto px-4">
          <div className="flex items-center py-3">
            {[1, 2].map((step) => (
              <div key={step} className="flex-1 flex items-center">
                <div className="flex items-center">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors ${
                      step < currentStep
                        ? "bg-pinterest-red text-white"
                        : step === currentStep
                        ? "bg-pinterest-red text-white"
                        : "bg-light-gray text-gray"
                    }`}
                  >
                    {step < currentStep ? (
                      <CheckCircle className="w-5 h-5" />
                    ) : (
                      step
                    )}
                  </div>
                  <span
                    className={`ml-3 text-sm font-medium ${
                      step <= currentStep ? "text-charcoal" : "text-gray"
                    }`}
                  >
                    {step === 1 ? "Choose Your Style" : "Set Your Budget"}
                  </span>
                </div>
                {step < totalSteps && (
                  <div className="flex-1 mx-4">
                    <div className="h-1 bg-light-gray rounded-full">
                      <div
                        className={`h-1 rounded-full transition-all ${
                          step < currentStep
                            ? "bg-pinterest-red w-full"
                            : "bg-light-gray w-0"
                        }`}
                      />
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="container mx-auto px-4 py-8">
        {currentStep === 1 && (
          <div>
            <div className="max-w-3xl mx-auto text-center mb-8">
              <h2 className="text-3xl font-bold text-charcoal mb-4">
                Select styles you love
              </h2>
              <p className="text-gray text-lg">
                Choose 3-5 products that match your personal style. This helps us
                understand your preferences and recommend products you'll love.
              </p>
            </div>
            <MoodboardSelector
              onComplete={handleMoodboardComplete}
              minSelection={3}
              maxSelection={5}
            />
          </div>
        )}

        {currentStep === 2 && (
          <div>
            <div className="max-w-3xl mx-auto text-center mb-8">
              <h2 className="text-3xl font-bold text-charcoal mb-4">
                Set your budget
              </h2>
              <p className="text-gray text-lg">
                Help us recommend products within your preferred price range.
                You can always adjust this later.
              </p>
            </div>
            <PriceRangeSelector
              selectedProducts={selectedProducts}
              onComplete={handlePriceRangeComplete}
            />
          </div>
        )}
      </div>
    </div>
  );
}