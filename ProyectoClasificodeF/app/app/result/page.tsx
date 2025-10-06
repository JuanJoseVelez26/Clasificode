"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { useTranslation } from "react-i18next"
import { Icons } from "@/lib/icons"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import { useToast } from "@/hooks/use-toast"
import { useClassificationStore } from "@/lib/store"
import { api } from "@/lib/api"
import { ConfidenceBadge } from "@/components/confidence-badge"
import { ExplanationPanel } from "@/components/explanation-panel"
import { SimilarItemsList } from "@/components/similar-items-list"
import { HelpChat } from "@/components/help-chat"

export default function ResultPage() {
  const { t } = useTranslation()
  const router = useRouter()
  const { toast } = useToast()

  const {
    inputType,
    rawText,
    ocrText,
    prediction,
    similarities,
    explanation,
    savedCaseId,
    flaggedLowConfidence,
    setPrediction,
    setSimilarities,
    setExplanation,
    setSavedCaseId,
    setFlaggedLowConfidence,
  } = useClassificationStore()

  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)

  // Load classification results on mount
  useEffect(() => {
    const loadResults = async () => {
      try {
        const textToClassify = inputType === "text" ? rawText : ocrText

        if (!textToClassify) {
          router.push("/app/form")
          return
        }

        const response = await api.classify.process({ text: textToClassify })

        const simplifiedResponse = {
          hs: response.topK[0].hs,
          confidence: response.topK[0].confidence,
          description: response.topK[0].description,
          topK: [],
        }

        setPrediction(simplifiedResponse)
        setSimilarities(response.similarities)
        setExplanation(response.explanation)
      } catch (error) {
        toast({
          variant: "destructive",
          title: "Error",
          description: "No se pudieron cargar los resultados de clasificación",
        })
        router.push("/app/form")
      } finally {
        setIsLoading(false)
      }
    }

    loadResults()
  }, [inputType, rawText, ocrText, router, setPrediction, setSimilarities, setExplanation, toast])

  const handleSaveCase = async () => {
    if (!prediction) return

    setIsSaving(true)
    try {
      const caseData = {
        inputType,
        text: inputType === "text" ? rawText : ocrText,
        prediction,
        similarities,
        explanation,
        timestamp: new Date().toISOString(),
      }

      await new Promise((resolve) => setTimeout(resolve, 1000))
      const caseId = `case_${Date.now()}`

      setSavedCaseId(caseId)

      toast({
        title: "Caso guardado",
        description: `Caso guardado con ID: ${caseId}`,
      })
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "No se pudo guardar el caso",
      })
    } finally {
      setIsSaving(false)
    }
  }

  const handleFlagLowConfidence = async () => {
    if (!prediction) return

    try {
      await new Promise((resolve) => setTimeout(resolve, 500))

      setFlaggedLowConfidence(true)

      toast({
        title: "Marcado para auditoría",
        description: "El caso ha sido marcado para revisión por baja confianza",
      })
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "No se pudo marcar el caso para auditoría",
      })
    }
  }

  const handleExport = async (format: "pdf" | "csv") => {
    if (!prediction) return

    setIsExporting(true)
    try {
      await new Promise((resolve) => setTimeout(resolve, 2000))

      toast({
        title: "Exportación completada",
        description: `Resultados exportados en formato ${format.toUpperCase()}`,
      })
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "No se pudo exportar los resultados",
      })
    } finally {
      setIsExporting(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="text-center space-y-4">
          <Icons.Loader />
          <p className="text-muted-foreground">Procesando clasificación...</p>
        </div>
      </div>
    )
  }

  if (!prediction) {
    return (
      <div className="text-center space-y-4">
        <h1 className="text-2xl font-bold">No hay resultados</h1>
        <p className="text-muted-foreground">No se encontraron resultados de clasificación.</p>
        <Button onClick={() => router.push("/app/form")}>Volver al formulario</Button>
      </div>
    )
  }

  const isLowConfidence = prediction.confidence < 0.6
  const isMediumConfidence = prediction.confidence >= 0.6 && prediction.confidence < 0.85
  const isHighConfidence = prediction.confidence >= 0.85

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Resultado de Clasificación</h1>
          <p className="text-muted-foreground">Código HS definitivo para tu producto</p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => setChatOpen(true)}>
            <Icons.MessageCircle />
            <span className="ml-2">Ayuda</span>
          </Button>
          <Button variant="outline" onClick={() => router.push("/app/form")}>
            Nueva Clasificación
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Icons.Target />
                  Clasificación Final
                </span>
                <ConfidenceBadge confidence={prediction.confidence} />
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="text-center p-8 bg-primary/5 rounded-2xl border-2 border-primary/20">
                <div className="text-5xl font-bold text-primary mb-3">{prediction.hs}</div>
                <p className="text-lg text-muted-foreground mb-2">Código HS Definitivo</p>
                <p className="text-sm text-muted-foreground max-w-md mx-auto leading-relaxed">
                  {prediction.description || "Clasificación basada en análisis de contenido"}
                </p>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-medium">Nivel de Confianza</span>
                  <span className="text-2xl font-bold">{Math.round(prediction.confidence * 100)}%</span>
                </div>
                <Progress
                  value={prediction.confidence * 100}
                  className={`h-4 ${
                    isHighConfidence
                      ? "[&>div]:bg-green-500"
                      : isMediumConfidence
                        ? "[&>div]:bg-yellow-500"
                        : "[&>div]:bg-red-500"
                  }`}
                />
                <div className="text-center">
                  <Badge variant={isHighConfidence ? "default" : isMediumConfidence ? "secondary" : "destructive"}>
                    {isHighConfidence ? "Alta Confianza" : isMediumConfidence ? "Confianza Media" : "Baja Confianza"}
                  </Badge>
                </div>
              </div>

              {isLowConfidence && (
                <div className="p-4 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded-2xl">
                  <div className="flex items-start gap-3">
                    <Icons.AlertTriangle />
                    <div className="flex-1">
                      <h4 className="font-medium text-red-900 dark:text-red-100">Confianza Baja Detectada</h4>
                      <p className="text-sm text-red-700 dark:text-red-300 mt-1">
                        Este resultado tiene baja confianza y podría requerir revisión manual.
                      </p>
                      <Button
                        size="sm"
                        variant="outline"
                        className="mt-3 border-red-300 text-red-700 hover:bg-red-50 bg-transparent"
                        onClick={handleFlagLowConfidence}
                        disabled={flaggedLowConfidence}
                      >
                        {flaggedLowConfidence ? (
                          <>
                            <Icons.Check />
                            <span className="ml-2">Marcado para Auditoría</span>
                          </>
                        ) : (
                          <>
                            <Icons.AlertTriangle />
                            <span className="ml-2">Marcar para Auditoría</span>
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <ExplanationPanel explanation={explanation} selectedHS={prediction.hs} />

          <SimilarItemsList similarities={similarities} />
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Acciones</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button className="w-full justify-start" onClick={handleSaveCase} disabled={isSaving || !!savedCaseId}>
                {isSaving ? <Icons.Clock /> : savedCaseId ? <Icons.Check /> : <Icons.Save />}
                <span className="ml-2">{savedCaseId ? "Caso Guardado" : t("results.save")}</span>
              </Button>

              <Separator />

              <div className="space-y-2">
                <p className="text-sm font-medium">Exportar Resultados</p>
                <Button
                  variant="outline"
                  className="w-full justify-start bg-transparent"
                  onClick={() => handleExport("pdf")}
                  disabled={isExporting}
                >
                  <Icons.Download />
                  <span className="ml-2">Exportar PDF</span>
                </Button>
                <Button
                  variant="outline"
                  className="w-full justify-start bg-transparent"
                  onClick={() => handleExport("csv")}
                  disabled={isExporting}
                >
                  <Icons.Download />
                  <span className="ml-2">Exportar CSV</span>
                </Button>
              </div>
            </CardContent>
          </Card>

          {savedCaseId && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Información del Caso</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">ID:</span>
                  <span className="font-mono">{savedCaseId}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Tipo:</span>
                  <span className="capitalize">{inputType}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Estado:</span>
                  <Badge variant={flaggedLowConfidence ? "destructive" : "default"}>
                    {flaggedLowConfidence ? "En Auditoría" : "Completado"}
                  </Badge>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      <HelpChat
        open={chatOpen}
        onOpenChange={setChatOpen}
        context={{
          hsCode: prediction.hs,
          confidence: prediction.confidence,
          inputText: inputType === "text" ? rawText : ocrText,
        }}
      />
    </div>
  )
}
