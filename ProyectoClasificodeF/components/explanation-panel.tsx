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
    <Card className="shadow-lg">
      <CardHeader className="bg-gradient-to-r from-primary/5 to-primary/10">
        <CardTitle className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 rounded-lg">
            <Lightbulb className="h-5 w-5 text-primary" />
          </div>
          <div>
            <span className="text-xl">Explicación de la Clasificación</span>
            <p className="text-sm text-muted-foreground font-normal mt-1">
              Análisis detallado del proceso de clasificación
            </p>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6 p-6">
        {/* Rationale */}
        <div className="p-6 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-950/20 dark:to-indigo-950/20 rounded-2xl border border-blue-200 dark:border-blue-800">
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
              <Info className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div className="flex-1">
              <h4 className="font-semibold text-lg mb-3 text-blue-900 dark:text-blue-100">
                Justificación para {selectedHS}
              </h4>
              <div className="prose prose-sm max-w-none">
                <p className="text-gray-700 dark:text-gray-300 leading-relaxed font-medium">
                  {explanation.rationale}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Factors */}
        <div className="space-y-5">
          <div className="flex items-center gap-3">
            <div className="w-1 h-6 bg-primary rounded-full"></div>
            <h4 className="font-semibold text-lg">Factores de Decisión</h4>
          </div>
          
          <div className="grid gap-4">
            {explanation.factors.map((factor, index) => (
              <div key={index} className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between mb-3">
                  <span className="font-semibold text-gray-900 dark:text-gray-100">{factor.name}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-primary">
                      {Math.round(factor.weight * 100)}%
                    </span>
                    <div className="w-16 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-primary to-primary/80 rounded-full transition-all duration-500"
                        style={{ width: `${factor.weight * 100}%` }}
                      ></div>
                    </div>
                  </div>
                </div>
                {factor.note && (
                  <div className="mt-3 p-3 bg-white/60 dark:bg-gray-900/60 rounded-lg border-l-4 border-primary/30">
                    <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                      {factor.note}
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
