"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ExternalLink, Package } from "lucide-react"
import { Button } from "@/components/ui/button"

interface SimilarItemsListProps {
  similarities?: Array<{
    id: string
    title: string
    snippet: string
    hs: string
    score: number
  }>
}

export function SimilarItemsList({ similarities }: SimilarItemsListProps) {
  if (!similarities || similarities.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Package className="h-5 w-5" />
            Productos Similares
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-center py-8">
            No se encontraron productos similares en la base de datos.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Package className="h-5 w-5" />
          Productos Similares
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {similarities.map((item) => (
            <div key={item.id} className="p-4 border rounded-2xl hover:bg-muted/50 transition-colors">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 space-y-2">
                  <div className="flex items-center gap-2">
                    <h4 className="font-medium">{item.title}</h4>
                    <Badge variant="outline" className="font-mono text-xs">
                      {item.hs}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground leading-relaxed">{item.snippet}</p>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">Similitud: {Math.round(item.score * 100)}%</span>
                  </div>
                </div>
                <Button variant="ghost" size="sm">
                  <ExternalLink className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
