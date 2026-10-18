"use client"

import { Logo } from "@/components/common/logo"
import { ThemeToggle } from "@/components/common/theme-toggle"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import useAuth from "@/hooks/use-auth"
import { SOLUTIONS, TOOLS_ANCHOR, solutionNavHref } from "@/lib/solutions"
import { ChevronDown, Menu, X } from "lucide-react"
import Link from "next/link"
import { useState } from "react"
import UserMenu from "./user-menu"

interface NavItem {
  label: string
  subLabel?: string
  children?: Array<NavItem>
  href?: string
  /** Rendered only for superusers. */
  superuserOnly?: boolean
}

const NAV_ITEMS: Array<NavItem> = [
  {
    label: "Learn",
    children: [
      {
        label: "Knowledge Hub",
        subLabel: "AI engineering, from first principles to production",
        href: "/",
      },
      {
        label: "AI Engineering Guide",
        subLabel: "Start here: every stage summarised",
        href: "/learn/AI_ENGINEERING_GUIDE",
      },
      {
        label: "Projects",
        subLabel: "Working systems built on these notes",
        href: `/#${TOOLS_ANCHOR}`,
      },
    ],
  },
  {
    label: "Solutions",
    // Generated from the shared tool catalogue so the dropdown and the
    // dashboard's "Your tools" grid always list the same things.
    // Settings is reached through the user menu ("My profile"), not here.
    children: SOLUTIONS.map((solution) => ({
      label: solution.title,
      subLabel: solution.navSubLabel,
      href: solutionNavHref(solution),
    })),
  },
  {
    label: "Resources",
    children: [
      {
        label: "Blog",
        subLabel: "Insights, tutorials, and updates",
        href: "/resources/blog",
      },
      {
        label: "Profile",
        subLabel: "Pradeep's portfolio, experience, and AI chat",
        href: "/profile",
        superuserOnly: true,
      },
      {
        label: "Items",
        subLabel: "Up-and-coming Designers",
        href: "/items",
        superuserOnly: true,
      },
      {
        label: "Legacy GPT Extractor",
        subLabel: "Original GPT-based extraction demo",
        href: "/extractor",
        superuserOnly: true,
      },
      {
        label: "Profile v1 (1st draft)",
        subLabel: "Archived first draft of the profile page",
        href: "/drafts/profile-v1",
        superuserOnly: true,
      },
      {
        label: "Profile V2",
        subLabel: "Archived second draft of the profile page",
        href: "/drafts/profile-v2",
        superuserOnly: true,
      },
      {
        label: "Dashboard v1 (backup)",
        subLabel: "The original AI operations desk home page",
        href: "/admin/dashboard-v1",
        superuserOnly: true,
      },
    ],
  },
  {
    label: "Pricing",
    href: "/pricing",
  },
  {
    label: "Admin",
    superuserOnly: true,
    children: [
      {
        label: "User Management",
        subLabel: "Create, edit, and deactivate accounts",
        href: "/admin",
      },
      {
        label: "Blog Admin",
        subLabel: "Write and publish blog posts",
        href: "/admin/blog",
      },
    ],
  },
]

interface WithSubnavigationProps {
  /** Drop the Sign In / Sign Up buttons for signed-out visitors (used by /profile). */
  hideSignedOutAuth?: boolean
}

export default function WithSubnavigation({
  hideSignedOutAuth = false,
}: WithSubnavigationProps = {}) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const { user } = useAuth()
  // The dashboard at "/" is public, so the logo always returns there.
  const logoHref = "/"

  // Superuser-only entries disappear for everyone else, and a group left with
  // no visible children drops out rather than rendering an empty dropdown.
  const isSuperuser = Boolean(user?.is_superuser)
  const navItems = NAV_ITEMS.filter(
    (item) => !item.superuserOnly || isSuperuser,
  )
    .map((item) =>
      item.children
        ? {
            ...item,
            children: item.children.filter(
              (child) => !child.superuserOnly || isSuperuser,
            ),
          }
        : item,
    )
    .filter((item) => !item.children || item.children.length > 0)

  // The header is always the deep-evergreen band (--header-bg) with lime,
  // whatever the page theme: `dark` scopes the dark tokens to this subtree, so
  // the logo, links and buttons inside pick up the dark palette in light mode
  // too. Sticky, so it stays in view while the page scrolls; the sticky
  // sidebars below it offset by its 60px height.
  return (
    <nav className="dark sticky top-0 z-50 bg-header text-foreground shadow-md shadow-black/10">
      <div className="flex h-[60px] items-center px-4">
        {/* Mobile hamburger */}
        <div className="flex md:hidden mr-2">
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label="Toggle Navigation"
            className="p-1 rounded text-foreground hover:bg-white/10"
          >
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        {/* Logo */}
        <div className="flex flex-1 items-center px-4">
          <Link href={logoHref}>
            <Logo />
          </Link>

          {/* Desktop nav */}
          <div className="hidden md:flex ml-10 w-full items-center justify-center gap-4">
            {navItems.map((navItem) =>
              navItem.children ? (
                <DropdownMenu key={navItem.label}>
                  <DropdownMenuTrigger asChild>
                    <button className="flex items-center gap-1 px-2 py-1 text-sm font-medium text-foreground/85 hover:text-ui-accent transition-colors">
                      {navItem.label}
                      <ChevronDown size={14} />
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent>
                    {navItem.children.map((child) => (
                      <DropdownMenuItem key={child.label} asChild>
                        <Link href={child.href ?? "#"} className="flex flex-col">
                          <span className="font-medium">{child.label}</span>
                          {child.subLabel && (
                            <span className="text-xs text-muted-foreground">
                              {child.subLabel}
                            </span>
                          )}
                        </Link>
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>
              ) : (
                <Link
                  key={navItem.label}
                  href={navItem.href ?? "#"}
                  className="px-2 py-1 text-sm font-medium text-foreground/85 hover:text-ui-accent transition-colors"
                >
                  {navItem.label}
                </Link>
              ),
            )}
          </div>
        </div>

        {/* Auth buttons */}
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <UserMenu hideSignedOutActions={hideSignedOutAuth} />
        </div>
      </div>

      {/* Mobile nav */}
      {mobileOpen && (
        <div className="md:hidden border-t border-white/10 bg-header px-4 py-2">
          {navItems.map((navItem) => (
            <div key={navItem.label} className="py-1">
              {navItem.children ? (
                <>
                  <p className="font-semibold text-sm text-muted-foreground py-1">
                    {navItem.label}
                  </p>
                  {navItem.children.map((child) => (
                    <Link
                      key={child.label}
                      href={child.href ?? "#"}
                      className="block pl-4 py-1 text-sm hover:text-ui-accent"
                      onClick={() => setMobileOpen(false)}
                    >
                      {child.label}
                    </Link>
                  ))}
                </>
              ) : (
                <Link
                  href={navItem.href ?? "#"}
                  className="block py-1 text-sm font-semibold hover:text-ui-accent"
                  onClick={() => setMobileOpen(false)}
                >
                  {navItem.label}
                </Link>
              )}
            </div>
          ))}
        </div>
      )}
    </nav>
  )
}
