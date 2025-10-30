"use client"

import { CheckCircle, Loader2, FileText, Zap, Send } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"

interface OcrPreviewProps {
  step: "idle" | "preprocessing" | "ocr" | "delivery" | "complete"
  progress: number
  extractedText?: string
}

export function OcrPreview({ step, progress, extractedText }: OcrPreviewProps) {
  const steps = [
    {
      key: "preprocessing",
      label: "Pre-proceso de imagen",
      icon: Zap,
      description: "Optimizando imagen para OCR",
    },
    {
      key: "ocr",
      label: "OCR",
      icon: FileText,
      description: "Extrayendo texto de la imagen",
    },
    {
      key: "delivery",
      label: "Entrega texto al Agente",
      icon: Send,
      description: "Preparando texto para clasificación",
    },
  ]

  const getStepStatus = (stepKey: string) => {
    const stepIndex = steps.findIndex((s) => s.key === stepKey)
    const currentIndex = steps.findIndex((s) => s.key === step)

    if (step === "complete") return "complete"
    if (stepIndex < currentIndex) return "complete"
    if (stepIndex === currentIndex) return "active"
    return "pending"
  }

  if (step === "idle") return null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="h-5 w-5" />
          Procesamiento OCR
          {step === "complete" && <CheckCircle className="h-5 w-5 text-green-500" />}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span>Progreso</span>
            <span>{progress}%</span>
          </div>
          <Progress value={progress} className="h-2" />
        </div>

        {/* Steps */}
        <div className="space-y-4">
          {steps.map((stepItem, index) => {
            const status = getStepStatus(stepItem.key)
            const Icon = stepItem.icon

            return (
              <div key={stepItem.key} className="flex items-center gap-4">
                <div
                  className={`
                  w-8 h-8 rounded-full flex items-center justify-center border-2
                  ${
                    status === "complete"
                      ? "bg-green-500 border-green-500 text-white"
                      : status === "active"
                        ? "bg-primary border-primary text-primary-foreground"
                        : "bg-muted border-muted-foreground/25 text-muted-foreground"
                  }
                `}
                >
                  {status === "complete" ? (
                    <CheckCircle className="h-4 w-4" />
                  ) : status === "active" ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Icon className="h-4 w-4" />
                  )}
                </div>

                <div className="flex-1">
                  <p className={`font-medium ${status === "pending" ? "text-muted-foreground" : ""}`}>
                    {stepItem.label}
                  </p>
                  <p className="text-sm text-muted-foreground">{stepItem.description}</p>
                </div>

                {status === "active" && <Badge variant="secondary">En proceso...</Badge>}
                {status === "complete" && <Badge variant="default">Completado</Badge>}
              </div>
            )
          })}
        </div>

        {/* Extracted Text Preview */}
        {extractedText && step === "complete" && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="font-medium">Texto extraído:</h4>
              {/* Sistema monolingüe - detección de idioma eliminada */}
            </div>
            <div className="p-4 bg-muted/50 rounded-lg">
              <p className="text-sm">
                {extractedText.length > 200 ? `${extractedText.substring(0, 200)}...` : extractedText}
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
