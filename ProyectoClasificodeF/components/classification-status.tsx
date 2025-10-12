"use client"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Icons } from "@/lib/icons"

interface ClassificationStatusProps {
  hsCode: string
  title: string
  confidence: number
  method?: string
}

export function ClassificationStatus({ hsCode, title, confidence, method }: ClassificationStatusProps) {
  const getConfidenceColor = (conf: number) => {
    if (conf >= 0.9) return "text-green-600"
    if (conf >= 0.7) return "text-yellow-600"
    return "text-red-600"
  }

  const getConfidenceLabel = (conf: number) => {
    if (conf >= 0.9) return "Muy Alta"
    if (conf >= 0.7) return "Alta"
    if (conf >= 0.5) return "Media"
    return "Baja"
  }

  const getMethodBadge = (method?: string) => {
    if (!method) return null
    
    if (method === "Reglas específicas") {
      return <Badge variant="default" className="bg-green-100 text-green-800">Reglas específicas</Badge>
    }
    if (method === "Motor RGI") {
      return <Badge variant="secondary" className="bg-blue-100 text-blue-800">Motor RGI</Badge>
    }
    return <Badge variant="outline">{method}</Badge>
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Icons.CheckCircle className="h-5 w-5 text-green-600" />
            Clasificación Final
          </span>
          {getMethodBadge(method)}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Código HS */}
        <div className="text-center">
          <div className="text-4xl font-bold text-primary mb-2">{hsCode}</div>
          <div className="text-sm text-muted-foreground">Código HS Definitivo</div>
        </div>

        {/* Descripción */}
        <div className="text-center">
          <div className="text-lg font-medium">{title}</div>
        </div>

        {/* Nivel de confianza */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span>Nivel de Confianza</span>
            <span className={`font-medium ${getConfidenceColor(confidence)}`}>
              {Math.round(confidence * 100)}%
            </span>
          </div>
          <Progress value={confidence * 100} className="h-2" />
          <div className="text-center">
            <Badge 
              variant={confidence >= 0.7 ? "default" : "destructive"}
              className={confidence >= 0.7 ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}
            >
              {getConfidenceLabel(confidence)} Confianza
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
