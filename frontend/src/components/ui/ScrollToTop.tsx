"use client";

import { useState, useEffect } from "react";
import { ArrowUp } from "lucide-react";

interface ScrollToTopProps {
  showAfter?: number; // Show button after scrolling this many pixels
  smooth?: boolean; // Use smooth scrolling
  className?: string;
}

export function ScrollToTop({
  showAfter = 400,
  smooth = true,
  className = "",
}: ScrollToTopProps) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsVisible(window.scrollY > showAfter);
    };

    // Initial check
    handleScroll();

    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, [showAfter]);

  const scrollToTop = () => {
    window.scrollTo({
      top: 0,
      behavior: smooth ? "smooth" : "auto",
    });
  };

  if (!isVisible) {
    return null;
  }

  return (
    <button
      onClick={scrollToTop}
      className={`
        fixed bottom-6 right-6 z-[var(--z-fab)]
        p-4 bg-pinterest-red text-white
        rounded-full shadow-xl
        hover:bg-dark-red hover:shadow-2xl
        active:scale-95
        transition-all duration-[var(--duration-fast)]
        animate-fade-in
        group
        ${className}
      `}
      aria-label="Scroll to top"
    >
      <ArrowUp className="w-6 h-6 group-hover:scale-110 transition-transform" />
    </button>
  );
}
