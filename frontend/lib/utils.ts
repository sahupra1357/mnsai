import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"
import type { ApiError } from "@/src/client"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export const emailPattern = {
  value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
  message: "Invalid email address",
}

export const namePattern = {
  value: /^[A-Za-z\s\u00C0-\u017F]{1,30}$/,
  message: "Invalid name",
}

export const passwordRules = (isRequired = true) => {
  const rules: Record<string, unknown> = {
    minLength: {
      value: 8,
      message: "Password must be at least 8 characters",
    },
  }

  if (isRequired) {
    rules.required = "Password is required"
  }

  return rules
}

export const confirmPasswordRules = (
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  getValues: () => any,
  isRequired = true,
) => {
  const rules: Record<string, unknown> = {
    validate: (value: string) => {
      const password = getValues().password || getValues().new_password
      return value === password ? true : "The passwords do not match"
    },
  }

  if (isRequired) {
    rules.required = "Password confirmation is required"
  }

  return rules
}

export const handleError = (
  err: ApiError,
  showToast: (title: string, description: string, status: "success" | "error") => void,
) => {
  const errDetail = (err.body as Record<string, unknown>)?.detail
  let errorMessage: string = (errDetail as string) || "Something went wrong."
  if (Array.isArray(errDetail) && errDetail.length > 0) {
    errorMessage = (errDetail[0] as Record<string, string>).msg
  }
  showToast("Error", errorMessage, "error")
}
