"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useRouter } from "next/navigation"
import { useState } from "react"
import { AxiosError } from "axios"
import { type ApiError, type UserRegister, UsersService } from "@/src/client"
import type { UserPublic } from "@/src/client"
import { useToast } from "@/hooks/use-toast"

async function fetchCurrentUser(): Promise<UserPublic | null> {
  const res = await fetch("/api/auth/me")
  if (!res.ok) return null
  return res.json()
}

const useAuth = () => {
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()
  const showToast = useToast()
  const queryClient = useQueryClient()

  const { data: user, isLoading } = useQuery<UserPublic | null, Error>({
    queryKey: ["currentUser"],
    queryFn: fetchCurrentUser,
    retry: false,
  })

  const signUpMutation = useMutation({
    mutationFn: (data: UserRegister) =>
      UsersService.registerUser({ requestBody: data }),
    onSuccess: () => {
      router.push("/login")
      showToast("Account created.", "Your account has been created successfully.", "success")
    },
    onError: (err: ApiError) => {
      let errDetail = (err.body as Record<string, unknown>)?.detail

      if (err instanceof AxiosError) {
        errDetail = err.message
      }

      showToast("Something went wrong.", errDetail as string, "error")
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
    },
  })

  const loginMutation = useMutation({
    mutationFn: async (data: { username: string; password: string }) => {
      const formData = new FormData()
      formData.append("username", data.username)
      formData.append("password", data.password)
      const res = await fetch("/api/auth/login", {
        method: "POST",
        body: formData,
      })
      if (!res.ok) {
        const error = await res.json()
        throw error
      }
    },
    onSuccess: () => {
      router.push("/dashboard")
    },
    onError: (err: Record<string, unknown>) => {
      let errDetail = err?.detail

      if (Array.isArray(errDetail)) {
        errDetail = "Something went wrong"
      }

      setError(errDetail as string || "Login failed")
    },
  })

  const logout = async () => {
    await fetch("/api/auth/logout", { method: "POST" })
    queryClient.clear()
    router.push("/login")
  }

  return {
    signUpMutation,
    loginMutation,
    logout,
    user,
    isLoading,
    error,
    resetError: () => setError(null),
  }
}

export default useAuth
