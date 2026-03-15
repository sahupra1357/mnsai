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

interface NavItem {
  label: string
  subLabel?: string
  children?: Array<NavItem>
  href?: string
}

const NAV_ITEMS: Array<NavItem> = [
  {
    label: "Product",
    children: [
      {
        label: "Dashboard",
        subLabel: "Trending Design to inspire you",
        href: "/dashboard",
      },
      {
        label: "Items",
        subLabel: "Up-and-coming Designers",
        href: "/items",
      },
    ],
  },
  {
    label: "Solutions",
    children: [
      {
        label: "User Settings",
        subLabel: "Find your dream design job",
        href: "/settings",
      },
      {
        label: "Data Extraction",
        subLabel: "An exclusive list for contract work",
        href: "/extractor",
      },
      {
        label: "Course Search",
        subLabel: "Find the best courses near you",
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
    href: "#",
  },
  {
    label: "Pricing",
    href: "#",
  },
]

export default function WithSubnavigation() {
  const [mobileOpen, setMobileOpen] = useState(false)

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
          <Link href="/">
            <Image
              src="/assets/images/mnsAI_2.png"
              alt="mnsAI logo"
              width={140}
              height={50}
              style={{ width: "auto", height: "auto" }}
              priority
            />
          </Link>

          {/* Desktop nav */}
          <div className="hidden md:flex ml-10 w-full items-center justify-center gap-4">
            {NAV_ITEMS.map((navItem) =>
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
          <UserMenu />
        </div>
      </div>

      {/* Mobile nav */}
      {mobileOpen && (
        <div className="md:hidden border-t border-border bg-background px-4 py-2">
          {NAV_ITEMS.map((navItem) => (
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
