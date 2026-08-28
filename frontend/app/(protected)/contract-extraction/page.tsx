import { Suspense } from "react"

import { ContractExtractionWorkspace } from "@/components/contract-extraction/workspace"

export const metadata = {
  title: "Contract field extraction",
  description:
    "Pull ten key contract fields to JSON, verify the blanks, and store the row.",
}

export default function ContractExtractionPage() {
  return (
    <Suspense
      fallback={
        <main className="mx-auto max-w-[1800px] px-4 py-6 sm:px-6">
          <p className="text-sm text-muted-foreground">Loading workspace…</p>
        </main>
      }
    >
      <ContractExtractionWorkspace />
    </Suspense>
  )
}
