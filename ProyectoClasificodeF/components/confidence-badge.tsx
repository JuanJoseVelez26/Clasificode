"use client"

import { Badge } from "@/components/ui/badge"
import { TrendingUp, TrendingDown, Minus } from "lucide-react"

interface ConfidenceBadgeProps {
  confidence: number
}

export function ConfidenceBadge({ confidence }: ConfidenceBadgeProps) {
  const getConfidenceLevel = () => {
    if (confidence >= 0.85) return { 
      label: "Alta", 
      variant: "default" as const, 
      icon: TrendingUp,
      className: "bg-green-100 text-green-800 border-green-200 hover:bg-green-100 dark:bg-green-900/20 dark:text-green-400 dark:border-green-800"
    }
    if (confidence >= 0.6) return { 
      label: "Media", 
      variant: "secondary" as const, 
      icon: Minus,
      className: "bg-yellow-100 text-yellow-800 border-yellow-200 hover:bg-yellow-100 dark:bg-yellow-900/20 dark:text-yellow-400 dark:border-yellow-800"
    }
    return { 
      label: "Baja", 
      variant: "destructive" as const, 
      icon: TrendingDown,
      className: "bg-red-100 text-red-800 border-red-200 hover:bg-red-100 dark:bg-red-900/20 dark:text-red-400 dark:border-red-800"
    }
  }

  const { label, variant, icon: Icon, className } = getConfidenceLevel()

  return (
    <Badge variant={variant} className={`gap-2 px-3 py-1.5 font-semibold ${className}`}>
      <Icon className="h-4 w-4" />
      <span className="text-sm">{label} ({Math.round(confidence * 100)}%)</span>
    </Badge>
  )
}
