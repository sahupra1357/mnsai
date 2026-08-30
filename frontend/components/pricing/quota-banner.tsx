"use client"

import { useQuery } from "@tanstack/react-query"
import { useSearchParams } from "next/navigation"
import { AlertCircle } from "lucide-react"
import { UsersService } from "@/src/client"

/**
 * Shown when a metered request was refused and the backend sent the user here
 * (`/pricing?reason=quota`). The exact numbers come from `/users/me/quota` so
 * the message matches whatever limit the account actually has — the limit is
 * per user and editable, so hard-coding "5" here would go stale.
 */
export default function QuotaBanner() {
  const searchParams = useSearchParams()
  const blocked = searchParams.get("reason") === "quota"

  const { data: quota } = useQuery({
    queryKey: ["userQuota"],
    queryFn: () => UsersService.readUserQuota(),
    enabled: blocked,
    retry: false,
    staleTime: 0,
  })

  if (!blocked) return null

  const usage =
    quota && !quota.unlimited
      ? `You have used all ${quota.limit} of your free requests.`
      : "You have used all of your free requests."

  return (
    <div className="px-6 pt-8">
      <div
        role="alert"
        className="mx-auto max-w-3xl flex items-start gap-3 rounded-lg border border-ui-danger/30 bg-ui-danger/5 px-5 py-4"
      >
        <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-ui-danger" />
        <div>
          <p className="font-semibold text-foreground">{usage}</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Choose a plan below to keep going. Your existing results stay
            available in the meantime.
          </p>
        </div>
      </div>
    </div>
  )
}
