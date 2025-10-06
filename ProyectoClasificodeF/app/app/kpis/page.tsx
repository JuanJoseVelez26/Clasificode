"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Download, TrendingUp, TrendingDown, FileText, CheckCircle, AlertTriangle } from "lucide-react"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  Area,
  AreaChart,
} from "recharts"
import { useI18n } from "@/lib/i18n"

interface KPIData {
  totalClassifications: number
  accuracyRate: number
  avgConfidence: number
  pendingAudits: number
  dailyVolume: Array<{ date: string; count: number }>
  confidenceDistribution: Array<{ range: string; count: number; color: string }>
  topCategories: Array<{ category: string; count: number; percentage: number }>
  auditStats: Array<{ status: string; count: number; color: string }>
  monthlyTrends: Array<{ month: string; classifications: number; accuracy: number }>
}

export default function KPIsPage() {
  const { t } = useI18n()
  const [kpiData, setKpiData] = useState<KPIData | null>(null)
  const [timeRange, setTimeRange] = useState("30d")
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchKPIs = async () => {
      setLoading(true)
      try {
        // Mock KPI data
        const data: KPIData = {
          totalClassifications: 2847,
          accuracyRate: 94.2,
          avgConfidence: 0.87,
          pendingAudits: 23,
          dailyVolume: Array.from({ length: 30 }, (_, i) => ({
            date: new Date(Date.now() - (29 - i) * 24 * 60 * 60 * 1000).toISOString().split("T")[0],
            count: Math.floor(Math.random() * 100) + 50,
          })),
          confidenceDistribution: [
            { range: "Alta (≥0.85)", count: 1892, color: "#22c55e" },
            { range: "Media (0.6-0.85)", count: 743, color: "#f59e0b" },
            { range: "Baja (<0.6)", count: 212, color: "#ef4444" },
          ],
          topCategories: [
            { category: "84 - Máquinas y aparatos", count: 456, percentage: 16.0 },
            { category: "85 - Máquinas eléctricas", count: 398, percentage: 14.0 },
            { category: "39 - Plásticos", count: 342, percentage: 12.0 },
            { category: "73 - Manufacturas de hierro", count: 285, percentage: 10.0 },
            { category: "90 - Instrumentos ópticos", count: 227, percentage: 8.0 },
          ],
          auditStats: [
            { status: "Aprobado", count: 156, color: "#22c55e" },
            { status: "Corregido", count: 89, color: "#f59e0b" },
            { status: "Rechazado", count: 34, color: "#ef4444" },
            { status: "Pendiente", count: 23, color: "#6b7280" },
          ],
          monthlyTrends: [
            { month: "Ene", classifications: 2100, accuracy: 92.1 },
            { month: "Feb", classifications: 2350, accuracy: 93.4 },
            { month: "Mar", classifications: 2680, accuracy: 94.2 },
            { month: "Abr", classifications: 2847, accuracy: 94.2 },
          ],
        }
        setKpiData(data)
      } catch (error) {
        console.error("Error fetching KPIs:", error)
      } finally {
        setLoading(false)
      }
    }

    fetchKPIs()
  }, [timeRange])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  if (!kpiData) return null

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">KPIs y Métricas</h1>
          <p className="text-muted-foreground">Panel de control con métricas clave del sistema de clasificación</p>
        </div>
        <div className="flex items-center gap-4">
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Seleccionar período" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7d">Últimos 7 días</SelectItem>
              <SelectItem value="30d">Últimos 30 días</SelectItem>
              <SelectItem value="90d">Últimos 90 días</SelectItem>
              <SelectItem value="1y">Último año</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm">
            <Download className="h-4 w-4 mr-2" />
            Exportar
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Clasificaciones</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{kpiData.totalClassifications.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              <TrendingUp className="h-3 w-3 inline mr-1" />
              +12.5% vs período anterior
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Precisión Promedio</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{kpiData.accuracyRate}%</div>
            <p className="text-xs text-muted-foreground">
              <TrendingUp className="h-3 w-3 inline mr-1" />
              +2.1% vs período anterior
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Confianza Promedio</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(kpiData.avgConfidence * 100).toFixed(1)}%</div>
            <p className="text-xs text-muted-foreground">
              <TrendingUp className="h-3 w-3 inline mr-1" />
              +1.8% vs período anterior
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Auditorías Pendientes</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{kpiData.pendingAudits}</div>
            <p className="text-xs text-muted-foreground">
              <TrendingDown className="h-3 w-3 inline mr-1" />
              -15.2% vs período anterior
            </p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="volume" className="space-y-4">
        <TabsList>
          <TabsTrigger value="volume">Volumen</TabsTrigger>
          <TabsTrigger value="confidence">Confianza</TabsTrigger>
          <TabsTrigger value="categories">Categorías</TabsTrigger>
          <TabsTrigger value="audit">Auditoría</TabsTrigger>
        </TabsList>

        <TabsContent value="volume" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Volumen Diario de Clasificaciones</CardTitle>
                <CardDescription>Número de clasificaciones procesadas por día</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={kpiData.dailyVolume}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="date"
                      tickFormatter={(value) =>
                        new Date(value).toLocaleDateString("es-ES", { month: "short", day: "numeric" })
                      }
                    />
                    <YAxis />
                    <Tooltip
                      labelFormatter={(value) => new Date(value).toLocaleDateString("es-ES")}
                      formatter={(value) => [value, "Clasificaciones"]}
                    />
                    <Area type="monotone" dataKey="count" stroke="#004B85" fill="#004B85" fillOpacity={0.1} />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Tendencias Mensuales</CardTitle>
                <CardDescription>Evolución de clasificaciones y precisión</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={kpiData.monthlyTrends}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" />
                    <YAxis yAxisId="left" />
                    <YAxis yAxisId="right" orientation="right" />
                    <Tooltip />
                    <Bar yAxisId="left" dataKey="classifications" fill="#004B85" />
                    <Line yAxisId="right" type="monotone" dataKey="accuracy" stroke="#22c55e" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="confidence" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Distribución de Confianza</CardTitle>
              <CardDescription>Clasificación de casos por nivel de confianza</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={kpiData.confidenceDistribution}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ range, percentage }) => `${range}: ${percentage}%`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="count"
                    >
                      {kpiData.confidenceDistribution.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
                <div className="space-y-4">
                  {kpiData.confidenceDistribution.map((item, index) => (
                    <div key={index} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                        <span className="text-sm font-medium">{item.range}</span>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-bold">{item.count}</div>
                        <div className="text-xs text-muted-foreground">
                          {((item.count / kpiData.totalClassifications) * 100).toFixed(1)}%
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="categories" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Top Categorías HS</CardTitle>
              <CardDescription>Categorías más frecuentemente clasificadas</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={kpiData.topCategories} layout="horizontal">
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" />
                  <YAxis dataKey="category" type="category" width={150} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#004B85" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="audit" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Estado de Auditorías</CardTitle>
                <CardDescription>Distribución de casos auditados</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={kpiData.auditStats}
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="count"
                      label={({ status, count }) => `${status}: ${count}`}
                    >
                      {kpiData.auditStats.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Métricas de Auditoría</CardTitle>
                <CardDescription>Estadísticas detalladas del proceso de auditoría</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {kpiData.auditStats.map((stat, index) => (
                  <div key={index} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" style={{ borderColor: stat.color, color: stat.color }}>
                        {stat.status}
                      </Badge>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-bold">{stat.count}</div>
                      <div className="text-xs text-muted-foreground">
                        {((stat.count / kpiData.auditStats.reduce((sum, s) => sum + s.count, 0)) * 100).toFixed(1)}%
                      </div>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
