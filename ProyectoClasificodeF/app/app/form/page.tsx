"use client"

import "@/lib/i18n"
import { useState } from "react"
import { useRouter } from "next/navigation"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useTranslation } from "react-i18next"
import { Icons } from "@/lib/icons"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { useToast } from "@/hooks/use-toast"
import { useClassificationStore } from "@/lib/store"
import { api } from "@/lib/api"
import { FileDropzone } from "@/components/file-dropzone"
import { OcrPreview } from "@/components/ocr-preview"
import { LangBadge } from "@/components/lang-badge"

const formSchema = z
  .object({
    inputType: z.enum(["text", "file"]),
    text: z.string().optional(),
    files: z.array(z.any()).optional(),
  })
  .refine(
    (data) => {
      if (data.inputType === "text") {
        return data.text && data.text.length >= 15
      }
      if (data.inputType === "file") {
        return data.files && data.files.length > 0
      }
      return false
    },
    {
      message: "Debes proporcionar texto (mín. 15 caracteres) o subir al menos un archivo",
    },
  )

type FormData = z.infer<typeof formSchema>

export default function FormPage() {
  const { t } = useTranslation()
  const router = useRouter()
  const { toast } = useToast()

  const { inputType, rawText, files, ocrText, lang, setInputType, setRawText, setFiles, setOcrText, setLang, reset } =
    useClassificationStore()

  const [isProcessing, setIsProcessing] = useState(false)
  const [ocrProgress, setOcrProgress] = useState(0)
  const [ocrStep, setOcrStep] = useState<"idle" | "preprocessing" | "ocr" | "delivery" | "complete">("idle")
  const [detectedLang, setDetectedLang] = useState<"es" | "en" | null>(null)
  const [showTranslation, setShowTranslation] = useState(false)

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

      const detected = spanishCount > englishCount ? "es" : "en"
      setDetectedLang(detected)
      setLang(detected)
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
      setDetectedLang(response.lang)
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
        textToProcess = await processOCR(data.files)
      }

      if (!textToProcess) {
        throw new Error("No se pudo obtener texto para procesar")
      }

      // Navigate to results page
      router.push("/app/result")

      toast({
        title: "Procesamiento iniciado",
        description: "Redirigiendo a los resultados...",
      })
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: error instanceof Error ? error.message : "Error al procesar la solicitud",
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
                {detectedLang && <LangBadge lang={detectedLang} />}
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
                  {detectedLang && detectedLang !== "es" && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowTranslation(!showTranslation)}
                    >
                      <Icons.Languages />
                      <span className="ml-1">Traducir a español</span>
                    </Button>
                  )}
                </div>
              </div>

              {showTranslation && (
                <div className="p-4 bg-muted/50 rounded-lg">
                  <Label className="text-sm font-medium">Traducción (simulada):</Label>
                  <p className="text-sm mt-1">
                    {watchedText ? `[Traducción simulada de: "${watchedText.substring(0, 50)}..."]` : ""}
                  </p>
                </div>
              )}

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
                    <OcrPreview step={ocrStep} progress={ocrProgress} extractedText={ocrText} detectedLang={lang} />
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
            disabled={isProcessing || (watchedInputType === "text" && (watchedText?.length || 0) < 15)}
            className="min-w-48"
          >
            {isProcessing && <Icons.Loader />}
            <span className="ml-2">{t("form.process")}</span>
          </Button>
        </div>
      </form>
    </div>
  )
}
