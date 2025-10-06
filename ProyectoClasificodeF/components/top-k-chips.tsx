"use client"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

interface TopKChipsProps {
  alternatives: Array<{ hs: string; confidence: number }>
  selectedAlternative: string | null
  onSelect: (hsCode: string) => void
}

export function TopKChips({ alternatives, selectedAlternative, onSelect }: TopKChipsProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {alternatives.map((alt, index) => {
        const isSelected = selectedAlternative === alt.hs
        const isMain = index === 0

        return (
          <Button
            key={alt.hs}
            variant={isSelected ? "default" : "outline"}
            size="sm"
            onClick={() => onSelect(alt.hs)}
            className="h-auto p-3 flex-col gap-1"
          >
            <div className="flex items-center gap-2">
              <span className="font-mono font-medium">{alt.hs}</span>
              {isMain && (
                <Badge variant="secondary" className="text-xs">
                  Principal
                </Badge>
              )}
            </div>
            <span className="text-xs opacity-75">{Math.round(alt.confidence * 100)}% confianza</span>
          </Button>
        )
      })}
    </div>
  )
}
