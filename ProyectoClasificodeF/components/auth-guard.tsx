"use client"

import type React from "react"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuthStore } from "@/lib/store"
import { Loader2 } from "lucide-react"

interface AuthGuardProps {
  children: React.ReactNode
  requiredRoles?: ("user" | "auditor" | "admin")[]
}

export function AuthGuard({ children, requiredRoles = ["user"] }: AuthGuardProps) {
  const router = useRouter()
  const { isAuthenticated, user } = useAuthStore()

  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/")
      return
    }

    if (user && requiredRoles.length > 0 && user.roles) {
      const hasRequiredRole = requiredRoles.some((role) => user.roles.includes(role))
      if (!hasRequiredRole) {
        router.push("/app/form") // Redirect to default page if no required role
        return
      }
    }
  }, [isAuthenticated, user, requiredRoles, router])

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex items-center gap-2">
          <Loader2 className="h-6 w-6 animate-spin" />
          <span>Verificando autenticación...</span>
        </div>
      </div>
    )
  }

  if (user && requiredRoles.length > 0 && user.roles) {
    const hasRequiredRole = requiredRoles.some((role) => user.roles.includes(role))
    if (!hasRequiredRole) {
      return (
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center space-y-4">
            <h1 className="text-2xl font-bold">Acceso Denegado</h1>
            <p className="text-muted-foreground">No tienes permisos para acceder a esta página.</p>
          </div>
        </div>
      )
    }
  }

  return <>{children}</>
}
