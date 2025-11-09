"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import Link from "next/link";
import { useAuth, useLogin } from "@/lib/queries/auth";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Input, Button } from "@/components/ui";
import { Mail, Lock, ArrowLeft } from "lucide-react";

// Validation schema
const loginSchema = z.object({
  email: z.string().email("Invalid email address"),
  password: z.string().min(1, "Password is required"),
});

type LoginFormData = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const { isAuthenticated } = useAuth();
  const loginMutation = useLogin();
  const router = useRouter();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  // Redirect if already logged in
  useEffect(() => {
    if (isAuthenticated) {
      router.push("/");
    }
  }, [isAuthenticated, router]);

  const onSubmit = (data: LoginFormData) => {
    loginMutation.mutate(data, {
      onSuccess: () => {
        router.push("/");
      },
    });
  };

  return (
    <div className="min-h-screen bg-ivory flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md animate-fade-in">
        <div className="bg-white rounded-2xl shadow-2xl p-8 border-2 border-blush">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="w-16 h-16 mx-auto mb-4 bg-pinterest-red rounded-full flex items-center justify-center shadow-lg">
              <span className="text-white font-bold text-2xl">K</span>
            </div>
            <h1 className="text-4xl font-bold text-charcoal mb-2">
              Welcome Back
            </h1>
            <p className="text-gray">Sign in to your account</p>
          </div>

          {/* Error Message */}
          {loginMutation.error && (
            <div className="mb-6 p-4 bg-red-50 border-2 border-red-200 rounded-lg animate-slide-down">
              <p className="text-red-700 text-sm font-medium flex items-center gap-2">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                {loginMutation.error.message || "Login failed. Please check your credentials."}
              </p>
            </div>
          )}

          {/* Login Form */}
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            {/* Email Field */}
            <Input
              {...register("email")}
              label="Email Address"
              type="email"
              leftIcon={<Mail className="w-5 h-5" />}
              error={errors.email?.message}
              floatingLabel={true}
            />

            {/* Password Field */}
            <Input
              {...register("password")}
              label="Password"
              type="password"
              leftIcon={<Lock className="w-5 h-5" />}
              error={errors.password?.message}
              floatingLabel={true}
            />

            {/* Submit Button */}
            <Button
              type="submit"
              variant="secondary"
              size="lg"
              loading={loginMutation.isPending}
              className="w-full"
            >
              Sign In
            </Button>
          </form>

          {/* Footer Links */}
          <div className="mt-6 text-center">
            <p className="text-sm text-sage">
              Don't have an account?{" "}
              <Link
                href="/register"
                className="text-terracotta hover:text-terracotta/80 font-medium"
              >
                Create one
              </Link>
            </p>
          </div>
        </div>

        {/* Back to Home */}
        <div className="mt-6 text-center">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-sm text-sage hover:text-evergreen transition-colors font-medium"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to home
          </Link>
        </div>
      </div>
    </div>
  );
}
