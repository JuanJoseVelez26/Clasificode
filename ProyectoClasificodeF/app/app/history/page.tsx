"use client"

import { useState, useEffect } from "react"
import { useTranslation } from "react-i18next"
import { Calendar, Filter, Search, Eye, Download, MoreHorizontal } from "lucide-react"
import {
  useReactTable,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  getPaginationRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
  type ColumnFiltersState,
} from "@tanstack/react-table"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { useToast } from "@/hooks/use-toast"
import { ConfidenceBadge } from "@/components/confidence-badge"

interface HistoryCase {
  id: string
  date: string
  inputType: "text" | "file"
  inputPreview: string
  hsCode: string
  confidence: number
  auditStatus: "pending" | "approved" | "corrected" | "rejected"
  auditor?: string
  correctedHS?: string
}

const mockHistoryData: HistoryCase[] = [
  {
    id: "case_001",
    date: "2024-01-15T10:30:00Z",
    inputType: "text",
    inputPreview: "Smartphone Samsung Galaxy S24 Ultra con pantalla AMOLED...",
    hsCode: "8517.12.00",
    confidence: 0.92,
    auditStatus: "approved",
    auditor: "Ana García",
  },
  {
    id: "case_002",
    date: "2024-01-15T09:15:00Z",
    inputType: "file",
    inputPreview: "documento_producto.pdf",
    hsCode: "8471.30.00",
    confidence: 0.78,
    auditStatus: "corrected",
    auditor: "Carlos López",
    correctedHS: "8471.41.00",
  },
  {
    id: "case_003",
    date: "2024-01-14T16:45:00Z",
    inputType: "text",
    inputPreview: "Auriculares inalámbricos Sony WH-1000XM5...",
    hsCode: "8518.30.00",
    confidence: 0.55,
    auditStatus: "pending",
  },
  {
    id: "case_004",
    date: "2024-01-14T14:20:00Z",
    inputType: "file",
    inputPreview: "especificaciones_laptop.pdf",
    hsCode: "8471.30.00",
    confidence: 0.89,
    auditStatus: "approved",
    auditor: "María Rodríguez",
  },
  {
    id: "case_005",
    date: "2024-01-13T11:10:00Z",
    inputType: "text",
    inputPreview: "Tablet Apple iPad Pro con chip M2...",
    hsCode: "8471.30.00",
    confidence: 0.43,
    auditStatus: "rejected",
    auditor: "Ana García",
  },
]

