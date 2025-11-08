"use client";

import { useState, Suspense, lazy } from "react";
import { useAuth } from "@/lib/queries/auth";
import { useRouter } from "next/navigation";
import { ProfileHeader } from "@/components/profile/ProfileHeader";
import { ProfileTabs } from "@/components/profile/ProfileTabs";
import { ProfileOverview } from "@/components/profile/ProfileOverview";
import { Loader2 } from "lucide-react";

// Lazy load the tab content components
const FavoritesContent = lazy(() => import("@/components/profile/FavoritesContent"));
const HistoryContent = lazy(() => import("@/components/profile/HistoryContent"));
const SettingsContent = lazy(() => import("@/components/profile/SettingsContent"));

export default function ProfilePage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [activeTab, setActiveTab] = useState("overview");

  // Redirect to login if not authenticated
  if (!authLoading && !isAuthenticated) {
    router.push("/login?redirect=/profile");
    return null;
  }

  if (authLoading) {
    return (
      <div className="min-h-screen bg-ivory flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-pinterest-red animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-ivory py-8">
      <div className="container mx-auto px-4 max-w-7xl">
        <div className="space-y-6">
          {/* Profile Header */}
          <ProfileHeader />

          {/* Tabs Navigation */}
          <ProfileTabs activeTab={activeTab} onTabChange={setActiveTab} />

          {/* Tab Content */}
          <div className="min-h-[500px]">
            <Suspense
              fallback={
                <div className="bg-white rounded-2xl shadow-sm border border-light-gray p-12 flex items-center justify-center">
                  <Loader2 className="w-8 h-8 text-pinterest-red animate-spin" />
                </div>
              }
            >
              {activeTab === "overview" && <ProfileOverview />}
              {activeTab === "favorites" && <FavoritesContent />}
              {activeTab === "history" && <HistoryContent />}
              {activeTab === "settings" && <SettingsContent />}
            </Suspense>
          </div>
        </div>
      </div>
    </div>
  );
}
