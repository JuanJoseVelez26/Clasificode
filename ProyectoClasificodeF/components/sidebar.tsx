"use client"

import { Home, Search, FilePlus, Bell, HelpCircle, LogOut, Settings } from "lucide-react"
import { Button } from "./ui/button"
import { useAuthStore } from "@/lib/store"
import { useRouter } from "next/navigation"

export function Sidebar() {
  const { user, logout } = useAuthStore()
  const router = useRouter()

  const handleLogout = () => {
    logout()
    router.push('/login')
  }

  return (
    <div className="hidden border-r bg-muted/40 md:block">
      <div className="flex h-full max-h-screen flex-col gap-2">
        <div className="flex h-14 items-center border-b px-4 lg:h-[60px] lg:px-6">
          <div className="flex items-center gap-2 font-semibold">
            <span className="text-xl">Classify Code</span>
          </div>
        </div>
        
        <div className="flex-1">
          <nav className="grid items-start px-2 text-sm font-medium lg:px-4">
            <Button
              variant="ghost"
              className="w-full justify-start gap-3 text-left"
              onClick={() => router.push('/dashboard')}
            >
              <Home className="h-4 w-4" />
              Inicio
            </Button>
            
            <Button
              variant="ghost"
              className="w-full justify-start gap-3 text-left"
              onClick={() => router.push('/search')}
            >
              <Search className="h-4 w-4" />
              Búsqueda Rápida
            </Button>
            
            <Button
              variant="ghost"
              className="w-full justify-start gap-3 text-left"
              onClick={() => router.push('/new-classification')}
            >
              <FilePlus className="h-4 w-4" />
              Nueva Clasificación
            </Button>
            
            <Button
              variant="ghost"
              className="w-full justify-start gap-3 text-left"
              onClick={() => router.push('/notifications')}
            >
              <Bell className="h-4 w-4" />
              Notificaciones
            </Button>
            
            <Button
              variant="ghost"
              className="w-full justify-start gap-3 text-left"
              onClick={() => router.push('/help')}
            >
              <HelpCircle className="h-4 w-4" />
              Ayuda y Soporte
            </Button>
            
            <Button
              variant="ghost"
              className="w-full justify-start gap-3 text-left"
              onClick={() => router.push('/settings')}
            >
              <Settings className="h-4 w-4" />
              Configuración
            </Button>
          </nav>
        </div>
        
        <div className="mt-auto p-4">
          <div className="flex items-center gap-4 rounded-lg border p-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
              <span className="font-medium text-primary">
                {user?.name?.charAt(0).toUpperCase() || 'U'}
              </span>
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium">{user?.name || 'Usuario'}</p>
              <p className="text-xs text-muted-foreground">
                {user?.email || 'usuario@ejemplo.com'}
              </p>
            </div>
            <Button variant="ghost" size="icon" onClick={handleLogout}>
              <LogOut className="h-4 w-4" />
              <span className="sr-only">Cerrar sesión</span>
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
