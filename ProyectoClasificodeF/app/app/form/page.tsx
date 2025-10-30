"use client"

import "@/lib/i18n"
import { useState } from "react"
import { useRouter } from "next/navigation"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useI18n } from "@/lib/i18n"
import { Icons } from "@/lib/icons"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { useToast } from "@/hooks/use-toast"
import { useClassificationStore } from "@/lib/store"
import { api } from "@/lib/api"
import { apiClient } from "@/lib/apiClient"
import { FileDropzone } from "@/components/file-dropzone"
import { OcrPreview } from "@/components/ocr-preview"

const formSchema = z
  .object({
    inputType: z.enum(["text", "file"]),
    text: z.string().optional(),
    files: z.array(z.any()).optional(),
  })
  .refine(
    (data) => {
      if (data.inputType === "text") {
        return data.text && data.text.length >= 10
      }
      if (data.inputType === "file") {
        return data.files && data.files.length > 0
      }
      return false
    },
    {
      message: "Debes proporcionar texto (mín. 10 caracteres) o subir al menos un archivo",
    },
  )

// Ejemplos de productos para ayudar al usuario
const productExamples = [
  "Computadora portátil de 15 pulgadas con procesador Intel i7, 16GB RAM, 512GB SSD",
  "Camiseta de algodón 100%, talla M, color azul, manga corta",
  "Café en grano tostado de Colombia, 500g, tueste medio",
  "Automóvil eléctrico de 4 puertas, autonomía 400 km, carga rápida",
  "Refrigerador de dos puertas, 350 litros, tecnología inverter, acero inoxidable",
  "Gorra de béisbol de algodón, color rojo, logo bordado",
  "Ternero vivo de tres meses",
  "Aceite de oliva virgen extra, 1 litro, botella de vidrio, origen España"
]

type FormData = z.infer<typeof formSchema>