export default function HistoryPage() {
  const { t } = useTranslation()
  const { toast } = useToast()
  const [data, setData] = useState<HistoryCase[]>([])
  const [sorting, setSorting] = useState<SortingState>([{ id: "date", desc: true }])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [globalFilter, setGlobalFilter] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [typeFilter, setTypeFilter] = useState<string>("all")

  useEffect(() => {
    // Simulate API call
    const loadHistory = async () => {
      await new Promise((resolve) => setTimeout(resolve, 1000))
      setData(mockHistoryData)
    }
    loadHistory()
  }, [])

  const getStatusBadge = (status: string, correctedHS?: string) => {
    switch (status) {
      case "approved":
        return <Badge variant="default">Aprobado</Badge>
      case "corrected":
        return <Badge variant="secondary">Corregido</Badge>
      case "rejected":
        return <Badge variant="destructive">Rechazado</Badge>
      case "pending":
        return <Badge variant="outline">Pendiente</Badge>
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  const columns: ColumnDef<HistoryCase>[] = [
    {
      accessorKey: "date",
      header: "Fecha",
      cell: ({ row }) => {
        const date = new Date(row.getValue("date"))
        return (
          <div className="space-y-1">
            <div className="font-medium">{date.toLocaleDateString()}</div>
            <div className="text-xs text-muted-foreground">{date.toLocaleTimeString()}</div>
          </div>
        )
      },
    },
    {
      accessorKey: "inputType",
      header: "Tipo",
      cell: ({ row }) => {
        const type = row.getValue("inputType") as string
        return (
          <Badge variant="outline" className="capitalize">
            {type === "text" ? "Texto" : "Archivo"}
          </Badge>
        )
      },
    },
    {
      accessorKey: "inputPreview",
      header: "Entrada",
      cell: ({ row }) => {
        const preview = row.getValue("inputPreview") as string
        return (
          <div className="max-w-xs">
            <p className="truncate text-sm">{preview}</p>
          </div>
        )
      },
    },
    {
      accessorKey: "hsCode",
      header: "Código HS",
      cell: ({ row }) => {
        const hsCode = row.getValue("hsCode") as string
        const correctedHS = row.original.correctedHS
        return (
          <div className="space-y-1">
            <div className="font-mono font-medium">{correctedHS || hsCode}</div>
            {correctedHS && <div className="text-xs text-muted-foreground line-through">{hsCode}</div>}
          </div>
        )
      },
    },
    {
      accessorKey: "confidence",
      header: "Confianza",
      cell: ({ row }) => {
        const confidence = row.getValue("confidence") as number
        return <ConfidenceBadge confidence={confidence} />
      },
    },
    {
      accessorKey: "auditStatus",
      header: "Estado Auditoría",
      cell: ({ row }) => {
        const status = row.getValue("auditStatus") as string
        const correctedHS = row.original.correctedHS
        return getStatusBadge(status, correctedHS)
      },
    },
    {
      accessorKey: "auditor",
      header: "Auditor",
      cell: ({ row }) => {
        const auditor = row.getValue("auditor") as string
        return auditor ? (
          <div className="text-sm">{auditor}</div>
        ) : (
          <div className="text-xs text-muted-foreground">-</div>
        )
      },
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) => {
        const caseItem = row.original
        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => handleViewCase(caseItem.id)}>
                <Eye className="h-4 w-4 mr-2" />
                Ver Detalles
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleExportCase(caseItem.id)}>
                <Download className="h-4 w-4 mr-2" />
                Exportar
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )
      },
    },
  ]

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: setGlobalFilter,
    state: {
      sorting,
      columnFilters,
      globalFilter,
    },
  })

  // Apply filters
  useEffect(() => {
    const filters: ColumnFiltersState = []

    if (statusFilter !== "all") {
      filters.push({ id: "auditStatus", value: statusFilter })
    }

    if (typeFilter !== "all") {
      filters.push({ id: "inputType", value: typeFilter })
    }

    setColumnFilters(filters)
  }, [statusFilter, typeFilter])

  const handleViewCase = (caseId: string) => {
    toast({
      title: "Ver caso",
      description: `Abriendo detalles del caso ${caseId}`,
    })
  }

  const handleExportCase = (caseId: string) => {
    toast({
      title: "Exportar caso",
      description: `Exportando caso ${caseId}`,
    })
  }

  const handleExportAll = () => {
    toast({
      title: "Exportar historial",
      description: "Exportando historial completo...",
    })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Historial de Clasificaciones</h1>
          <p className="text-muted-foreground">Revisa tus clasificaciones anteriores y su estado de auditoría</p>
        </div>
        <Button onClick={handleExportAll}>
          <Download className="h-4 w-4 mr-2" />
          Exportar Todo
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="h-5 w-5" />
            Filtros
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Buscar</label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Buscar en historial..."
                  value={globalFilter}
                  onChange={(e) => setGlobalFilter(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Estado de Auditoría</label>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="Todos los estados" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos los estados</SelectItem>
                  <SelectItem value="pending">Pendiente</SelectItem>
                  <SelectItem value="approved">Aprobado</SelectItem>
                  <SelectItem value="corrected">Corregido</SelectItem>
                  <SelectItem value="rejected">Rechazado</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Tipo de Entrada</label>
              <Select value={typeFilter} onValueChange={setTypeFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="Todos los tipos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos los tipos</SelectItem>
                  <SelectItem value="text">Texto</SelectItem>
                  <SelectItem value="file">Archivo</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Rango de Fechas</label>
              <Button variant="outline" className="w-full justify-start bg-transparent">
                <Calendar className="h-4 w-4 mr-2" />
                Seleccionar fechas
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Results Table */}
      <Card>
        <CardHeader>
          <CardTitle>Resultados ({table.getFilteredRowModel().rows.length} casos)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-2xl border">
            <Table>
              <TableHeader>
                {table.getHeaderGroups().map((headerGroup) => (
                  <TableRow key={headerGroup.id}>
                    {headerGroup.headers.map((header) => (
                      <TableHead key={header.id} className="font-medium">
                        {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                      </TableHead>
                    ))}
                  </TableRow>
                ))}
              </TableHeader>
              <TableBody>
                {table.getRowModel().rows?.length ? (
                  table.getRowModel().rows.map((row) => (
                    <TableRow key={row.id} className="hover:bg-muted/50">
                      {row.getVisibleCells().map((cell) => (
                        <TableCell key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</TableCell>
                      ))}
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={columns.length} className="h-24 text-center">
                      No se encontraron resultados.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between space-x-2 py-4">
            <div className="text-sm text-muted-foreground">
              Mostrando {table.getState().pagination.pageIndex * table.getState().pagination.pageSize + 1} a{" "}
              {Math.min(
                (table.getState().pagination.pageIndex + 1) * table.getState().pagination.pageSize,
                table.getFilteredRowModel().rows.length,
              )}{" "}
              de {table.getFilteredRowModel().rows.length} resultados
            </div>
            <div className="flex items-center space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => table.previousPage()}
                disabled={!table.getCanPreviousPage()}
              >
                Anterior
              </Button>
              <Button variant="outline" size="sm" onClick={() => table.nextPage()} disabled={!table.getCanNextPage()}>
                Siguiente
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
