"use client"

import { useEffect, useMemo, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { useToast } from "@/hooks/use-toast"
import { apiClient } from "@/lib/apiClient"

interface MetricEntry {
  latest_value: number
  latest_context?: Record<string, any>
  latest_timestamp?: string
  count: number
}

interface MassiveTestSummary {
  total_products: number
  success_count: number
  errors: number
  avg_confidence: number
  min_confidence: number
  max_confidence: number
  suspicious_ratio: number
  review_ratio: number
  avg_response_time: number
  top_hs_codes: Array<{ hs: string; count: number }>
}

const RANGE_TO_HOURS: Record<string, number> = {
  "24h": 24,
  "7d": 24 * 7,
  "30d": 24 * 30,
  "90d": 24 * 90,
}

type Tone = "ok" | "warn" | "danger"

function formatPercent(value: number | undefined, digits = 1): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "0%"
  return `${(value * 100).toFixed(digits)}%`
}

function formatSeconds(value: number | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "0.00 s"
  return `${value.toFixed(2)} s`
}

function resolveTone(value: number, { ok, warn }: { ok: number; warn: number }, invert = false): Tone {
  const normalized = Number.isFinite(value) ? value : 0
  if (!invert) {
    if (normalized >= ok) return "ok"
    if (normalized >= warn) return "warn"
    return "danger"
  }
  if (normalized <= ok) return "ok"
  if (normalized <= warn) return "warn"
  return "danger"
}

interface MetricCardProps {
  title: string
  value: string
  description: string
  tone: Tone
}

const MetricCard = ({ title, value, description, tone }: MetricCardProps) => {
  const variantClasses: Record<Tone, string> = {
    ok: "text-emerald-600 dark:text-emerald-400",
    warn: "text-amber-600 dark:text-amber-400",
    danger: "text-red-600 dark:text-red-400",
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-semibold text-muted-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className={`text-2xl font-bold ${variantClasses[tone]}`}>{value}</div>
        <p className="text-xs text-muted-foreground mt-1">{description}</p>
      </CardContent>
    </Card>
  )
}

const TONE_BADGE_VARIANT: Record<Tone, "default" | "secondary" | "destructive" | "outline"> = {
  ok: "secondary",
  warn: "default",
  danger: "destructive",
}

