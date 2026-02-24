"use client"

import useAuth from "@/hooks/use-auth"

export default function DashboardPage() {
  const { user: currentUser } = useAuth()

  return (
    <div className="container mx-auto max-w-full">
      <div className="pt-12 m-4">
        <p className="text-2xl">
          Hi, {currentUser?.full_name || currentUser?.email} 👋🏼
        </p>
        <p>Welcome to the Home page of mnsAI</p>
      </div>
    </div>
  )
}
