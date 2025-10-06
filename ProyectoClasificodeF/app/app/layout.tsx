"use client"

import type React from "react"

import { AuthGuard } from "@/components/auth-guard"
import { AppLayout } from "@/components/app-layout"

export default function AppLayoutWrapper({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <AuthGuard>
      <AppLayout>{children}</AppLayout>
    </AuthGuard>
  )
}
