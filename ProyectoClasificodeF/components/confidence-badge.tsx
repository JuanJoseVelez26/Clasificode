"use client"

import { Badge } from "@/components/ui/badge"
import { TrendingUp, TrendingDown, Minus } from "lucide-react"

interface ConfidenceBadgeProps {
  confidence: number
}

export function ConfidenceBadge({ confidence }: ConfidenceBadgeProps) {
  const getConfidenceLevel = () => {
    if (confidence >= 0.85) return { label: "Alta", variant: "default" as const, icon: TrendingUp }
    if (confidence >= 0.6) return { label: "Media", variant: "secondary" as const, icon: Minus }
    return { label: "Baja", variant: "destructive" as const, icon: TrendingDown }
  }

  const { label, variant, icon: Icon } = getConfidenceLevel()

  return (
    <Badge variant={variant} className="gap-1">
      <Icon className="h-3 w-3" />
      {label} ({Math.round(confidence * 100)}%)
    </Badge>
  )
}
