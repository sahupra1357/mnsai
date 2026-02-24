"use client"

import { useMutation } from "@tanstack/react-query"
import { type SubmitHandler, useForm } from "react-hook-form"
import { Loader2 } from "lucide-react"
import { type ApiError, LoginService } from "@/src/client"
import { emailPattern, handleError } from "@/lib/utils"
import { useToast } from "@/hooks/use-toast"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

interface FormData {
  email: string
}

export default function RecoverPasswordPage() {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>()
  const showToast = useToast()

  const recoverPassword = async (data: FormData) => {
    await LoginService.recoverPassword({ email: data.email })
  }

  const mutation = useMutation({
    mutationFn: recoverPassword,
    onSuccess: () => {
      showToast(
        "Email sent.",
        "We sent an email with a link to get back into your account.",
        "success",
      )
      reset()
    },
    onError: (err: ApiError) => {
      handleError(err, showToast)
    },
  })

  const onSubmit: SubmitHandler<FormData> = async (data) => {
    mutation.mutate(data)
  }

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="flex h-screen max-w-sm mx-auto flex-col items-stretch justify-center gap-4 px-4"
    >
      <h1 className="text-3xl font-bold text-ui-main text-center mb-2">
        Password Recovery
      </h1>
      <p className="text-center text-muted-foreground">
        A password recovery email will be sent to the registered account.
      </p>
      <div className="flex flex-col gap-1.5">
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
      <Button
        type="submit"
        disabled={isSubmitting}
        className="bg-ui-main hover:bg-[#003d8f] text-white"
      >
        {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        Continue
      </Button>
    </form>
  )
}
