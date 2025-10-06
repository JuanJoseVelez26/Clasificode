"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Search, Download, RefreshCw, User, FileText, Shield, AlertTriangle, CheckCircle, XCircle } from "lucide-react"
import { useI18n } from "@/lib/i18n"

interface LogEntry {
  id: string
  timestamp: string
  user: string
  action: string
  resource: string
  details: string
  ip: string
  userAgent: string
  status: "success" | "error" | "warning"
  duration?: number
}

const actionIcons = {
  "Autoriza sesión": User,
  "Clasifica producto": FileText,
  "Audita caso": Shield,
  "Exporta datos": Download,
  "Modifica configuración": AlertTriangle,
  "Accede a KPIs": FileText,
  "Consulta historial": FileText,
}

const statusColors = {
  success: "bg-green-100 text-green-800 border-green-200",
  error: "bg-red-100 text-red-800 border-red-200",
  warning: "bg-yellow-100 text-yellow-800 border-yellow-200",
}

const statusIcons = {
  success: CheckCircle,
  error: XCircle,
  warning: AlertTriangle,
}

export default function LogsPage() {
  const { t } = useI18n()
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [filteredLogs, setFilteredLogs] = useState<LogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [actionFilter, setActionFilter] = useState<string>("all")
  const [dateFilter, setDateFilter] = useState<string>("all")

  useEffect(() => {
    const fetchLogs = async () => {
      setLoading(true)
      try {
        // Mock log data
        const mockLogs: LogEntry[] = [
          {
            id: "1",
            timestamp: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
            user: "admin@eafit.edu.co",
            action: "Autoriza sesión",
            resource: "/app/form",
            details: "Inicio de sesión exitoso desde navegador Chrome",
            ip: "192.168.1.100",
            userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            status: "success",
            duration: 245,
          },
          {
            id: "2",
            timestamp: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
            user: "auditor@eafit.edu.co",
            action: "Audita caso",
            resource: "/app/audit/case-123",
            details: "Caso aprobado: HS 8471.30.00 con confianza 0.92",
            ip: "192.168.1.101",
            userAgent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            status: "success",
            duration: 1200,
          },
          {
            id: "3",
            timestamp: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
            user: "user@eafit.edu.co",
            action: "Clasifica producto",
            resource: "/app/form",
            details: 'Clasificación de "Laptop Dell Inspiron" - HS: 8471.30.00',
            ip: "192.168.1.102",
            userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            status: "success",
            duration: 3400,
          },
          {
            id: "4",
            timestamp: new Date(Date.now() - 45 * 60 * 1000).toISOString(),
            user: "admin@eafit.edu.co",
            action: "Exporta datos",
            resource: "/app/kpis",
            details: "Exportación de KPIs del último mes en formato CSV",
            ip: "192.168.1.100",
            userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            status: "success",
            duration: 890,
          },
          {
            id: "5",
            timestamp: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
            user: "user@eafit.edu.co",
            action: "Clasifica producto",
            resource: "/app/form",
            details: "Error en clasificación: Timeout en procesamiento OCR",
            ip: "192.168.1.103",
            userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X)",
            status: "error",
            duration: 30000,
          },
          {
            id: "6",
            timestamp: new Date(Date.now() - 90 * 60 * 1000).toISOString(),
            user: "auditor@eafit.edu.co",
            action: "Audita caso",
            resource: "/app/audit/case-122",
            details: "Caso corregido: HS cambiado de 3926.90.99 a 3926.30.00",
            ip: "192.168.1.101",
            userAgent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            status: "warning",
            duration: 2100,
          },
        ]

        setLogs(mockLogs)
        setFilteredLogs(mockLogs)
      } catch (error) {
        console.error("Error fetching logs:", error)
      } finally {
        setLoading(false)
      }
    }

    fetchLogs()
  }, [])

  useEffect(() => {
    let filtered = logs

    // Filter by search term
    if (searchTerm) {
      filtered = filtered.filter(
        (log) =>
          log.user.toLowerCase().includes(searchTerm.toLowerCase()) ||
          log.action.toLowerCase().includes(searchTerm.toLowerCase()) ||
          log.details.toLowerCase().includes(searchTerm.toLowerCase()) ||
          log.ip.includes(searchTerm),
      )
    }

    // Filter by status
    if (statusFilter !== "all") {
      filtered = filtered.filter((log) => log.status === statusFilter)
    }

    // Filter by action
    if (actionFilter !== "all") {
      filtered = filtered.filter((log) => log.action === actionFilter)
    }

    // Filter by date
    if (dateFilter !== "all") {
      const now = new Date()
      const filterDate = new Date()

      switch (dateFilter) {
        case "1h":
          filterDate.setHours(now.getHours() - 1)
          break
        case "24h":
          filterDate.setDate(now.getDate() - 1)
          break
        case "7d":
          filterDate.setDate(now.getDate() - 7)
          break
        case "30d":
          filterDate.setDate(now.getDate() - 30)
          break
      }

      filtered = filtered.filter((log) => new Date(log.timestamp) >= filterDate)
    }

    setFilteredLogs(filtered)
  }, [logs, searchTerm, statusFilter, actionFilter, dateFilter])

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleString("es-ES", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    })
  }

  const formatDuration = (duration?: number) => {
    if (!duration) return "-"
    if (duration < 1000) return `${duration}ms`
    return `${(duration / 1000).toFixed(1)}s`
  }

  const getRelativeTime = (timestamp: string) => {
    const now = new Date()
    const date = new Date(timestamp)
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)

    if (diffMins < 1) return "Hace menos de 1 min"
    if (diffMins < 60) return `Hace ${diffMins} min`
    if (diffMins < 1440) return `Hace ${Math.floor(diffMins / 60)} h`
    return `Hace ${Math.floor(diffMins / 1440)} días`
  }

  const uniqueActions = [...new Set(logs.map((log) => log.action))]

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Logs del Sistema</h1>
          <p className="text-muted-foreground">Registro detallado de todas las actividades del sistema</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            Actualizar
          </Button>
          <Button variant="outline" size="sm">
            <Download className="h-4 w-4 mr-2" />
            Exportar
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Filtros</CardTitle>
          <CardDescription>Filtra los logs por diferentes criterios</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
            <div className="space-y-2">
              <label className="text-sm font-medium">Buscar</label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Usuario, acción, IP..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Estado</label>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="Todos los estados" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos los estados</SelectItem>
                  <SelectItem value="success">Exitoso</SelectItem>
                  <SelectItem value="error">Error</SelectItem>
                  <SelectItem value="warning">Advertencia</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Acción</label>
              <Select value={actionFilter} onValueChange={setActionFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="Todas las acciones" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todas las acciones</SelectItem>
                  {uniqueActions.map((action) => (
                    <SelectItem key={action} value={action}>
                      {action}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Período</label>
              <Select value={dateFilter} onValueChange={setDateFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="Todo el tiempo" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todo el tiempo</SelectItem>
                  <SelectItem value="1h">Última hora</SelectItem>
                  <SelectItem value="24h">Últimas 24 horas</SelectItem>
                  <SelectItem value="7d">Últimos 7 días</SelectItem>
                  <SelectItem value="30d">Últimos 30 días</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Resultados</label>
              <div className="text-sm text-muted-foreground pt-2">
                {filteredLogs.length} de {logs.length} registros
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Logs Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Registro de Actividades</CardTitle>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[600px]">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>Usuario</TableHead>
                  <TableHead>Acción</TableHead>
                  <TableHead>Detalles</TableHead>
                  <TableHead>IP</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Duración</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredLogs.map((log) => {
                  const ActionIcon = actionIcons[log.action as keyof typeof actionIcons] || FileText
                  const StatusIcon = statusIcons[log.status]

                  return (
                    <TableRow key={log.id}>
                      <TableCell>
                        <div className="space-y-1">
                          <div className="text-sm font-medium">{formatTimestamp(log.timestamp)}</div>
                          <div className="text-xs text-muted-foreground">{getRelativeTime(log.timestamp)}</div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <div className="w-6 h-6 bg-primary/10 rounded-full flex items-center justify-center">
                            <span className="text-xs font-medium text-primary">{log.user.charAt(0).toUpperCase()}</span>
                          </div>
                          <span className="text-sm">{log.user}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <ActionIcon className="h-4 w-4 text-muted-foreground" />
                          <span className="text-sm font-medium">{log.action}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="max-w-md">
                          <p className="text-sm text-muted-foreground truncate" title={log.details}>
                            {log.details}
                          </p>
                          <p className="text-xs text-muted-foreground mt-1">{log.resource}</p>
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className="text-sm font-mono">{log.ip}</span>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className={`${statusColors[log.status]} flex items-center gap-1`}>
                          <StatusIcon className="h-3 w-3" />
                          {log.status === "success" ? "Exitoso" : log.status === "error" ? "Error" : "Advertencia"}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <span className="text-sm font-mono">{formatDuration(log.duration)}</span>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  )
}
