"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Info, Lightbulb } from "lucide-react"

interface ExplanationPanelProps {
  explanation?: {
    factors: Array<{ name: string; weight: number; note?: string }>
    rationale: string
  }
  selectedHS: string
}

export function ExplanationPanel({ explanation, selectedHS }: ExplanationPanelProps) {
  if (!explanation) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Lightbulb className="h-5 w-5" />
          Explicación de la Clasificación
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Rationale */}
        <div className="p-4 bg-muted/50 rounded-2xl">
          <div className="flex items-start gap-3">
            <Info className="h-5 w-5 text-primary mt-0.5" />
            <div>
              <h4 className="font-medium mb-2">Justificación para {selectedHS}</h4>
              <p className="text-sm text-muted-foreground leading-relaxed">{explanation.rationale}</p>
            </div>
          </div>
        </div>

        {/* Factors */}
        <div className="space-y-4">
          <h4 className="font-medium">Factores de Decisión</h4>
          <div className="space-y-3">
            {explanation.factors.map((factor, index) => (
              <div key={index} className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">{factor.name}</span>
                  <span className="text-muted-foreground">{Math.round(factor.weight * 100)}%</span>
                </div>
                <Progress value={factor.weight * 100} className="h-2" />
                {factor.note && (
                  <p className="text-xs text-muted-foreground pl-2 border-l-2 border-muted">{factor.note}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
