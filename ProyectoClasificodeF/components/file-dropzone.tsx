"use client"

import { useCallback, useState } from "react"
import { useDropzone } from "react-dropzone"
import { Upload, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useToast } from "@/hooks/use-toast"

interface FileDropzoneProps {
  onFilesChange: (files: File[]) => void
  acceptedTypes?: string[]
  maxSize?: number
  multiple?: boolean
}

export function FileDropzone({
  onFilesChange,
  acceptedTypes = [".pdf", ".jpg", ".jpeg", ".png", ".tiff"],
  maxSize = 20 * 1024 * 1024, // 20MB
  multiple = true,
}: FileDropzoneProps) {
  const { toast } = useToast()
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([])

  const onDrop = useCallback(
    (acceptedFiles: File[], rejectedFiles: any[]) => {
      // Handle rejected files
      if (rejectedFiles.length > 0) {
        rejectedFiles.forEach(({ file, errors }) => {
          errors.forEach((error: any) => {
            let message = "Error al subir archivo"
            if (error.code === "file-too-large") {
              message = `${file.name} es muy grande (máximo ${maxSize / 1024 / 1024}MB)`
            } else if (error.code === "file-invalid-type") {
              message = `${file.name} no es un tipo de archivo válido`
            }

            toast({
              variant: "destructive",
              title: "Error de archivo",
              description: message,
            })
          })
        })
      }

      // Handle accepted files
      if (acceptedFiles.length > 0) {
        const newFiles = multiple ? [...uploadedFiles, ...acceptedFiles] : acceptedFiles
        setUploadedFiles(newFiles)
        onFilesChange(newFiles)

        toast({
          title: "Archivos subidos",
          description: `${acceptedFiles.length} archivo(s) subido(s) exitosamente`,
        })
      }
    },
    [uploadedFiles, multiple, maxSize, onFilesChange, toast],
  )

  const removeFile = (index: number) => {
    const newFiles = uploadedFiles.filter((_, i) => i !== index)
    setUploadedFiles(newFiles)
    onFilesChange(newFiles)
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: acceptedTypes.reduce(
      (acc, type) => {
        const mimeType = getMimeType(type)
        if (mimeType) acc[mimeType] = [type]
        return acc
      },
      {} as Record<string, string[]>,
    ),
    maxSize,
    multiple,
  })

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-colors
          ${
            isDragActive
              ? "border-primary bg-primary/5"
              : "border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/50"
          }
        `}
      >
        <input {...getInputProps()} />
        <div className="space-y-4">
          <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mx-auto">
            <Upload className="h-6 w-6 text-primary" />
          </div>

          {isDragActive ? (
            <div>
              <p className="text-lg font-medium">Suelta los archivos aquí</p>
              <p className="text-sm text-muted-foreground">Los archivos se subirán automáticamente</p>
            </div>
          ) : (
            <div>
              <p className="text-lg font-medium">Arrastra archivos aquí o haz clic para seleccionar</p>
              <p className="text-sm text-muted-foreground">
                Soporta: {acceptedTypes.join(", ")} • Máximo {maxSize / 1024 / 1024}MB por archivo
              </p>
            </div>
          )}
        </div>
      </div>

      {uploadedFiles.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium">Archivos seleccionados:</p>
          {uploadedFiles.map((file, index) => (
            <div key={index} className="flex items-center gap-3 p-3 bg-muted/50 rounded-lg">
              <Upload className="h-4 w-4 text-muted-foreground" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{file.name}</p>
                <p className="text-xs text-muted-foreground">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
              </div>
              <Button type="button" variant="ghost" size="sm" onClick={() => removeFile(index)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function getMimeType(extension: string): string | null {
  const mimeTypes: Record<string, string> = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".tiff": "image/tiff",
  }
  return mimeTypes[extension.toLowerCase()] || null
}
