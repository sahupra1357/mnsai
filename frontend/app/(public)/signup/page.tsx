"use client"

import Link from "next/link"
import Image from "next/image"
import { type SubmitHandler, useForm } from "react-hook-form"
import { Loader2 } from "lucide-react"
import type { UserRegister } from "@/src/client"
import useAuth from "@/hooks/use-auth"
import { confirmPasswordRules, emailPattern, passwordRules } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

interface UserRegisterForm extends UserRegister {
  confirm_password: string
}

export default function SignUpPage() {
  const { signUpMutation } = useAuth()
  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<UserRegisterForm>({
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      email: "",
      full_name: "",
      password: "",
      confirm_password: "",
    },
  })

  const onSubmit: SubmitHandler<UserRegisterForm> = (data) => {
    signUpMutation.mutate(data)
  }

  return (
    <div className="flex h-screen flex-col md:flex-row justify-center">
      <div className="flex h-full max-w-sm mx-auto flex-col items-stretch justify-center gap-4 px-4">
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
            <Label className="sr-only" htmlFor="full_name">Full Name</Label>
            <Input
              id="full_name"
              minLength={3}
              {...register("full_name", { required: "Full Name is required" })}
              placeholder="Full Name"
              type="text"
              className={errors.full_name ? "border-destructive" : ""}
            />
            {errors.full_name && (
              <p className="text-sm text-destructive">{errors.full_name.message}</p>
            )}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label className="sr-only" htmlFor="email">Email</Label>
            <Input
              id="email"
              {...register("email", {
                required: "Email is required",
                pattern: emailPattern,
              })}
              placeholder="Email"
              type="email"
              className={errors.email ? "border-destructive" : ""}
            />
            {errors.email && (
              <p className="text-sm text-destructive">{errors.email.message}</p>
            )}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label className="sr-only" htmlFor="password">Password</Label>
            <Input
              id="password"
              {...register("password", passwordRules())}
              placeholder="Password"
              type="password"
              className={errors.password ? "border-destructive" : ""}
            />
            {errors.password && (
              <p className="text-sm text-destructive">{errors.password.message}</p>
            )}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label className="sr-only" htmlFor="confirm_password">Confirm Password</Label>
            <Input
              id="confirm_password"
              {...register("confirm_password", confirmPasswordRules(getValues))}
              placeholder="Repeat Password"
              type="password"
              className={errors.confirm_password ? "border-destructive" : ""}
            />
            {errors.confirm_password && (
              <p className="text-sm text-destructive">{errors.confirm_password.message}</p>
            )}
          </div>

          <Button
            type="submit"
            disabled={isSubmitting}
            className="bg-ui-main hover:bg-[#003d8f] text-white"
          >
            {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Sign Up
          </Button>
        </form>

        <p className="text-sm text-center">
          Already have an account?{" "}
          <Link href="/login" className="text-blue-500">
            Log In
          </Link>
        </p>
      </div>
    </div>
  )
}
