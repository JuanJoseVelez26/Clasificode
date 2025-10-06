"use client"

import { useState } from "react"
import { Save, AlertTriangle, CheckCircle, X, User, Clock } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useToast } from "@/hooks/use-toast"
import { ConfidenceBadge } from "@/components/confidence-badge"
import { TopKChips } from "@/components/top-k-chips"

interface AuditCase {
  caseId: string
  originalHS: string
  alternatives: Array<{ hs: string; confidence: number }>
  explanation: string
  inputText: string
  inputType: "text" | "file"
  confidence: number
  note?: string
  status: "pending" | "corrected" | "rejected"
  correctedHS?: string
  reviewer?: string
  updatedAt: string
  createdAt: string
  flagReason?: string
}

interface AuditEditorProps {
  auditCase: AuditCase
  onUpdate: (updates: Partial<AuditCase>) => void
}

export function AuditEditor({ auditCase, onUpdate }: AuditEditorProps) {
  const { toast } = useToast()
  const [correctedHS, setCorrectedHS] = useState(auditCase.correctedHS || "")
  const [reviewComment, setReviewComment] = useState(auditCase.note || "")
  const [selectedAlternative, setSelectedAlternative] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  const handleSaveCorrection = async (status: "corrected" | "rejected") => {
    if (status === "corrected" && !correctedHS.trim()) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Debes proporcionar un código HS corregido",
      })
      return
    }

    setIsSaving(true)

    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1000))

      const updates: Partial<AuditCase> = {
        status,
        note: reviewComment,
        ...(status === "corrected" && { correctedHS: correctedHS.trim() }),
      }

      onUpdate(updates)

      toast({
        title: status === "corrected" ? "Caso corregido" : "Caso rechazado",
        description: `El caso ${auditCase.caseId} ha sido ${status === "corrected" ? "corregido" : "rechazado"} exitosamente`,
      })
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "No se pudo guardar la corrección",
      })
    } finally {
      setIsSaving(false)
    }
  }

  const handleApprove = async () => {
    setIsSaving(true)

    try {
      await new Promise((resolve) => setTimeout(resolve, 500))

      onUpdate({
        status: "corrected",
        correctedHS: auditCase.originalHS, // Keep original as approved
        note: reviewComment || "Clasificación aprobada sin cambios",
      })

      toast({
        title: "Caso aprobado",
        description: `El caso ${auditCase.caseId} ha sido aprobado`,
      })
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "No se pudo aprobar el caso",
      })
    } finally {
      setIsSaving(false)
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "pending":
        return (
          <Badge variant="outline">
            <Clock className="h-3 w-3 mr-1" />
            Pendiente
          </Badge>
        )
      case "corrected":
        return (
          <Badge variant="default">
            <CheckCircle className="h-3 w-3 mr-1" />
            Corregido
          </Badge>
        )
      case "rejected":
        return (
          <Badge variant="destructive">
            <X className="h-3 w-3 mr-1" />
            Rechazado
          </Badge>
        )
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  return (
    <div className="space-y-6">
      {/* Case Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              Caso {auditCase.caseId}
              {getStatusBadge(auditCase.status)}
            </CardTitle>
            <div className="flex items-center gap-2">
              <ConfidenceBadge confidence={auditCase.confidence} />
              {auditCase.confidence < 0.6 && (
                <Badge variant="destructive" className="gap-1">
                  <AlertTriangle className="h-3 w-3" />
                  Requiere Revisión
                </Badge>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">Creado:</span>
              <span className="ml-2">{new Date(auditCase.createdAt).toLocaleString()}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Actualizado:</span>
              <span className="ml-2">{new Date(auditCase.updatedAt).toLocaleString()}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Tipo:</span>
              <Badge variant="outline" className="ml-2 capitalize">
                {auditCase.inputType === "text" ? "Texto" : "Archivo"}
              </Badge>
            </div>
            <div>
              <span className="text-muted-foreground">Razón:</span>
              <span className="ml-2">{auditCase.flagReason}</span>
            </div>
          </div>

          {auditCase.reviewer && (
            <div className="flex items-center gap-2 text-sm">
              <User className="h-4 w-4 text-muted-foreground" />
              <span className="text-muted-foreground">Revisado por:</span>
              <span>{auditCase.reviewer}</span>
            </div>
          )}
        </CardContent>
      </Card>

      <Tabs defaultValue="review" className="space-y-4">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="review">Revisión</TabsTrigger>
          <TabsTrigger value="details">Detalles</TabsTrigger>
        </TabsList>

        <TabsContent value="review" className="space-y-6">
          {/* Original Classification */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Clasificación Original</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-center p-6 bg-muted/50 rounded-2xl">
                <div className="text-center">
                  <div className="text-3xl font-bold font-mono text-primary mb-2">{auditCase.originalHS}</div>
                  <p className="text-muted-foreground">Código HS Propuesto</p>
                </div>
              </div>

              <div className="space-y-3">
                <h4 className="font-medium">Alternativas Disponibles</h4>
                <TopKChips
                  alternatives={auditCase.alternatives}
                  selectedAlternative={selectedAlternative}
                  onSelect={setSelectedAlternative}
                />
              </div>
            </CardContent>
          </Card>

          {/* Correction Form */}
          {auditCase.status === "pending" && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Corrección Manual</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="correctedHS">Código HS Corregido (opcional)</Label>
                  <Input
                    id="correctedHS"
                    placeholder="Ej: 8517.12.00"
                    value={correctedHS}
                    onChange={(e) => setCorrectedHS(e.target.value)}
                    className="font-mono"
                  />
                  <p className="text-xs text-muted-foreground">Deja vacío si apruebas la clasificación original</p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="comment">Comentario de Revisión</Label>
                  <Textarea
                    id="comment"
                    placeholder="Explica la razón de la corrección o aprobación..."
                    value={reviewComment}
                    onChange={(e) => setReviewComment(e.target.value)}
                    className="min-h-24"
                  />
                </div>

                <Separator />

                <div className="flex items-center gap-3">
                  <Button onClick={handleApprove} disabled={isSaving} className="bg-green-600 hover:bg-green-700">
                    <CheckCircle className="h-4 w-4 mr-2" />
                    Aprobar Original
                  </Button>

                  <Button onClick={() => handleSaveCorrection("corrected")} disabled={isSaving}>
                    <Save className="h-4 w-4 mr-2" />
                    Guardar Corrección
                  </Button>

                  <Button variant="destructive" onClick={() => handleSaveCorrection("rejected")} disabled={isSaving}>
                    <X className="h-4 w-4 mr-2" />
                    Rechazar
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Review History */}
          {auditCase.status !== "pending" && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Resultado de la Revisión</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="p-4 bg-muted/50 rounded-2xl">
                  <div className="flex items-center justify-between mb-3">
                    <span className="font-medium">Estado Final:</span>
                    {getStatusBadge(auditCase.status)}
                  </div>

                  {auditCase.correctedHS && auditCase.correctedHS !== auditCase.originalHS && (
                    <div className="space-y-2">
                      <span className="font-medium">Código Corregido:</span>
                      <div className="font-mono text-lg text-primary">{auditCase.correctedHS}</div>
                    </div>
                  )}

                  {auditCase.note && (
                    <div className="space-y-2">
                      <span className="font-medium">Comentario:</span>
                      <p className="text-sm text-muted-foreground">{auditCase.note}</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="details" className="space-y-6">
          {/* Input Text */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Texto de Entrada</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="p-4 bg-muted/50 rounded-2xl">
                <p className="text-sm leading-relaxed">{auditCase.inputText}</p>
              </div>
            </CardContent>
          </Card>

          {/* Explanation */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Explicación del Sistema</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="p-4 bg-muted/50 rounded-2xl">
                <p className="text-sm leading-relaxed">{auditCase.explanation}</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
