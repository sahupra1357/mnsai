import {
  BookOpen,
  Boxes,
  Brain,
  Database,
  FlaskConical,
  GitFork,
  GraduationCap,
  Layers,
  MessageSquareText,
  Network,
  Rocket,
  Sigma,
  Sparkles,
  type LucideIcon,
} from "lucide-react"

/** Per-stage icons. A stage added to the repo later gets the default book. */
const STAGE_ICONS: Record<number, LucideIcon> = {
  1: Sigma,
  2: Layers,
  3: Brain,
  4: Sparkles,
  5: MessageSquareText,
  6: Database,
  7: Network,
  8: GitFork,
  9: FlaskConical,
  10: Rocket,
  11: Boxes,
  12: GraduationCap,
}

export function stageIcon(n: number | null): LucideIcon {
  return (n !== null && STAGE_ICONS[n]) || BookOpen
}
