"use client"

import { useRouter } from "next/navigation"
import { FileText, History, BarChart3, TrendingUp, Activity, FileCheck } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export default function AppHomePage() {
  const router = useRouter()

  const quickActions = [
    {
      title: "Nueva Clasificación",
      description: "Clasifique un nuevo producto o servicio usando IA",
      icon: FileText,
      href: "/app/form",
      color: "bg-blue-500",
    },
    {
      title: "Historial",
      description: "Revise sus clasificaciones anteriores",
      icon: History,
      href: "/app/history",
      color: "bg-purple-500",
    },
    {
      title: "KPI's y Estadísticas",
      description: "Visualice métricas y estadísticas del sistema",
      icon: BarChart3,
      href: "/app/kpis",
      color: "bg-green-500",
    },
  ]

  const features = [
    {
      icon: TrendingUp,
      title: "Alta Precisión",
      description: "Sistema de IA con más del 85% de precisión",
    },
    {
      icon: Activity,
      title: "Tiempo Real",
      description: "Clasificación instantánea con análisis en tiempo real",
    },
    {
      icon: FileCheck,
      title: "Auditoría Completa",
      description: "Registro completo de todas las operaciones",
    },
  ]

  return (
    <div className="flex flex-col space-y-8">
      {/* Header Section */}
      <div className="space-y-2">
        <h1 className="text-4xl font-bold tracking-tight">Bienvenido a ClasifiCode</h1>
        <p className="text-xl text-muted-foreground">
          Sistema inteligente de clasificación arancelaria con IA
        </p>
      </div>

      {/* Quick Actions */}
      <div className="grid gap-4 md:grid-cols-3">
        {quickActions.map((action) => {
          const Icon = action.icon
          return (
            <Card 
              key={action.title}
              className="hover:shadow-lg transition-shadow cursor-pointer border-2 hover:border-primary/50"
              onClick={() => router.push(action.href)}
            >
              <CardHeader>
                <div className="flex items-center gap-3">
                  <div className={`p-3 rounded-lg ${action.color} text-white`}>
                    <Icon className="h-6 w-6" />
                  </div>
                  <div className="flex-1">
                    <CardTitle className="text-lg">{action.title}</CardTitle>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <CardDescription>{action.description}</CardDescription>
                <Button className="w-full mt-4" variant="outline" size="sm">
                  Acceder
                </Button>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Features Section */}
      <div className="grid gap-4 md:grid-cols-3">
        {features.map((feature) => {
          const Icon = feature.icon
          return (
            <Card key={feature.title} className="border-l-4 border-l-primary">
              <CardHeader>
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-primary/10 text-primary">
                    <Icon className="h-5 w-5" />
                  </div>
                  <CardTitle className="text-base">{feature.title}</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <CardDescription>{feature.description}</CardDescription>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Stats Section */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card className="bg-gradient-to-r from-primary/5 to-primary/10 border-primary/20">
          <CardHeader>
            <CardTitle>Sistema de Clasificación Inteligente</CardTitle>
            <CardDescription>
              Powered by Advanced AI & Machine Learning
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center">
                <div className="text-3xl font-bold text-primary">85%+</div>
                <div className="text-sm text-muted-foreground">Precisión</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-primary">RGI</div>
                <div className="text-sm text-muted-foreground">Reglas de Interpretación</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-primary">IA</div>
                <div className="text-sm text-muted-foreground">Deep Learning</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-r from-purple-500/10 to-pink-500/10 border-purple-200 dark:border-purple-800">
          <CardHeader>
            <CardTitle>Inicio Rápido</CardTitle>
            <CardDescription>
              Comience a clasificar productos ahora
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button 
              className="w-full" 
              size="lg"
              onClick={() => router.push("/app/form")}
            >
              <FileText className="mr-2 h-5 w-5" />
              Nueva Clasificación
            </Button>
            <p className="text-sm text-muted-foreground mt-4 text-center">
              Ingrese una descripción de producto o suba un archivo para comenzar
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
