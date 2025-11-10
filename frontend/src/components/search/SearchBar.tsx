"use client";

import { useState, useEffect, FormEvent } from "react";
import { Search, X } from "lucide-react";

interface SearchBarProps {
  onSearch: (query: string) => void;
  placeholder?: string;
  className?: string;
  isLoading?: boolean;
  initialQuery?: string;
}

export function SearchBar({
  onSearch,
  placeholder = "Search for products...",
  className = "",
  isLoading = false,
  initialQuery = "",
}: SearchBarProps) {
  const [query, setQuery] = useState(initialQuery);

  // Update query when initialQuery changes
  useEffect(() => {
    if (initialQuery) {
      setQuery(initialQuery);
    }
  }, [initialQuery]);

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim());
    }
  };

  const handleClear = () => {
    setQuery("");
  };

  return (
    <form onSubmit={handleSubmit} className={`relative ${className}`}>
      <div className="relative flex items-center">
        {/* Search Icon */}
        <div className="absolute left-4 text-muted-foreground">
          <Search className="h-5 w-5" />
        </div>

        {/* Input Field */}
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder}
          disabled={isLoading}
          className={`
            w-full pl-12 pr-12 py-3
            text-base text-charcoal
            bg-white
            border-2 border-light-gray
            rounded-lg
            focus:outline-none focus:ring-4 focus:ring-pinterest-red/20 focus:border-pinterest-red
            disabled:opacity-50 disabled:cursor-not-allowed
            transition-all
          `}
        />

        {/* Clear Button */}
        {query && (
          <button
            type="button"
            onClick={handleClear}
            className="absolute right-4 text-muted-foreground hover:text-foreground transition-colors"
            aria-label="Clear search"
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      {/* Submit Button - Hidden but functional for Enter key */}
      <button type="submit" className="sr-only">
        Search
      </button>
    </form>
  );
}
