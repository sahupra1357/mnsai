"use client"

import { useTheme } from "next-themes"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"

const Appearance = () => {
  const { theme, setTheme } = useTheme()

  return (
    <div className="max-w-full">
      <h3 className="text-sm font-semibold">Appearance</h3>
      <div className="mt-4 flex flex-col gap-3">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="radio"
            name="theme"
            value="light"
            checked={theme === "light"}
            onChange={() => setTheme("light")}
            className="accent-ui-main"
          />
          <Label className="cursor-pointer">
            Light Mode
            <Badge className="ml-1 bg-primary text-primary-foreground">Default</Badge>
          </Label>
        </label>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="radio"
            name="theme"
            value="dark"
            checked={theme === "dark"}
            onChange={() => setTheme("dark")}
            className="accent-ui-main"
          />
          <Label className="cursor-pointer">Dark Mode</Label>
        </label>
      </div>
    </div>
  )
}

export default Appearance
