"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useRouter } from "next/navigation"
import { useState } from "react"
import { AxiosError } from "axios"
import { type ApiError, type UserRegister, UsersService } from "@/src/client"
import type { UserPublic } from "@/src/client"
import { useToast } from "@/hooks/use-toast"

async function fetchCurrentUser(): Promise<UserPublic | null> {
  // no-store because this answers "who is signed in right now": a cached copy
  // shows a signed-out visitor as signed in, or the reverse, and Safari will
  // heuristically cache a response that carries no explicit directive.
  const res = await fetch("/api/auth/me", { cache: "no-store" })
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
    staleTime: 0,
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
      window.location.href = "/"
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
    window.location.href = "/login"
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
