import { skillGroups } from "@/lib/profile-data"

/**
 * Skills as chip clusters (not checklists). Each of the five draft groups is a
 * labelled subsection with an icon tile and a wrapped set of tool chips.
 */
export function SkillsChips() {
  return (
    <div className="grid gap-6 md:grid-cols-2">
      {skillGroups.map((group) => {
        const Icon = group.icon
        return (
          <div
            key={group.title}
            className="rounded-2xl border border-border bg-card p-6 shadow-sm"
          >
            <div className="flex items-center gap-2.5">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-ui-accent/10 text-ui-accent">
                <Icon className="h-4 w-4" />
              </span>
              <h3 className="font-display text-base font-bold tracking-tight text-foreground">
                {group.title}
              </h3>
            </div>
            <ul className="mt-4 flex flex-wrap gap-2">
              {group.items.map((item) => (
                <li
                  key={item}
                  className="rounded-full border border-border bg-background px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:border-ui-accent/40 hover:text-ui-accent"
                >
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )
      })}
    </div>
  )
}
