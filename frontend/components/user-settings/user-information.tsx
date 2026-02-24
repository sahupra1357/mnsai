"use client"

import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { type SubmitHandler, useForm } from "react-hook-form"
import { Loader2 } from "lucide-react"
import {
  type ApiError,
  type UserPublic,
  type UserUpdateMe,
  UsersService,
} from "@/src/client"
import useAuth from "@/hooks/use-auth"
import { useToast } from "@/hooks/use-toast"
import { emailPattern, handleError } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

const UserInformation = () => {
  const queryClient = useQueryClient()
  const showToast = useToast()
  const [editMode, setEditMode] = useState(false)
  const { user: currentUser } = useAuth()
  const {
    register,
    handleSubmit,
    reset,
    getValues,
    formState: { isSubmitting, errors, isDirty },
  } = useForm<UserPublic>({
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      full_name: currentUser?.full_name,
      email: currentUser?.email,
    },
  })

  const toggleEditMode = () => {
    setEditMode(!editMode)
  }

  const mutation = useMutation({
    mutationFn: (data: UserUpdateMe) =>
      UsersService.updateUserMe({ requestBody: data }),
    onSuccess: () => {
      showToast("Success!", "User updated successfully.", "success")
    },
    onError: (err: ApiError) => {
      handleError(err, showToast)
    },
    onSettled: () => {
      queryClient.invalidateQueries()
    },
  })

  const onSubmit: SubmitHandler<UserUpdateMe> = async (data) => {
    mutation.mutate(data)
  }

  const onCancel = () => {
    reset()
    toggleEditMode()
  }

  return (
    <div className="max-w-full">
      <h3 className="text-sm font-semibold py-4">User Information</h3>
      <form
        onSubmit={handleSubmit(onSubmit)}
        className="w-full md:w-1/2"
      >
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="name">Full name</Label>
          {editMode ? (
            <Input
              id="name"
              {...register("full_name", { maxLength: 30 })}
              type="text"
              className="w-auto"
            />
          ) : (
            <p className="py-2 text-sm truncate max-w-[250px] text-muted-foreground">
              {currentUser?.full_name || "N/A"}
            </p>
          )}
        </div>

        <div className="flex flex-col gap-1.5 mt-4">
          <Label htmlFor="email">Email</Label>
          {editMode ? (
            <Input
              id="email"
              {...register("email", {
                required: "Email is required",
                pattern: emailPattern,
              })}
              type="email"
              className={`w-auto ${errors.email ? "border-destructive" : ""}`}
            />
          ) : (
            <p className="py-2 text-sm truncate max-w-[250px]">
              {currentUser?.email}
            </p>
          )}
          {errors.email && (
            <p className="text-sm text-destructive">{errors.email.message}</p>
          )}
        </div>

        <div className="flex gap-3 mt-4">
          <Button
            className="bg-ui-main hover:bg-[#003d8f] text-white"
            onClick={editMode ? undefined : toggleEditMode}
            type={editMode ? "submit" : "button"}
            disabled={editMode ? isSubmitting || !isDirty || !getValues("email") : false}
          >
            {editMode && isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {editMode ? "Save" : "Edit"}
          </Button>
          {editMode && (
            <Button
              type="button"
              variant="outline"
              onClick={onCancel}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
          )}
        </div>
      </form>
    </div>
  )
}

export default UserInformation
