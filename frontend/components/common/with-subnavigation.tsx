"use client"

import { useState } from "react"
import Link from "next/link"
import Image from "next/image"
import { Menu, X, ChevronDown } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import UserMenu from "./user-menu"
import useAuth from "@/hooks/use-auth"

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
    label: "Product",
    children: [
      {
        label: "Dashboard",
        subLabel: "Trending Design to inspire you",
        href: "/",
      },
    ],
  },
  {
    label: "Solutions",
    children: [
      // Settings is reached through the user menu ("My profile"), not here.
      {
        label: "Data Extraction",
        subLabel: "Review OCR results with confidence and parser provenance",
        href: "/document-extractions",
      },
      {
        label: "Contract Review",
        subLabel: "AI review of contracts for risks, clauses, and obligations",
        href: "/solutions/contract-review",
      },
      {
        label: "Career Explorer Empowered by AI",
        subLabel: "Evidence-backed research on any field and the colleges that teach it",
        href: "/solutions/course-search",
      },
      {
        label: "ATS Resume Matcher",
        subLabel: "Match your resume to any job description",
        href: "/solutions/ats-resume-matcher",
      },
    ],
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
    ],
  },
  {
    label: "Pricing",
    href: "/pricing",
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

  return (
    <nav className="border-b border-border bg-background">
      <div className="flex min-h-[60px] items-center px-4 py-2">
        {/* Mobile hamburger */}
        <div className="flex md:hidden mr-2">
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label="Toggle Navigation"
            className="p-1 rounded hover:bg-muted"
          >
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        {/* Logo */}
        <div className="flex flex-1 items-center px-4">
          <Link href={logoHref}>
            <Image
              src="/assets/images/mnsAI_2-transparent.png"
              alt="mnsAI logo"
              width={140}
              height={50}
              style={{ width: "auto", height: "auto" }}
              className="dark:brightness-0 dark:invert"
              priority
            />
          </Link>

          {/* Desktop nav */}
          <div className="hidden md:flex ml-10 w-full items-center justify-center gap-4">
            {navItems.map((navItem) =>
              navItem.children ? (
                <DropdownMenu key={navItem.label}>
                  <DropdownMenuTrigger asChild>
                    <button className="flex items-center gap-1 px-2 py-1 text-sm font-medium text-ui-main hover:text-[#00766C] transition-colors">
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
                  className="px-2 py-1 text-sm font-medium text-ui-main hover:text-[#00766C] transition-colors"
                >
                  {navItem.label}
                </Link>
              ),
            )}
          </div>
        </div>

        {/* Auth buttons */}
        <div className="flex items-center gap-2">
          <UserMenu hideSignedOutActions={hideSignedOutAuth} />
        </div>
      </div>

      {/* Mobile nav */}
      {mobileOpen && (
        <div className="md:hidden border-t border-border bg-background px-4 py-2">
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
                      className="block pl-4 py-1 text-sm hover:text-[#00766C]"
                      onClick={() => setMobileOpen(false)}
                    >
                      {child.label}
                    </Link>
                  ))}
                </>
              ) : (
                <Link
                  href={navItem.href ?? "#"}
                  className="block py-1 text-sm font-semibold hover:text-[#00766C]"
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