export default function FormPage() {
  const { t } = useI18n()
  const router = useRouter()
  const { toast } = useToast()

  const { inputType, rawText, files, ocrText, setInputType, setRawText, setFiles, setOcrText, setClassificationResult, setCaseId, setCaseData, setFlaggedLowConfidence, reset } =
    useClassificationStore()

  const [isProcessing, setIsProcessing] = useState(false)
  const [ocrProgress, setOcrProgress] = useState(0)
  const [ocrStep, setOcrStep] = useState<"idle" | "preprocessing" | "ocr" | "delivery" | "complete">("idle")

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      inputType: inputType,
      text: rawText || "",
      files: files || [],
    },
  })

  const watchedInputType = watch("inputType")
  const watchedText = watch("text")

  // Handle input type change
  const handleInputTypeChange = (type: "text" | "file") => {
    setInputType(type)
    setValue("inputType", type)
    reset() // Clear previous data when switching types
  }

  // Handle text input
  const handleTextChange = (text: string) => {
    setRawText(text)
    setValue("text", text)

    // Simple language detection simulation
    if (text.length > 20) {
      const spanishWords = ["el", "la", "de", "que", "y", "con", "en", "para", "por", "un", "una"]
      const englishWords = ["the", "and", "of", "to", "a", "in", "for", "is", "on", "that", "by"]

      const lowerText = text.toLowerCase()
      const spanishCount = spanishWords.filter((word) => lowerText.includes(word)).length
      const englishCount = englishWords.filter((word) => lowerText.includes(word)).length

      // Sistema monolingüe - detección de idioma eliminada
      // const detected = spanishCount > englishCount ? "es" : "en"
      // setLang(detected) // Función eliminada para sistema monolingüe
    }
  }

  // Handle file upload
  const handleFilesChange = (uploadedFiles: File[]) => {
    const fileObjects = uploadedFiles.map((file) => ({
      id: Math.random().toString(36).substr(2, 9),
      name: file.name,
      size: file.size,
      type: file.type,
      url: URL.createObjectURL(file),
      file,
    }))

    setFiles(fileObjects)
    setValue("files", fileObjects)
  }

  // Process OCR
  const processOCR = async (files: any[]) => {
    setOcrStep("preprocessing")
    setOcrProgress(10)

    await new Promise((resolve) => setTimeout(resolve, 1000))

    setOcrStep("ocr")
    setOcrProgress(50)

    try {
      // Process first file for demo
      const response = await api.ocr.process({ file: files[0].file })

      setOcrProgress(90)
      setOcrStep("delivery")

      await new Promise((resolve) => setTimeout(resolve, 500))

      setOcrText(response.ocrText)
      setLang(response.lang)
      // Sistema monolingüe - detección de idioma eliminada
      setOcrProgress(100)
      setOcrStep("complete")

      return response.ocrText
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error en OCR",
        description: "No se pudo procesar el archivo. Intenta de nuevo.",
      })
      setOcrStep("idle")
      setOcrProgress(0)
      throw error
    }
  }

  // Submit form
  const onSubmit = async (data: FormData) => {
    setIsProcessing(true)

    try {
      let textToProcess = ""

      if (data.inputType === "text") {
        textToProcess = data.text || ""
      } else if (data.inputType === "file" && data.files) {
        // File upload no está implementado en backend aún
        toast({
          variant: "destructive",
          title: "Función no disponible",
          description: "La clasificación por archivo aún no está implementada en el servidor.",
        })
        setIsProcessing(false)
        return
      }

      if (!textToProcess || textToProcess.length < 10) {
        toast({
          variant: "destructive",
          title: "Descripción insuficiente",
          description: "La descripción debe tener al menos 10 caracteres.",
        })
        setIsProcessing(false)
        return
      }

      // PASO 1: Crear caso en el backend
      toast({
        title: "Creando caso...",
        description: "Preparando la clasificación...",
      })

      const title = textToProcess.slice(0, 80)
      const desc = textToProcess.slice(80) || textToProcess
      
             const caseRes = await apiClient.post("/cases", { 
         product_title: title, 
         product_desc: desc 
       })

       if (!caseRes.data) {
         throw new Error("No se pudo crear el caso en el servidor")
       }

       const caseId = caseRes.data.details?.case_id || caseRes.data.details?.id || caseRes.data.case_id
       if (!caseId) {
         throw new Error("El servidor no devolvió un ID de caso válido")
       }

       // Guardar case ID en el store
       setCaseId(String(caseId))
       setCaseData(caseRes.data.details || caseRes.data)

       toast({
         title: "Clasificando producto...",
         description: "Analizando características del producto...",
       })

       // PASO 2: Clasificar el caso
       const classifyRes = await apiClient.post(`/api/v1/classify/${caseId}`, {})

       if (!classifyRes.data) {
         throw new Error("No se pudo clasificar el producto")
       }

       const result = classifyRes.data.details || classifyRes.data

      // Guardar resultado en el store
      setClassificationResult({
        hs: result.national_code || result.hs || "0000.00.00",
        title: result.title || title,
        confidence: result.confidence || 0.5,
        rationale: result.rationale || "Clasificación generada automáticamente",
        topK: result.candidates?.map((c: any) => ({
          hs: c.hs_code || c.national_code || "0000.00.00",
          confidence: c.confidence || 0.5,
          title: c.title,
        })) || [],
      })

      setFlaggedLowConfidence((result.confidence || 0.5) < 0.7)

      // Navegar a resultados
      router.push("/app/result")

      toast({
        title: "Clasificación completada",
        description: "Redirigiendo a los resultados...",
      })
    } catch (error: any) {
      console.error("Error en clasificación:", error)
      toast({
        variant: "destructive",
        title: "Error de clasificación",
        description: error?.message || "No se pudo clasificar el producto. Inténtalo de nuevo.",
      })
    } finally {
      setIsProcessing(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Clasificar Producto</h1>
        <p className="text-muted-foreground">Describe tu producto o sube documentos para obtener la clasificación HS</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Input Type Selector */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Icons.FileText />
              {t("form.inputType")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Button
                type="button"
                variant={watchedInputType === "text" ? "default" : "outline"}
                className="h-20 flex-col gap-2"
                onClick={() => handleInputTypeChange("text")}
              >
                <Icons.FileText />
                {t("form.text")}
              </Button>
              <Button
                type="button"
                variant={watchedInputType === "file" ? "default" : "outline"}
                className="h-20 flex-col gap-2"
                onClick={() => handleInputTypeChange("file")}
              >
                <Icons.Upload />
                {t("form.file")}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Text Input */}
        {watchedInputType === "text" && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Descripción del Producto</span>
                {/* Detección de idioma eliminada - sistema monolingüe */}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="text">Describe tu producto</Label>
                <Textarea
                  id="text"
                  placeholder={t("form.textPlaceholder")}
                  className="min-h-32 resize-none"
                  value={watchedText || ""}
                  onChange={(e) => handleTextChange(e.target.value)}
                />
                <div className="flex items-center justify-between text-sm text-muted-foreground">
                  <span>
                    {watchedText?.length || 0} caracteres
                    {(watchedText?.length || 0) < 15 && <span className="text-destructive ml-1">(mínimo 15)</span>}
                  </span>
                {/* Sistema monolingüe - traducción eliminada */}
                </div>
              </div>

              {/* Sistema monolingüe - sección de traducción eliminada */}

              {errors.text && <p className="text-sm text-destructive">{errors.text.message}</p>}
            </CardContent>
          </Card>
        )}

        {/* File Input */}
        {watchedInputType === "file" && (
          <Card>
            <CardHeader>
              <CardTitle>Subir Documentos o Imágenes</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <FileDropzone
                onFilesChange={handleFilesChange}
                acceptedTypes={[".pdf", ".jpg", ".jpeg", ".png", ".tiff"]}
                maxSize={20 * 1024 * 1024} // 20MB
                multiple
              />

              {files && files.length > 0 && (
                <div className="space-y-4">
                  <div className="grid gap-2">
                    {files.map((file) => (
                      <div key={file.id} className="flex items-center gap-3 p-3 bg-muted/50 rounded-lg">
                        <Icons.FileText />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">{file.name}</p>
                          <p className="text-xs text-muted-foreground">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                        </div>
                        <Badge variant="secondary">{file.type}</Badge>
                      </div>
                    ))}
                  </div>

                  {/* OCR Progress */}
                  {ocrStep !== "idle" && (
                    <OcrPreview step={ocrStep} progress={ocrProgress} extractedText={ocrText} />
                  )}
                </div>
              )}

              {errors.files && <p className="text-sm text-destructive">{errors.files.message}</p>}
            </CardContent>
          </Card>
        )}

        {/* Submit Button */}
        <div className="flex justify-end">
          <Button
            type="submit"
            size="lg"
            disabled={isProcessing || (watchedInputType === "text" && (watchedText?.length || 0) < 10)}
            className="min-w-48"
          >
            {isProcessing && <Icons.Loader />}
            <span className="ml-2">{t("form.process")}</span>
          </Button>
        </div>
      </form>

      {/* Ejemplos de productos */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Icons.Lightbulb />
            Ejemplos de productos para clasificar
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Haz clic en cualquier ejemplo para usarlo como plantilla
          </p>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {productExamples.map((example, index) => (
              <Button
                key={index}
                variant="outline"
                className="h-auto p-4 text-left justify-start whitespace-normal"
                onClick={() => {
                  setValue("text", example)
                  setValue("inputType", "text")
                }}
              >
                <div className="text-sm">
                  <div className="font-medium mb-1">Ejemplo {index + 1}</div>
                  <div className="text-muted-foreground">{example}</div>
                </div>
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
