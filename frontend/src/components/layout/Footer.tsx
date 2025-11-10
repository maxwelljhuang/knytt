"use client";

import Link from "next/link";
import Image from "next/image";
import { Github, Twitter, Instagram } from "lucide-react";

export function Footer() {
  return (
    <footer className="bg-evergreen text-ivory mt-auto">
      <div className="container mx-auto px-4 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="relative w-12 h-12 flex-shrink-0">
                <Image
                  src="/knytt-logo-circle.png"
                  alt="Knytt Logo"
                  width={48}
                  height={48}
                  className="rounded-full"
                  onError={(e) => {
                    // Fallback if logo not found
                    e.currentTarget.style.display = 'none';
                    e.currentTarget.parentElement!.innerHTML = `
                      <div class="w-12 h-12 bg-gradient-to-br from-sage to-ivory rounded-full flex items-center justify-center">
                        <span class="text-evergreen font-bold text-xl">K</span>
                      </div>
                    `;
                  }}
                />
              </div>
              <span className="text-2xl font-bold">Knytt</span>
            </div>
            <p className="text-ivory/80 text-sm">
              Discover curated products powered by AI-driven personalization.
            </p>
          </div>

          {/* Shop */}
          <div>
            <h3 className="font-semibold mb-4">Shop</h3>
            <ul className="space-y-2 text-sm">
              <li>
                <Link href="/search" className="text-ivory/80 hover:text-ivory transition-colors">
                  All Products
                </Link>
              </li>
              <li>
                <Link href="/search?category=fashion" className="text-ivory/80 hover:text-ivory transition-colors">
                  Fashion
                </Link>
              </li>
              <li>
                <Link href="/search?category=home" className="text-ivory/80 hover:text-ivory transition-colors">
                  Home & Living
                </Link>
              </li>
              <li>
                <Link href="/search?category=accessories" className="text-ivory/80 hover:text-ivory transition-colors">
                  Accessories
                </Link>
              </li>
            </ul>
          </div>

          {/* Company */}
          <div>
            <h3 className="font-semibold mb-4">Company</h3>
            <ul className="space-y-2 text-sm">
              <li>
                <Link href="/about" className="text-ivory/80 hover:text-ivory transition-colors">
                  About Us
                </Link>
              </li>
              <li>
                <Link href="/contact" className="text-ivory/80 hover:text-ivory transition-colors">
                  Contact
                </Link>
              </li>
              <li>
                <Link href="/privacy" className="text-ivory/80 hover:text-ivory transition-colors">
                  Privacy Policy
                </Link>
              </li>
              <li>
                <Link href="/terms" className="text-ivory/80 hover:text-ivory transition-colors">
                  Terms of Service
                </Link>
              </li>
            </ul>
          </div>

          {/* Connect */}
          <div>
            <h3 className="font-semibold mb-4">Connect</h3>
            <div className="flex gap-4">
              <a
                href="https://github.com"
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 bg-ivory/10 hover:bg-ivory/20 rounded-full transition-colors"
              >
                <Github className="w-5 h-5" />
              </a>
              <a
                href="https://twitter.com"
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 bg-ivory/10 hover:bg-ivory/20 rounded-full transition-colors"
              >
                <Twitter className="w-5 h-5" />
              </a>
              <a
                href="https://instagram.com"
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 bg-ivory/10 hover:bg-ivory/20 rounded-full transition-colors"
              >
                <Instagram className="w-5 h-5" />
              </a>
            </div>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="mt-12 pt-8 border-t border-ivory/20">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4 text-sm text-ivory/60">
            <p>&copy; 2025 Knytt. All rights reserved.</p>
            <p>Powered by AI-driven product discovery</p>
          </div>
        </div>
      </div>
    </footer>
  );
}
