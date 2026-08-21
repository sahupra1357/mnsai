"use client"

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { PlayCircle } from "lucide-react"

type ToolDemoDialogProps = {
  /** Tool name — used in the dialog title and the trigger's accessible name. */
  title: string
  description: string
  /** Path under /public, e.g. "/assets/videos/foo.mp4". */
  src: string
  poster?: string
}

/**
 * "Watch demo" trigger + video lightbox for a tools-grid card that has a
 * screen recording instead of an in-app route.
 *
 * The trigger stretches over its card via ::after — same treatment as the
 * "Open" link on the other cards, so a demo card is clicked the same way.
 * Radix unmounts dialog content while closed, so the <video> element (and
 * therefore the mp4) is only created when a visitor actually opens it; the
 * dashboard pays nothing for it on load.
 */
export function ToolDemoDialog({
  title,
  description,
  src,
  poster,
}: ToolDemoDialogProps) {
  return (
    <Dialog>
      <DialogTrigger className="inline-flex items-center text-xs font-semibold text-ui-accent after:absolute after:inset-0 after:content-[''] hover:underline">
        Watch demo <PlayCircle className="ml-1 h-3.5 w-3.5" />
      </DialogTrigger>

      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        {/* The recording is a silent screen capture with no audio track, so
            there is nothing for a <track> to caption; `muted` keeps autoplay
            allowed everywhere. */}
        <video
          src={src}
          poster={poster}
          controls
          autoPlay
          loop
          muted
          playsInline
          preload="metadata"
          aria-label={`${title} screen recording`}
          className="w-full rounded-lg border border-border bg-muted"
        />
      </DialogContent>
    </Dialog>
  )
}
