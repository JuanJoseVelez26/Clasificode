"use client"

import { Icons } from "@/lib/icons"
import { useTheme } from "next-themes"
import { Button } from "@/components/ui/button"

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()

  return (
    <Button
      variant="outline"
      size="icon"
      onClick={() => setTheme(theme === "light" ? "dark" : "light")}
      className="h-9 w-9"
    >
      <Icons.Sun />
      <Icons.Moon />
      <span className="sr-only">Toggle theme</span>
    </Button>
  )
}
