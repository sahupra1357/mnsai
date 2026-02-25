"use client"

import Link from "next/link"
import Image from "next/image"
import { Suspense, useState } from "react"
import { type SubmitHandler, useForm } from "react-hook-form"
import { Eye, EyeOff, Loader2 } from "lucide-react"
import { useSearchParams } from "next/navigation"
import useAuth from "@/hooks/use-auth"
import { emailPattern } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

const OAUTH_ERROR_MESSAGES: Record<string, string> = {
  access_denied: "Sign-in was cancelled.",
  state_mismatch: "Security check failed. Please try again.",
  no_email: "Could not retrieve your email address.",
  inactive_user: "Your account is inactive.",
  provider_not_configured: "This sign-in method is not available.",
  invalid_token: "Authentication failed. Please try again.",
}

interface LoginForm {
  username: string
  password: string
}

function LoginPage() {
  const [showPassword, setShowPassword] = useState(false)
  const { loginMutation, error, resetError } = useAuth()
  const searchParams = useSearchParams()
  const oauthErrorKey = searchParams.get("error")
  const oauthError = oauthErrorKey
    ? (OAUTH_ERROR_MESSAGES[oauthErrorKey] ?? "Sign-in failed. Please try again.")
    : null

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      username: "",
      password: "",
    },
  })

  const onSubmit: SubmitHandler<LoginForm> = async (data) => {
    if (isSubmitting) return
    resetError()
    try {
      await loginMutation.mutateAsync(data)
    } catch {
      // error is handled by useAuth
    }
  }

  return (
    <div className="flex h-screen max-w-sm mx-auto flex-col items-stretch justify-center gap-4 px-4">
      <div className="flex justify-center mb-4">
        <Image
          src="/assets/images/mnsAI_2.png"
          alt="mnsAI logo"
          width={160}
          height={60}
          style={{ width: "auto", height: "auto" }}
          priority
        />
      </div>

      {oauthError && (
        <p className="text-sm text-destructive text-center rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2">
          {oauthError}
        </p>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="username">Email</Label>
          <Input
            id="username"
            {...register("username", {
              required: "Username is required",
              pattern: emailPattern,
            })}
            placeholder="Email"
            type="email"
            className={errors.username || error ? "border-destructive" : ""}
          />
          {errors.username && (
            <p className="text-sm text-destructive">{errors.username.message}</p>
          )}
        </div>

        <div className="flex flex-col gap-1.5">
          <div className="relative">
            <Input
              {...register("password", {
                required: "Password is required",
              })}
              type={showPassword ? "text" : "password"}
              placeholder="Password"
              className={`pr-10 ${error ? "border-destructive" : ""}`}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>

        <Link href="/recover-password" className="text-sm text-blue-500">
          Forgot password?
        </Link>

        <Button
          type="submit"
          disabled={isSubmitting}
          className="bg-ui-main hover:bg-[#003d8f] text-white"
        >
          {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Log In
        </Button>
      </form>

      <div className="relative flex items-center gap-3">
        <div className="flex-1 border-t border-border" />
        <span className="text-xs text-muted-foreground">or continue with</span>
        <div className="flex-1 border-t border-border" />
      </div>

      <div className="flex flex-col gap-2">
        <a
          href={`${API_BASE}/api/v1/login/google`}
          className="flex items-center justify-center gap-2 rounded-md border border-border bg-background px-4 py-2 text-sm font-medium hover:bg-accent transition-colors"
        >
          <svg viewBox="0 0 24 24" className="h-4 w-4" aria-hidden="true">
            <path
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              fill="#4285F4"
            />
            <path
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              fill="#34A853"
            />
            <path
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              fill="#FBBC05"
            />
            <path
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              fill="#EA4335"
            />
          </svg>
          Sign in with Google
        </a>

        <a
          href={`${API_BASE}/api/v1/login/github`}
          className="flex items-center justify-center gap-2 rounded-md border border-border bg-background px-4 py-2 text-sm font-medium hover:bg-accent transition-colors"
        >
          <svg viewBox="0 0 24 24" className="h-4 w-4 fill-foreground" aria-hidden="true">
            <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
          </svg>
          Sign in with GitHub
        </a>
      </div>

      <p className="text-sm text-center">
        Don&apos;t have an account?{" "}
        <Link href="/signup" className="text-blue-500">
          Sign up
        </Link>
      </p>
    </div>
  )
}

export default function LoginPageWithSuspense() {
  return (
    <Suspense>
      <LoginPage />
    </Suspense>
  )
}
