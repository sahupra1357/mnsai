import Link from "next/link"

export default function NotFound() {
  return (
    <div className="flex h-screen flex-col items-center justify-center gap-4">
      <h1 className="text-4xl font-bold text-ui-main">404</h1>
      <p className="text-muted-foreground">Page not found</p>
      <Link href="/" className="text-primary underline">
        Go back home
      </Link>
    </div>
  )
}
