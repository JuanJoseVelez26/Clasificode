"use client"

import { useState, useEffect } from "react"
import { useTranslation } from "react-i18next"
import { Shield, AlertTriangle, CheckCircle, X, Clock } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useToast } from "@/hooks/use-toast"
import { useAuthStore } from "@/lib/store"
import { ConfidenceBadge } from "@/components/confidence-badge"
import { AuditEditor } from "@/components/audit-editor"

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

const mockAuditCases: AuditCase[] = [
  {
    caseId: "case_003",
    originalHS: "8518.30.00",
    alternatives: [
      { hs: "8518.30.00", confidence: 0.55 },
      { hs: "8518.21.00", confidence: 0.42 },
      { hs: "8518.29.00", confidence: 0.38 },
    ],
    explanation: "Clasificado como auriculares por características de audio inalámbrico",
    inputText: "Auriculares inalámbricos Sony WH-1000XM5 con cancelación activa de ruido...",
    inputType: "text",
    confidence: 0.55,
    status: "pending",
    createdAt: "2024-01-14T16:45:00Z",
    updatedAt: "2024-01-14T16:45:00Z",
    flagReason: "Baja confianza automática",
  },
  {
    caseId: "case_005",
    originalHS: "8471.30.00",
    alternatives: [
      { hs: "8471.30.00", confidence: 0.43 },
      { hs: "8471.41.00", confidence: 0.39 },
      { hs: "8471.49.00", confidence: 0.35 },
    ],
    explanation: "Clasificado como máquina de procesamiento digital portátil",
    inputText: "Tablet Apple iPad Pro con chip M2, pantalla Liquid Retina XDR de 12.9 pulgadas...",
    inputType: "text",
    confidence: 0.43,
    status: "pending",
    createdAt: "2024-01-13T11:10:00Z",
    updatedAt: "2024-01-13T11:10:00Z",
    flagReason: "Marcado por usuario",
  },
  {
    caseId: "case_006",
    originalHS: "9403.20.00",
    alternatives: [
      { hs: "9403.20.00", confidence: 0.58 },
      { hs: "9403.10.00", confidence: 0.41 },
      { hs: "9403.30.00", confidence: 0.33 },
    ],
    explanation: "Clasificado como mueble de metal para oficina",
    inputText: "Escritorio ejecutivo de acero inoxidable con cajones integrados...",
    inputType: "text",
    confidence: 0.58,
    status: "pending",
    createdAt: "2024-01-12T09:30:00Z",
    updatedAt: "2024-01-12T09:30:00Z",
    flagReason: "Revisión de calidad",
  },
]

export default function AuditPage() {
  const { t } = useTranslation()
  const { toast } = useToast()
  const { user } = useAuthStore()
  const [cases, setCases] = useState<AuditCase[]>([])
  const [selectedCase, setSelectedCase] = useState<AuditCase | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Simulate API call to load audit cases
    const loadAuditCases = async () => {
      await new Promise((resolve) => setTimeout(resolve, 1000))
      setCases(mockAuditCases)
      setIsLoading(false)
    }
    loadAuditCases()
  }, [])

  const handleCaseSelect = (caseItem: AuditCase) => {
    setSelectedCase(caseItem)
  }

  const handleCaseUpdate = (caseId: string, updates: Partial<AuditCase>) => {
    setCases((prev) =>
      prev.map((c) =>
        c.caseId === caseId ? { ...c, ...updates, reviewer: user?.name, updatedAt: new Date().toISOString() } : c,
      ),
    )

    if (selectedCase?.caseId === caseId) {
      setSelectedCase((prev) => (prev ? { ...prev, ...updates, reviewer: user?.name } : null))
    }

    toast({
      title: "Caso actualizado",
      description: `El caso ${caseId} ha sido actualizado exitosamente`,
    })
  }

  const getPriorityBadge = (confidence: number, flagReason?: string) => {
    if (confidence < 0.4) {
      return <Badge variant="destructive">Alta Prioridad</Badge>
    }
    if (confidence < 0.6) {
      return <Badge variant="secondary">Media Prioridad</Badge>
    }
    return <Badge variant="outline">Baja Prioridad</Badge>
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "pending":
        return <Clock className="h-4 w-4 text-yellow-500" />
      case "corrected":
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case "rejected":
        return <X className="h-4 w-4 text-red-500" />
      default:
        return <AlertTriangle className="h-4 w-4 text-gray-500" />
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="text-center space-y-4">
          <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-muted-foreground">Cargando casos de auditoría...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Shield className="h-8 w-8" />
            Auditoría de Clasificaciones
          </h1>
          <p className="text-muted-foreground">Revisa y corrige clasificaciones que requieren validación manual</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline">{cases.filter((c) => c.status === "pending").length} casos pendientes</Badge>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Cases List */}
        <div className="lg:col-span-1 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Cola de Auditoría</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 max-h-96 overflow-y-auto">
              {cases.length === 0 ? (
                <div className="text-center py-8">
                  <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-4" />
                  <p className="text-muted-foreground">No hay casos pendientes de auditoría</p>
                </div>
              ) : (
                cases.map((caseItem) => (
                  <div
                    key={caseItem.caseId}
                    className={`p-4 border rounded-2xl cursor-pointer transition-colors hover:bg-muted/50 ${
                      selectedCase?.caseId === caseItem.caseId ? "border-primary bg-primary/5" : ""
                    }`}
                    onClick={() => handleCaseSelect(caseItem)}
                  >
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-sm font-medium">{caseItem.caseId}</span>
                        {getStatusIcon(caseItem.status)}
                      </div>

                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="font-mono text-xs">
                            {caseItem.originalHS}
                          </Badge>
                          <ConfidenceBadge confidence={caseItem.confidence} />
                        </div>
                        {getPriorityBadge(caseItem.confidence, caseItem.flagReason)}
                      </div>

                      <p className="text-sm text-muted-foreground line-clamp-2">{caseItem.inputText}</p>

                      <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <span>{new Date(caseItem.createdAt).toLocaleDateString()}</span>
                        <span>{caseItem.flagReason}</span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>

        {/* Case Details */}
        <div className="lg:col-span-2">
          {selectedCase ? (
            <AuditEditor
              auditCase={selectedCase}
              onUpdate={(updates) => handleCaseUpdate(selectedCase.caseId, updates)}
            />
          ) : (
            <Card>
              <CardContent className="flex items-center justify-center h-96">
                <div className="text-center space-y-4">
                  <Shield className="h-16 w-16 text-muted-foreground mx-auto" />
                  <div>
                    <h3 className="text-lg font-medium">Selecciona un caso para auditar</h3>
                    <p className="text-muted-foreground">
                      Elige un caso de la lista para revisar y corregir la clasificación
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
