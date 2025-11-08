"use client";

import { User as UserIcon, Calendar, Activity, Heart, Eye, MousePointer } from "lucide-react";
import { useAuth } from "@/lib/queries/auth";
import { useUserStats, useUserFavorites } from "@/lib/queries/user";

export function ProfileHeader() {
  const { user } = useAuth();
  const { data: stats } = useUserStats();
  const { data: favorites } = useUserFavorites();

  if (!user) return null;

  // Get initials from email
  const getInitials = (email: string) => {
    return email.charAt(0).toUpperCase();
  };

  // Format member since date
  const formatMemberSince = (date: string) => {
    return new Date(date).toLocaleDateString('en-US', {
      month: 'long',
      year: 'numeric'
    });
  };

  // Get display name from email
  const displayName = user.email.split('@')[0];

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-light-gray p-8">
      <div className="flex flex-col md:flex-row items-center md:items-start gap-6">
        {/* Avatar */}
        <div className="w-24 h-24 bg-pinterest-red rounded-full flex items-center justify-center shadow-lg shrink-0">
          <span className="text-white font-bold text-4xl">
            {getInitials(user.email)}
          </span>
        </div>

        {/* User Info */}
        <div className="flex-1 text-center md:text-left">
          <h1 className="text-3xl font-bold text-charcoal mb-1">
            {displayName}
          </h1>
          <p className="text-gray mb-4">{user.email}</p>

          <div className="flex flex-wrap items-center justify-center md:justify-start gap-4 text-sm text-gray">
            <div className="flex items-center gap-1.5">
              <Calendar className="w-4 h-4" />
              <span>Joined {formatMemberSince(user.created_at)}</span>
            </div>
            {stats && (
              <div className="flex items-center gap-1.5">
                <Activity className="w-4 h-4" />
                <span>{stats.account_age_days} days active</span>
              </div>
            )}
          </div>
        </div>

        {/* Stats Summary */}
        <div className="grid grid-cols-3 gap-6 text-center">
          <div className="flex flex-col">
            <span className="text-2xl font-bold text-charcoal">
              {favorites?.length || 0}
            </span>
            <span className="text-sm text-gray flex items-center justify-center gap-1">
              <Heart className="w-3.5 h-3.5" />
              Favorites
            </span>
          </div>
          <div className="flex flex-col">
            <span className="text-2xl font-bold text-charcoal">
              {stats?.total_views || 0}
            </span>
            <span className="text-sm text-gray flex items-center justify-center gap-1">
              <Eye className="w-3.5 h-3.5" />
              Views
            </span>
          </div>
          <div className="flex flex-col">
            <span className="text-2xl font-bold text-charcoal">
              {stats?.total_interactions || 0}
            </span>
            <span className="text-sm text-gray flex items-center justify-center gap-1">
              <MousePointer className="w-3.5 h-3.5" />
              Interactions
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
