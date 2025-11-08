"use client";

import { useState, ReactNode } from "react";
import { LayoutDashboard, Heart, History, Settings } from "lucide-react";

interface Tab {
  id: string;
  label: string;
  icon: ReactNode;
}

const tabs: Tab[] = [
  { id: "overview", label: "Overview", icon: <LayoutDashboard className="w-4 h-4" /> },
  { id: "favorites", label: "Favorites", icon: <Heart className="w-4 h-4" /> },
  { id: "history", label: "History", icon: <History className="w-4 h-4" /> },
  { id: "settings", label: "Settings", icon: <Settings className="w-4 h-4" /> },
];

interface ProfileTabsProps {
  activeTab: string;
  onTabChange: (tabId: string) => void;
}

export function ProfileTabs({ activeTab, onTabChange }: ProfileTabsProps) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-light-gray p-2">
      <div className="flex flex-wrap gap-2">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`
              flex items-center gap-2 px-6 py-3 rounded-xl font-medium transition-all duration-[var(--duration-fast)]
              ${
                activeTab === tab.id
                  ? "bg-pinterest-red text-white shadow-md"
                  : "text-charcoal hover:bg-light-gray active:scale-95"
              }
            `}
          >
            {tab.icon}
            <span className="hidden sm:inline">{tab.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
