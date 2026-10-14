"use client"

import { PanelLeftOpen } from "lucide-react"
import { useState } from "react"
import { KnowledgeSidebar } from "@/components/knowledge/sidebar"
import {
  Sheet,
  SheetContent,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"

type Props = React.ComponentProps<typeof KnowledgeSidebar>

/** Below lg the table of contents lives in a drawer, opened from a sticky bar. */
export function MobileSidebar(props: Props) {
  const [open, setOpen] = useState(false)
  return (
    <div className="sticky top-0 z-30 border-b border-border bg-background/95 px-4 py-2 backdrop-blur lg:hidden">
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetTrigger className="inline-flex items-center gap-2 rounded-md px-2 py-1 text-sm font-medium text-foreground hover:bg-muted">
          <PanelLeftOpen className="h-4 w-4" />
          Browse topics
        </SheetTrigger>
        <SheetContent
          side="left"
          className="w-[85vw] max-w-sm overflow-y-auto p-0 pt-8"
          aria-describedby={undefined}
        >
          <SheetTitle className="sr-only">Knowledge hub topics</SheetTitle>
          <KnowledgeSidebar {...props} onNavigate={() => setOpen(false)} />
        </SheetContent>
      </Sheet>
    </div>
  )
}
