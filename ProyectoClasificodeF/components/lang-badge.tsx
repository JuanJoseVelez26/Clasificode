"use client"

import { Badge } from "@/components/ui/badge"
import { Languages } from "lucide-react"

interface LangBadgeProps {
  lang: "es" | "en"
}

export function LangBadge({ lang }: LangBadgeProps) {
  const langLabels = {
    es: "Español",
    en: "English",
  }

  return (
    <Badge variant="secondary" className="gap-1">
      <Languages className="h-3 w-3" />
      {langLabels[lang]}
    </Badge>
  )
}
