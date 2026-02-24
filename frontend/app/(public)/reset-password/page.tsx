"use client"

import { useMutation } from "@tanstack/react-query"
import { useRouter } from "next/navigation"
import { type SubmitHandler, useForm } from "react-hook-form"
import { Loader2 } from "lucide-react"
import { type ApiError, LoginService, type NewPassword } from "@/src/client"
import { confirmPasswordRules, handleError, passwordRules } from "@/lib/utils"
import { useToast } from "@/hooks/use-toast"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

interface NewPasswordForm extends NewPassword {
  confirm_password: string
}

export default function ResetPasswordPage() {
  const {
    register,
    handleSubmit,
    getValues,
    reset,
    formState: { errors },
  } = useForm<NewPasswordForm>({
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      new_password: "",
    },
  })
  const showToast = useToast()
  const router = useRouter()

  const resetPassword = async (data: NewPassword) => {
    const token = new URLSearchParams(window.location.search).get("token")
    if (!token) return
    await LoginService.resetPassword({
      requestBody: { new_password: data.new_password, token: token },
    })
  }

  const mutation = useMutation({
    mutationFn: resetPassword,
    onSuccess: () => {
      showToast("Success!", "Password updated successfully.", "success")
      reset()
      router.push("/login")
    },
    onError: (err: ApiError) => {
      handleError(err, showToast)
    },
  })

  const onSubmit: SubmitHandler<NewPasswordForm> = async (data) => {
    mutation.mutate(data)
  }

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="flex h-screen max-w-sm mx-auto flex-col items-stretch justify-center gap-4 px-4"
    >
      <h1 className="text-3xl font-bold text-ui-main text-center mb-2">
        Reset Password
      </h1>
      <p className="text-center text-muted-foreground">
        Please enter your new password and confirm it to reset your password.
      </p>
      <div className="flex flex-col gap-1.5 mt-4">
        <Label htmlFor="password">Set Password</Label>
        <Input
          id="password"
          {...register("new_password", passwordRules())}
          placeholder="Password"
          type="password"
          className={errors.new_password ? "border-destructive" : ""}
        />
        {errors.new_password && (
          <p className="text-sm text-destructive">{errors.new_password.message}</p>
        )}
      </div>
      <div className="flex flex-col gap-1.5 mt-4">
        <Label htmlFor="confirm_password">Confirm Password</Label>
        <Input
          id="confirm_password"
          {...register("confirm_password", confirmPasswordRules(getValues))}
          placeholder="Password"
          type="password"
          className={errors.confirm_password ? "border-destructive" : ""}
        />
        {errors.confirm_password && (
          <p className="text-sm text-destructive">{errors.confirm_password.message}</p>
        )}
      </div>
      <Button
        type="submit"
        className="bg-ui-main hover:bg-[#003d8f] text-white"
      >
        Reset Password
      </Button>
    </form>
  )
}
