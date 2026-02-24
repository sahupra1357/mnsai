"use client"

import Link from "next/link"
import Image from "next/image"
import { useState } from "react"
import { type SubmitHandler, useForm } from "react-hook-form"
import { Eye, EyeOff, Loader2 } from "lucide-react"
import useAuth from "@/hooks/use-auth"
import { emailPattern } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

interface LoginForm {
  username: string
  password: string
}

export default function LoginPage() {
  const [showPassword, setShowPassword] = useState(false)
  const { loginMutation, error, resetError } = useAuth()
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

      <p className="text-sm text-center">
        Don&apos;t have an account?{" "}
        <Link href="/signup" className="text-blue-500">
          Sign up
        </Link>
      </p>
    </div>
  )
}