export default function KPIsPage() {
  const { toast } = useToast()
  const [timeRange, setTimeRange] = useState<string>("24h")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [kpis, setKpis] = useState<Record<string, MetricEntry>>({})
  const [massiveSummary, setMassiveSummary] = useState<MassiveTestSummary | null>(null)
  const [generatedAt, setGeneratedAt] = useState<string | null>(null)

  useEffect(() => {
    const fetchMetrics = async () => {
      setLoading(true)
      setError(null)
      try {
        const hours = RANGE_TO_HOURS[timeRange] ?? 24
        const response = await apiClient.get("/metrics/kpis", { params: { hours } })
        const data = response.data ?? {}
        setKpis(data.kpis ?? {})

        const summary = data.massive_test_summary
        if (summary?.summary) {
          setMassiveSummary(summary.summary as MassiveTestSummary)
          setGeneratedAt(summary.generated_at ?? null)
        } else {
          setMassiveSummary(null)
          setGeneratedAt(null)
        }
      } catch (err: any) {
        const message = err?.message || err?.data?.error || "No se pudieron obtener las métricas"
        setError(message)
        toast({ variant: "destructive", title: "Error cargando métricas", description: message })
      } finally {
        setLoading(false)
      }
    }

    fetchMetrics()
  }, [timeRange, toast])

  const avgConfidence = useMemo(() => {
    if (massiveSummary) return massiveSummary.avg_confidence
    return Number(kpis.classification_confidence?.latest_value ?? 0)
  }, [kpis, massiveSummary])

  const avgResponse = useMemo(() => {
    if (massiveSummary) return massiveSummary.avg_response_time
    return Number(kpis.response_time?.latest_value ?? 0)
  }, [kpis, massiveSummary])

  const reviewRatio = useMemo(() => {
    if (massiveSummary) return massiveSummary.review_ratio
    return Number(kpis.feedback_ratio?.latest_value ?? 0)
  }, [kpis, massiveSummary])

  const suspiciousRatio = useMemo(() => {
    if (massiveSummary) return massiveSummary.suspicious_ratio
    return Number(kpis.suspicious_ratio?.latest_value ?? 0)
  }, [kpis, massiveSummary])

  const accuracyEstimate = useMemo(() => {
    const direct = kpis.accuracy_test_set?.latest_value
    if (typeof direct === "number") return direct
    if (massiveSummary) {
      const { total_products, errors } = massiveSummary
      if (total_products > 0) {
        return Math.max(0, (total_products - errors) / total_products)
      }
    }
    return Math.max(0, Math.min(1, avgConfidence * (1 - reviewRatio)))
  }, [avgConfidence, reviewRatio, kpis, massiveSummary])

  const totalProcessed = massiveSummary?.total_products ?? kpis.classification_event?.count ?? 0

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">KPIs y métricas</h1>
          <p className="text-muted-foreground">Visión operativa del clasificador y del test masivo de 50 productos</p>
        </div>
        <Select value={timeRange} onValueChange={setTimeRange}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Seleccionar período" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="24h">Últimas 24 horas</SelectItem>
            <SelectItem value="7d">Últimos 7 días</SelectItem>
            <SelectItem value="30d">Últimos 30 días</SelectItem>
            <SelectItem value="90d">Últimos 90 días</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {error && (
        <Card>
          <CardHeader>
            <CardTitle>Error al cargar métricas</CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          title="Precisión estimada"
          value={formatPercent(accuracyEstimate)}
          description="Estimación basada en confianza y feedback registrado"
          tone={resolveTone(accuracyEstimate, { ok: 0.9, warn: 0.75 })}
        />
        <MetricCard
          title="Confianza promedio"
          value={formatPercent(avgConfidence)}
          description="Promedio ponderado de confianza en el período seleccionado"
          tone={resolveTone(avgConfidence, { ok: 0.78, warn: 0.65 })}
        />
        <MetricCard
          title="Casos sospechosos"
          value={formatPercent(suspiciousRatio)}
          description="Proporción de clasificaciones marcadas como código sospechoso"
          tone={resolveTone(suspiciousRatio, { ok: 0.15, warn: 0.3 }, true)}
        />
        <MetricCard
          title="Tiempo de respuesta"
          value={formatSeconds(avgResponse)}
          description="Promedio de generación de respuesta por caso"
          tone={resolveTone(avgResponse, { ok: 2.5, warn: 4.0 }, true)}
        />
      </div>

      {massiveSummary && (
        <Card>
          <CardHeader>
            <CardTitle>Test masivo 50 productos</CardTitle>
            <CardDescription>
              Resumen generado automáticamente{generatedAt ? ` el ${new Date(generatedAt).toLocaleString("es-ES")}` : ""}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <Badge variant="outline">Total: {massiveSummary.total_products}</Badge>
              <Badge variant="outline">Éxitos: {massiveSummary.success_count}</Badge>
              <Badge variant="outline">Errores: {massiveSummary.errors}</Badge>
              <Badge variant={TONE_BADGE_VARIANT[resolveTone(massiveSummary.review_ratio, { ok: 0.4, warn: 0.5 }, true)]}>
                Revisión: {formatPercent(massiveSummary.review_ratio)}
              </Badge>
              <Badge variant={TONE_BADGE_VARIANT[resolveTone(massiveSummary.suspicious_ratio, { ok: 0.2, warn: 0.4 }, true)]}>
                Sospechosos: {formatPercent(massiveSummary.suspicious_ratio)}
              </Badge>
            </div>

            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
              <div className="rounded-lg border bg-card p-4">
                <p className="text-xs text-muted-foreground">Confianza promedio</p>
                <p className="text-lg font-semibold">{formatPercent(massiveSummary.avg_confidence)}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Rango {formatPercent(massiveSummary.min_confidence)} - {formatPercent(massiveSummary.max_confidence)}
                </p>
              </div>
              <div className="rounded-lg border bg-card p-4">
                <p className="text-xs text-muted-foreground">Tiempo de respuesta</p>
                <p className="text-lg font-semibold">{formatSeconds(massiveSummary.avg_response_time)}</p>
              </div>
              <div className="rounded-lg border bg-card p-4">
                <p className="text-xs text-muted-foreground">Cobertura efectiva</p>
                <p className="text-lg font-semibold">
                  {formatPercent(massiveSummary.success_count / massiveSummary.total_products || 0)}
                </p>
              </div>
            </div>

            <div>
              <h3 className="text-sm font-semibold mb-2">Top códigos HS detectados</h3>
              {massiveSummary.top_hs_codes.length === 0 ? (
                <p className="text-sm text-muted-foreground">No hay registros disponibles.</p>
              ) : (
                <ul className="space-y-2">
                  {massiveSummary.top_hs_codes.map((item) => (
                    <li key={item.hs} className="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
                      <span className="font-mono">{item.hs}</span>
                      <span className="text-muted-foreground">{item.count} casos</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <p className="text-xs text-muted-foreground">
              Los resultados del test masivo se usan para ajustar dinámicamente los pesos del motor (sin migraciones). Si el
              ratio de sospechosos supera 60 % o la confianza promedio cae por debajo de 0.6, los pesos de embeddings se
              penalizan y se elevan los umbrales de fallback. Para ajustes estructurales más fuertes se recomienda programar
              una iteración adicional con validación humana.
            </p>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Actividad reciente</CardTitle>
          <CardDescription>
            Métricas individuales registradas en el periodo seleccionado (sin impacto en la respuesta del endpoint)
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-lg border bg-card p-4">
            <p className="text-xs text-muted-foreground">Eventos registrados</p>
            <p className="text-lg font-semibold">{totalProcessed}</p>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <p className="text-xs text-muted-foreground">KPIs disponibles</p>
            <p className="text-lg font-semibold">{Object.keys(kpis).length}</p>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <p className="text-xs text-muted-foreground">Última muestra</p>
            <p className="text-sm text-muted-foreground">
              {kpis.classification_event?.latest_timestamp
                ? new Date(kpis.classification_event.latest_timestamp).toLocaleString("es-ES")
                : "Sin registros"}
            </p>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <p className="text-xs text-muted-foreground">Feedback recibido</p>
            <p className="text-lg font-semibold">{kpis.user_feedback?.count ?? 0}</p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
