"use client"

import { useMutation } from "@tanstack/react-query"
import { type SubmitHandler, useForm } from "react-hook-form"
import { Loader2 } from "lucide-react"
import { type ApiError, type UpdatePassword, UsersService } from "@/src/client"
import { useToast } from "@/hooks/use-toast"
import { confirmPasswordRules, handleError, passwordRules } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

interface UpdatePasswordForm extends UpdatePassword {
  confirm_password: string
}

const ChangePassword = () => {
  const showToast = useToast()
  const {
    register,
    handleSubmit,
    reset,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<UpdatePasswordForm>({
    mode: "onBlur",
    criteriaMode: "all",
  })

  const mutation = useMutation({
    mutationFn: (data: UpdatePassword) =>
      UsersService.updatePasswordMe({ requestBody: data }),
    onSuccess: () => {
      showToast("Success!", "Password updated successfully.", "success")
      reset()
    },
    onError: (err: ApiError) => {
      handleError(err, showToast)
    },
  })

  const onSubmit: SubmitHandler<UpdatePasswordForm> = async (data) => {
    mutation.mutate(data)
  }

  return (
    <div className="max-w-full">
      <h3 className="text-sm font-semibold py-4">Change Password</h3>
      <form
        onSubmit={handleSubmit(onSubmit)}
        className="w-full md:w-1/2 flex flex-col gap-4"
      >
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="current_password">Current Password *</Label>
          <Input
            id="current_password"
            {...register("current_password")}
            placeholder="Password"
            type="password"
            className={`w-auto ${errors.current_password ? "border-destructive" : ""}`}
          />
          {errors.current_password && (
            <p className="text-sm text-destructive">{errors.current_password.message}</p>
          )}
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="new_password">Set Password *</Label>
          <Input
            id="new_password"
            {...register("new_password", passwordRules())}
            placeholder="Password"
            type="password"
            className={`w-auto ${errors.new_password ? "border-destructive" : ""}`}
          />
          {errors.new_password && (
            <p className="text-sm text-destructive">{errors.new_password.message}</p>
          )}
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="confirm_password">Confirm Password *</Label>
          <Input
            id="confirm_password"
            {...register("confirm_password", confirmPasswordRules(getValues))}
            placeholder="Password"
            type="password"
            className={`w-auto ${errors.confirm_password ? "border-destructive" : ""}`}
          />
          {errors.confirm_password && (
            <p className="text-sm text-destructive">{errors.confirm_password.message}</p>
          )}
        </div>

        <Button
          type="submit"
          disabled={isSubmitting}
          className="mt-2 bg-ui-main hover:bg-[#003d8f] text-white w-fit"
        >
          {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Save
        </Button>
      </form>
    </div>
  )
}

export default ChangePassword
