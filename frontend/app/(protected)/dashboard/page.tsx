import { redirect } from "next/navigation"

/**
 * The dashboard moved to "/". This route stays so old links, bookmarks, and the
 * OAuth callback's historical target keep resolving.
 */
export default function DashboardRedirect() {
  redirect("/")
}
