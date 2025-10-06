"use client"

import type React from "react"

import { useTranslation } from "react-i18next"
import { useRouter, usePathname } from "next/navigation"
import {
  FileText,
  History,
  Shield,
  BarChart3,
  ScrollText,
  LogOut,
  Menu,
  X,
  Settings,
  HelpCircle,
  Bell,
  Users,
  Database,
  Download,
  Upload,
  Search,
  BookOpen,
  Activity,
} from "lucide-react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { useAuthStore } from "@/lib/store"
import { useToast } from "@/hooks/use-toast"
import { ThemeToggle } from "@/components/theme-toggle"
import { LanguageToggle } from "@/components/language-toggle"

interface AppLayoutProps {
  children: React.ReactNode
}

export function AppLayout({ children }: AppLayoutProps) {
  const { t } = useTranslation()
  const router = useRouter()
  const pathname = usePathname()
  const { toast } = useToast()
  const { user, logout } = useAuthStore()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const handleLogout = () => {
    logout()
    toast({
      title: "Sesión cerrada",
      description: "Has cerrado sesión exitosamente",
    })
    router.push("/")
  }

  const mainNavigation = [
    {
      name: t("nav.form"),
      href: "/app/form",
      icon: FileText,
      roles: ["user", "auditor", "admin"],
      badge: "Nuevo",
      badgeVariant: "default" as const,
    },
    {
      name: t("nav.history"),
      href: "/app/history",
      icon: History,
      roles: ["user", "auditor", "admin"],
    },
  ]

  const managementNavigation = [
    {
      name: t("nav.audit"),
      href: "/app/audit",
      icon: Shield,
      roles: ["auditor", "admin"],
      badge: "3",
      badgeVariant: "destructive" as const,
    },
    {
      name: t("nav.kpis"),
      href: "/app/kpis",
      icon: BarChart3,
      roles: ["auditor", "admin"],
    },
    {
      name: "Usuarios",
      href: "/app/users",
      icon: Users,
      roles: ["admin"],
    },
    {
      name: "Base de Datos",
      href: "/app/database",
      icon: Database,
      roles: ["admin"],
    },
  ]

  const toolsNavigation = [
    {
      name: "Búsqueda Avanzada",
      href: "/app/search",
      icon: Search,
      roles: ["user", "auditor", "admin"],
    },
    {
      name: "Exportar Datos",
      href: "/app/export",
      icon: Download,
      roles: ["auditor", "admin"],
    },
    {
      name: "Importar HS",
      href: "/app/import",
      icon: Upload,
      roles: ["admin"],
    },
    {
      name: "Documentación",
      href: "/app/docs",
      icon: BookOpen,
      roles: ["user", "auditor", "admin"],
    },
  ]

  const systemNavigation = [
    {
      name: t("nav.logs"),
      href: "/app/logs",
      icon: ScrollText,
      roles: ["admin"],
    },
    {
      name: "Monitor Sistema",
      href: "/app/monitor",
      icon: Activity,
      roles: ["admin"],
    },
    {
      name: "Configuración",
      href: "/app/settings",
      icon: Settings,
      roles: ["admin"],
    },
  ]

  const filterNavigation = (nav: any[]) => nav.filter((item) => user?.roles.some((role) => item.roles.includes(role)))

  const filteredMainNav = filterNavigation(mainNavigation)
  const filteredManagementNav = filterNavigation(managementNavigation)
  const filteredToolsNav = filterNavigation(toolsNavigation)
  const filteredSystemNav = filterNavigation(systemNavigation)

  const renderNavSection = (items: any[], title?: string) => (
    <div className="space-y-1">
      {title && (
        <div className="px-3 py-2">
          <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{title}</h3>
        </div>
      )}
      {items.map((item) => {
        const isActive = pathname === item.href
        return (
          <Button
            key={item.name}
            variant={isActive ? "default" : "ghost"}
            className="w-full justify-start h-9 px-3"
            onClick={() => {
              router.push(item.href)
              setSidebarOpen(false)
            }}
          >
            <item.icon className="mr-3 h-4 w-4 flex-shrink-0" />
            <span className="flex-1 text-left truncate">{item.name}</span>
            {item.badge && (
              <Badge variant={item.badgeVariant || "secondary"} className="ml-2 text-xs">
                {item.badge}
              </Badge>
            )}
          </Button>
        )
      })}
    </div>
  )

  return (
    <div className="min-h-screen bg-background lg:grid lg:grid-cols-[18rem_1fr]">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 bg-black/50 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <aside
        className={`
          z-50 w-72 bg-card border-r transition-transform duration-200 ease-in-out
          lg:translate-x-0 lg:static lg:h-screen lg:w-[18rem] lg:sticky lg:top-0
          ${sidebarOpen ? "fixed inset-y-0 left-0 translate-x-0" : "fixed inset-y-0 left-0 -translate-x-full lg:translate-x-0"}
        `}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center justify-between h-16 px-6 border-b">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
                <span className="text-sm font-bold text-primary-foreground">CC</span>
              </div>
              <div>
                <span className="font-semibold text-base">ClasifiCode</span>
                <p className="text-xs text-muted-foreground">Sistema HS v2.1</p>
              </div>
            </div>
            <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setSidebarOpen(false)}>
              <X className="h-4 w-4" />
            </Button>
          </div>

          <div className="flex-1 overflow-y-auto">
            <nav className="px-3 py-4 space-y-6">
              {/* Quick Actions */}
              <div className="space-y-2">
                <Button
                  className="w-full justify-start bg-primary/10 hover:bg-primary/20 text-primary border border-primary/20"
                  onClick={() => router.push("/app/form")}
                >
                  <FileText className="mr-3 h-4 w-4" />
                  Nueva Clasificación
                </Button>
                <Button
                  variant="outline"
                  className="w-full justify-start bg-transparent"
                  onClick={() => router.push("/app/search")}
                >
                  <Search className="mr-3 h-4 w-4" />
                  Búsqueda Rápida
                </Button>
              </div>

              <Separator />

              {/* Main Navigation */}
              {filteredMainNav.length > 0 && renderNavSection(filteredMainNav, "Principal")}

              {filteredManagementNav.length > 0 && (
                <>
                  <Separator />
                  {renderNavSection(filteredManagementNav, "Gestión")}
                </>
              )}

              {filteredToolsNav.length > 0 && (
                <>
                  <Separator />
                  {renderNavSection(filteredToolsNav, "Herramientas")}
                </>
              )}

              {filteredSystemNav.length > 0 && (
                <>
                  <Separator />
                  {renderNavSection(filteredSystemNav, "Sistema")}
                </>
              )}
            </nav>
          </div>

          <div className="border-t">
            {/* Notifications */}
            <div className="p-3 border-b">
              <Button variant="ghost" className="w-full justify-start h-8 px-2">
                <Bell className="mr-3 h-4 w-4" />
                <span className="flex-1 text-left text-sm">Notificaciones</span>
                <Badge variant="destructive" className="ml-2 text-xs">
                  2
                </Badge>
              </Button>
              <Button variant="ghost" className="w-full justify-start h-8 px-2 mt-1">
                <HelpCircle className="mr-3 h-4 w-4" />
                <span className="text-sm">Ayuda y Soporte</span>
              </Button>
            </div>

            {/* User info */}
            <div className="p-4 space-y-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-gradient-to-br from-primary to-primary/70 rounded-full flex items-center justify-center">
                  <span className="text-sm font-semibold text-primary-foreground">
                    {user?.name.charAt(0).toUpperCase()}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{user?.name}</p>
                  <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
                  <div className="flex gap-1 mt-1">
                    {user?.roles.map((role) => (
                      <Badge key={role} variant="outline" className="text-xs px-1 py-0">
                        {role}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>
              <Button variant="outline" className="w-full justify-start bg-transparent" onClick={handleLogout}>
                <LogOut className="mr-3 h-4 w-4" />
                {t("nav.logout")}
              </Button>
            </div>
          </div>
        </div>
      </aside>

      {/* Main content (grid column 2) */}
      <div className="flex flex-col min-h-screen">
        {/* Top bar */}
        <header className="h-16 bg-card border-b flex items-center justify-between px-6">
          <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setSidebarOpen(true)}>
            <Menu className="h-4 w-4" />
          </Button>

          <div className="flex items-center gap-2 ml-auto">
            <LanguageToggle />
            <ThemeToggle />
          </div>
        </header>

        {/* Page content */}
        <main className="p-6 flex-1">{children}</main>
      </div>
    </div>
  )
}
