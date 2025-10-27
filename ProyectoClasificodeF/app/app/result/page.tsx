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
    setFlaggedLowConfidence,
  } = useClassificationStore()

  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)

  // Load classification results on mount
  useEffect(() => {
    // Leer resultados desde el store (ya clasificados en form/page.tsx)
    if (!prediction) {
      // Si no hay resultados en el store, redirigir a form
      toast({
        variant: "destructive",
        title: "Sin resultados",
        description: "No hay resultados de clasificación. Por favor, clasifica un producto primero.",
      })
      router.push("/app/form")
      return
    }

    setIsLoading(false)
    
    // Mostrar notificación de éxito si hay resultados
    if (prediction.confidence >= 0.7) {
      toast({
        title: "Clasificación exitosa",
        description: `Producto clasificado con ${Math.round(prediction.confidence * 100)}% de confianza`,
      })
    } else {
      toast({
        title: "Baja confianza",
        description: "La clasificación tiene baja confianza. Revisa los resultados cuidadosamente.",
        variant: "destructive"
      })
    }
  }, [prediction, router, toast])

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

      // TODO: Implementar guardado real en backend cuando esté disponible

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
      const textToClassify = inputType === "text" ? rawText : ocrText
      
      const exportData = {
        hs_code: prediction.hs,
        description: prediction.topK[0]?.title || prediction.title || "",
        confidence: prediction.confidence,
        product_description: textToClassify || "",
        input_type: inputType,
        explanation: explanation?.rationale || "",
        similar_items: similarities || [],
        top_k: prediction.topK || []
      }

      let blob: Blob
      let filename: string

      if (format === "pdf") {
        blob = await api.export.pdf(exportData)
        filename = `clasificacion_${prediction.hs}_${new Date().toISOString().slice(0, 10)}.html`
      } else {
        blob = await api.export.csv(exportData)
        filename = `clasificacion_${prediction.hs}_${new Date().toISOString().slice(0, 10)}.csv`
      }

      // Crear URL para descarga
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)

      toast({
        title: "Exportación completada",
        description: `Resultados exportados en formato ${format.toUpperCase()}`,
      })
    } catch (error) {
      console.error("Error en exportación:", error)
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
              <div className="text-center p-8 bg-gradient-to-br from-primary/5 to-primary/10 rounded-2xl border-2 border-primary/20 shadow-lg">
                <div className="text-6xl font-bold text-primary mb-4 tracking-wider">{prediction.hs}</div>
                <p className="text-xl text-muted-foreground mb-4 font-medium">Código HS Definitivo</p>
                
                {/* Descripción mejorada */}
                <div className="bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm rounded-xl p-6 border border-primary/10 shadow-inner">
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 w-2 h-2 bg-primary rounded-full mt-2"></div>
                    <div className="text-left">
                      <h3 className="text-sm font-semibold text-primary mb-2 uppercase tracking-wide">Descripción del Producto</h3>
                      <p className="text-base text-gray-700 dark:text-gray-300 leading-relaxed font-medium">
                        {prediction.topK[0]?.title || prediction.title || "Clasificación basada en análisis de contenido"}
                      </p>
                    </div>
                  </div>
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
                  <span className="ml-2">Exportar HTML</span>
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
