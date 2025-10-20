"use client"

import type React from "react"

import { useRouter, usePathname } from "next/navigation"
import { FileText, History, Menu, X, LogOut } from "lucide-react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { useAuthStore } from "@/lib/store"
import { useToast } from "@/hooks/use-toast"
import { ThemeToggle } from "@/components/theme-toggle"

interface AppLayoutProps {
  children: React.ReactNode
}

export function AppLayout({ children }: AppLayoutProps) {
  const router = useRouter()
  const pathname = usePathname()
  const { toast } = useToast()
  const { logout } = useAuthStore()
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
      name: "Clasificar",
      href: "/app/form",
      icon: FileText,
    },
    {
      name: "Historial",
      href: "/app/history",
      icon: History,
    },
  ]

  const filterNavigation = (nav: any[]) => nav

  const filteredMainNav = filterNavigation(mainNavigation)

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
          <div className="flex items-center justify-between p-4 border-b">
            <div className="flex items-center space-x-2">
              <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setSidebarOpen(!sidebarOpen)}>
                {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
                <span className="sr-only">Menú</span>
              </Button>
              <h1 className="text-lg font-semibold ml-2">ClasifiCode</h1>
            </div>
          </div>

          {/* Navigation */}
          <div className="flex-1 overflow-y-auto p-2">
            {renderNavSection(filteredMainNav)}
          </div>

          {/* Logout button */}
          <div className="p-4 border-t">
            <Button variant="outline" className="w-full" onClick={handleLogout}>
              <LogOut className="mr-2 h-4 w-4" />
              Cerrar sesión
            </Button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex flex-col min-h-screen">
        {/* Top bar */}
        <header className="h-16 bg-card border-b flex items-center justify-between px-6">
          <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setSidebarOpen(true)}>
            <Menu className="h-4 w-4" />
          </Button>
          <div className="ml-auto">
            <ThemeToggle />
          </div>
        </header>

        {/* Page content */}
        <main className="p-6 flex-1">{children}</main>
      </div>
    </div>
  )
}
