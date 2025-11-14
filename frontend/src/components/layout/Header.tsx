"use client";

import Link from "next/link";
import Image from "next/image";
import { Search, Heart, ShoppingBag, User, LogOut, Settings, History, Sparkles, Menu, X } from "lucide-react";
import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuth, useLogout } from "@/lib/queries/auth";
import { useCartStore } from "@/lib/stores/cartStore";
import Tooltip from "@/components/ui/Tooltip";

export function Header() {
  const [searchQuery, setSearchQuery] = useState("");
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showMobileMenu, setShowMobileMenu] = useState(false);
  const router = useRouter();
  const { user, isAuthenticated } = useAuth();
  const logoutMutation = useLogout();
  const cartItemCount = useCartStore((state) => state.getItemCount());
  const userMenuRef = useRef<HTMLDivElement>(null);
  const mobileMenuRef = useRef<HTMLDivElement>(null);

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setShowUserMenu(false);
      }
      if (mobileMenuRef.current && !mobileMenuRef.current.contains(event.target as Node)) {
        setShowMobileMenu(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Prevent body scroll when mobile menu is open
  useEffect(() => {
    if (showMobileMenu) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [showMobileMenu]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      router.push(`/search?q=${encodeURIComponent(searchQuery)}`);
    }
  };

  const handleLogout = () => {
    logoutMutation.mutate(undefined, {
      onSuccess: () => {
        setShowUserMenu(false);
        router.push("/");
      },
    });
  };

  return (
    <header className="sticky top-0 z-[var(--z-sticky)] glass border-b border-light-gray">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between gap-4">
          {/* Mobile Menu Button */}
          <button
            onClick={() => setShowMobileMenu(!showMobileMenu)}
            className="md:hidden p-2 hover:bg-light-gray rounded-lg transition-all active:scale-95"
            aria-label="Toggle mobile menu"
          >
            {showMobileMenu ? (
              <X className="w-6 h-6 text-charcoal" />
            ) : (
              <Menu className="w-6 h-6 text-charcoal" />
            )}
          </button>

          {/* Logo */}
          <Link href="/" className="flex items-center gap-3 group">
            <div className="relative w-12 h-12 flex-shrink-0">
              <Image
                src="/knytt-logo-circle.png"
                alt="Knytt Logo"
                width={48}
                height={48}
                className="rounded-full shadow-md group-hover:shadow-xl transition-all group-hover:scale-110"
                priority
                onError={(e) => {
                  // Fallback if logo not found
                  e.currentTarget.style.display = 'none';
                  e.currentTarget.parentElement!.innerHTML = `
                    <div class="w-12 h-12 bg-evergreen rounded-full flex items-center justify-center shadow-md group-hover:shadow-xl transition-all group-hover:scale-110">
                      <span class="text-white font-bold text-xl">K</span>
                    </div>
                  `;
                }}
              />
            </div>
            <span className="text-2xl font-bold text-evergreen group-hover:text-sage transition-colors duration-[var(--duration-fast)]">
              Knytt
            </span>
          </Link>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-6">
            <Link
              href="/"
              className="text-charcoal hover:text-pinterest-red transition-colors font-medium"
            >
              Discover
            </Link>
            {isAuthenticated && (
              <Link
                href="/feed"
                className="text-charcoal hover:text-pinterest-red transition-colors font-medium flex items-center gap-1"
              >
                <Sparkles className="w-4 h-4" />
                For You
              </Link>
            )}
            <Link
              href="/search"
              className="text-charcoal hover:text-pinterest-red transition-colors font-medium"
            >
              Search
            </Link>
          </nav>

          {/* Search Bar */}
          <form onSubmit={handleSearch} className="flex-1 max-w-2xl hidden lg:block">
            <div className="relative group">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray group-focus-within:text-pinterest-red transition-colors" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search for products..."
                className="w-full pl-12 pr-4 py-3 bg-white border-2 border-light-gray rounded-full focus:outline-none focus:ring-4 focus:ring-pinterest-red/20 focus:border-pinterest-red transition-all duration-[var(--duration-fast)] shadow-sm focus:shadow-md"
              />
            </div>
          </form>

          {/* Action Icons */}
          <div className="flex items-center gap-3">
            {/* Mobile Search */}
            <Link
              href="/search"
              className="lg:hidden p-2 hover:bg-light-gray rounded-full transition-colors"
            >
              <Search className="w-5 h-5 text-charcoal" />
            </Link>

            {/* Favorites */}
            <Tooltip content="Favorites">
              <Link
                href="/favorites"
                className="p-2.5 hover:bg-light-gray rounded-full transition-all duration-[var(--duration-fast)] group relative active:scale-95"
              >
                <Heart className="w-5 h-5 text-charcoal group-hover:text-pinterest-red transition-colors group-hover:scale-110" />
              </Link>
            </Tooltip>

            {/* Cart */}
            <Tooltip content="Shopping Cart">
              <Link
                href="/cart"
                className="p-2.5 hover:bg-light-gray rounded-full transition-all duration-[var(--duration-fast)] group relative active:scale-95"
              >
                <ShoppingBag className="w-5 h-5 text-charcoal group-hover:text-pinterest-red transition-colors group-hover:scale-110" />
                {cartItemCount > 0 && (
                  <span className="absolute -top-1 -right-1 min-w-[20px] h-5 px-1.5 bg-pinterest-red text-white text-xs rounded-full flex items-center justify-center font-medium shadow-md animate-scale-in">
                    {cartItemCount}
                  </span>
                )}
              </Link>
            </Tooltip>

            {/* User Profile / Auth */}
            {isAuthenticated && user ? (
              <div className="relative" ref={userMenuRef}>
                <button
                  onClick={() => setShowUserMenu(!showUserMenu)}
                  className="flex items-center gap-2 p-2 hover:bg-light-gray rounded-full transition-all duration-[var(--duration-fast)] active:scale-95"
                >
                  <User className="w-5 h-5 text-charcoal" />
                  <span className="hidden sm:block text-sm text-charcoal font-medium">
                    {user.email.split('@')[0]}
                  </span>
                </button>

                {/* User Dropdown Menu */}
                {showUserMenu && (
                  <div className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-xl border-2 border-light-gray py-2 z-[var(--z-dropdown)] animate-slide-down">
                    <div className="px-4 py-2 border-b border-light-gray">
                      <p className="text-sm font-medium text-charcoal">
                        {user.email}
                      </p>
                      <p className="text-xs text-gray">
                        {user.total_interactions} interactions
                      </p>
                    </div>

                    <button
                      onClick={() => {
                        router.push('/favorites');
                        setShowUserMenu(false);
                      }}
                      className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-light-gray transition-all duration-[var(--duration-fast)] text-left group"
                    >
                      <Heart className="w-4 h-4 text-pinterest-red group-hover:scale-110 transition-transform" />
                      <span className="text-sm text-charcoal font-medium">Favorites</span>
                    </button>

                    <button
                      onClick={() => {
                        router.push('/history');
                        setShowUserMenu(false);
                      }}
                      className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-light-gray transition-all duration-[var(--duration-fast)] text-left group"
                    >
                      <History className="w-4 h-4 text-gray group-hover:scale-110 transition-transform" />
                      <span className="text-sm text-charcoal font-medium">History</span>
                    </button>

                    <button
                      onClick={() => {
                        router.push('/settings');
                        setShowUserMenu(false);
                      }}
                      className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-light-gray transition-all duration-[var(--duration-fast)] text-left group"
                    >
                      <Settings className="w-4 h-4 text-gray group-hover:scale-110 transition-transform" />
                      <span className="text-sm text-charcoal font-medium">Settings</span>
                    </button>

                    <div className="border-t border-light-gray my-1" />

                    <button
                      onClick={handleLogout}
                      className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-red-50 transition-all duration-[var(--duration-fast)] text-left group"
                    >
                      <LogOut className="w-4 h-4 text-red-600 group-hover:scale-110 transition-transform" />
                      <span className="text-sm text-red-600 font-medium">Logout</span>
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link
                  href="/login"
                  className="px-4 py-2 text-sm font-medium text-charcoal hover:text-pinterest-red transition-colors"
                >
                  Login
                </Link>
                <Link
                  href="/register"
                  className="px-4 py-2 text-sm font-medium bg-pinterest-red text-white rounded-full hover:bg-dark-red transition-colors"
                >
                  Sign Up
                </Link>
              </div>
            )}
          </div>
        </div>

        {/* Mobile Menu */}
        {showMobileMenu && (
          <div
            ref={mobileMenuRef}
            className="md:hidden fixed inset-0 top-[73px] bg-ivory z-[var(--z-overlay)] animate-fade-in"
          >
            <nav className="flex flex-col p-6 space-y-2">
              <Link
                href="/"
                onClick={() => setShowMobileMenu(false)}
                className="px-4 py-3 text-lg font-medium text-charcoal hover:bg-light-gray rounded-lg transition-all active:scale-95"
              >
                Discover
              </Link>
              {isAuthenticated && (
                <Link
                  href="/feed"
                  onClick={() => setShowMobileMenu(false)}
                  className="px-4 py-3 text-lg font-medium text-charcoal hover:bg-light-gray rounded-lg transition-all active:scale-95 flex items-center gap-2"
                >
                  <Sparkles className="w-5 h-5" />
                  For You
                </Link>
              )}
              <Link
                href="/search"
                onClick={() => setShowMobileMenu(false)}
                className="px-4 py-3 text-lg font-medium text-charcoal hover:bg-light-gray rounded-lg transition-all active:scale-95"
              >
                Search
              </Link>

              <div className="border-t border-light-gray my-4" />

              {isAuthenticated ? (
                <>
                  <Link
                    href="/favorites"
                    onClick={() => setShowMobileMenu(false)}
                    className="px-4 py-3 text-lg font-medium text-charcoal hover:bg-light-gray rounded-lg transition-all active:scale-95 flex items-center gap-3"
                  >
                    <Heart className="w-5 h-5 text-pinterest-red" />
                    Favorites
                  </Link>
                  <Link
                    href="/history"
                    onClick={() => setShowMobileMenu(false)}
                    className="px-4 py-3 text-lg font-medium text-charcoal hover:bg-light-gray rounded-lg transition-all active:scale-95 flex items-center gap-3"
                  >
                    <History className="w-5 h-5 text-gray" />
                    History
                  </Link>
                  <Link
                    href="/settings"
                    onClick={() => setShowMobileMenu(false)}
                    className="px-4 py-3 text-lg font-medium text-charcoal hover:bg-light-gray rounded-lg transition-all active:scale-95 flex items-center gap-3"
                  >
                    <Settings className="w-5 h-5 text-gray" />
                    Settings
                  </Link>
                  <button
                    onClick={() => {
                      handleLogout();
                      setShowMobileMenu(false);
                    }}
                    className="px-4 py-3 text-lg font-medium text-red-600 hover:bg-red-50 rounded-lg transition-all active:scale-95 flex items-center gap-3 text-left"
                  >
                    <LogOut className="w-5 h-5" />
                    Logout
                  </button>
                </>
              ) : (
                <>
                  <Link
                    href="/login"
                    onClick={() => setShowMobileMenu(false)}
                    className="px-4 py-3 text-lg font-medium text-charcoal hover:bg-light-gray rounded-lg transition-all active:scale-95"
                  >
                    Login
                  </Link>
                  <Link
                    href="/register"
                    onClick={() => setShowMobileMenu(false)}
                    className="px-4 py-3 text-lg font-medium bg-pinterest-red text-white rounded-lg hover:bg-dark-red transition-all active:scale-95 text-center"
                  >
                    Sign Up
                  </Link>
                </>
              )}
            </nav>
          </div>
        )}
      </div>
    </header>
  );
}
