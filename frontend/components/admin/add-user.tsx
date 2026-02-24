"use client"

import { useMutation, useQueryClient } from "@tanstack/react-query"
import { type SubmitHandler, useForm } from "react-hook-form"
import { Loader2 } from "lucide-react"
import { type UserCreate, UsersService } from "@/src/client"
import type { ApiError } from "@/src/client/core/ApiError"
import { useToast } from "@/hooks/use-toast"
import { emailPattern, handleError } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

interface AddUserProps {
  isOpen: boolean
  onClose: () => void
}

interface UserCreateForm extends UserCreate {
  confirm_password: string
}

const AddUser = ({ isOpen, onClose }: AddUserProps) => {
  const queryClient = useQueryClient()
  const showToast = useToast()
  const {
    register,
    handleSubmit,
    reset,
    getValues,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<UserCreateForm>({
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      email: "",
      full_name: "",
      password: "",
      confirm_password: "",
      is_superuser: false,
      is_active: false,
    },
  })

  const isSuperuser = watch("is_superuser")
  const isActive = watch("is_active")

  const mutation = useMutation({
    mutationFn: (data: UserCreate) =>
      UsersService.createUser({ requestBody: data }),
    onSuccess: () => {
      showToast("Success!", "User created successfully.", "success")
      reset()
      onClose()
    },
    onError: (err: ApiError) => {
      handleError(err, showToast)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
    },
  })

  const onSubmit: SubmitHandler<UserCreateForm> = (data) => {
    mutation.mutate(data)
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Add User</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4 pb-2">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="email">Email *</Label>
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
            <Label htmlFor="name">Full name</Label>
            <Input
              id="name"
              {...register("full_name")}
              placeholder="Full name"
              type="text"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="password">Set Password *</Label>
            <Input
              id="password"
              {...register("password", {
                required: "Password is required",
                minLength: {
                  value: 8,
                  message: "Password must be at least 8 characters",
                },
              })}
              placeholder="Password"
              type="password"
              className={errors.password ? "border-destructive" : ""}
            />
            {errors.password && (
              <p className="text-sm text-destructive">{errors.password.message}</p>
            )}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="confirm_password">Confirm Password *</Label>
            <Input
              id="confirm_password"
              {...register("confirm_password", {
                required: "Please confirm your password",
                validate: (value) =>
                  value === getValues().password ||
                  "The passwords do not match",
              })}
              placeholder="Password"
              type="password"
              className={errors.confirm_password ? "border-destructive" : ""}
            />
            {errors.confirm_password && (
              <p className="text-sm text-destructive">{errors.confirm_password.message}</p>
            )}
          </div>

          <div className="flex gap-4 mt-2">
            <div className="flex items-center gap-2">
              <Checkbox
                id="is_superuser"
                checked={!!isSuperuser}
                onCheckedChange={(checked) => setValue("is_superuser", !!checked)}
              />
              <Label htmlFor="is_superuser">Is superuser?</Label>
            </div>
            <div className="flex items-center gap-2">
              <Checkbox
                id="is_active"
                checked={!!isActive}
                onCheckedChange={(checked) => setValue("is_active", !!checked)}
              />
              <Label htmlFor="is_active">Is active?</Label>
            </div>
          </div>

          <div className="flex justify-end gap-3 mt-2">
            <Button
              type="submit"
              disabled={isSubmitting}
              className="bg-ui-main hover:bg-[#003d8f] text-white"
            >
              {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Save
            </Button>
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export default AddUser
