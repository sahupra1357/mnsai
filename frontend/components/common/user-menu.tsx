"use client"

import Link from "next/link"
import { UserRound, LogOut, User } from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import useAuth from "@/hooks/use-auth"

const UserMenu = () => {
  const { logout, user } = useAuth()

  if (!user) {
    return (
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          className="text-ui-main font-semibold hover:bg-[#00766C] hover:text-white"
          asChild
        >
          <Link href="/login">Sign In</Link>
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="hidden md:inline-flex text-ui-main font-semibold hover:bg-[#00766C] hover:text-white"
          asChild
        >
          <Link href="/signup">Sign Up</Link>
        </Button>
      </div>
    )
  }

  return (
    <div className="hidden md:block">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            size="icon"
            className="rounded-full bg-ui-main hover:bg-[#00766C] text-white"
            aria-label="Options"
            data-testid="user-menu"
          >
            <UserRound size={18} />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem asChild>
            <Link href="/settings" className="flex items-center gap-2">
              <User size={18} />
              My profile
            </Link>
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={logout}
            className="flex items-center gap-2 text-ui-danger font-bold focus:text-ui-danger"
          >
            <LogOut size={18} />
            Log out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  )
}

export default UserMenu
