"use client"

import "@/lib/i18n"
import { useState } from "react"
import { useRouter } from "next/navigation"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useTranslation } from "react-i18next"
import { Eye, EyeOff, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useToast } from "@/hooks/use-toast"
import { useAuthStore } from "@/lib/store"
import { api } from "@/lib/api"
import { ThemeToggle } from "@/components/theme-toggle"
import { LanguageToggle } from "@/components/language-toggle"

const loginSchema = z.object({
  email: z.string().email("Email inválido"),
  password: z.string().min(8, "La contraseña debe tener al menos 8 caracteres"),
})

type LoginForm = z.infer<typeof loginSchema>

export default function LoginPage() {
  const { t } = useTranslation()
  const router = useRouter()
  const { toast } = useToast()
  const login = useAuthStore((state) => state.login)
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  })

  const onSubmit = async (data: LoginForm) => {
    setIsLoading(true)
    try {
      const response = await api.auth.login(data)
      login(response.user, response.token)

      // Create audit log entry for session authorization
      console.log("[ClasifiCode] Autoriza sesión:", response.user.email)

      toast({
        title: t("common.success"),
        description: `Bienvenido, ${response.user.name}`,
      })

      router.push("/app/form")
    } catch (error) {
      toast({
        variant: "destructive",
        title: t("common.error"),
        description: error instanceof Error ? error.message : "Error de autenticación",
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary/5 via-background to-primary/10 flex items-center justify-center p-4">
      <div className="absolute top-4 right-4 flex items-center gap-2">
        <LanguageToggle />
        <ThemeToggle />
      </div>

      <div className="w-full max-w-md space-y-8">
        {/* Logo and Header */}
        <div className="text-center space-y-4">
          <div className="w-16 h-16 bg-primary rounded-2xl flex items-center justify-center mx-auto">
            <span className="text-2xl font-bold text-primary-foreground">CC</span>
          </div>
          <div className="space-y-2">
            <h1 className="text-3xl font-bold text-balance">{t("auth.welcome")}</h1>
            <p className="text-muted-foreground text-pretty">{t("auth.subtitle")}</p>
          </div>
        </div>

        {/* Login Card */}
        <Card className="border-0 shadow-2xl">
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl text-center">{t("auth.login")}</CardTitle>
            <CardDescription className="text-center">Ingresa tus credenciales para acceder al sistema</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">{t("auth.email")}</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="usuario@eafit.edu.co"
                  {...register("email")}
                  className={errors.email ? "border-destructive" : ""}
                />
                {errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">{t("auth.password")}</Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="••••••••"
                    {...register("password")}
                    className={errors.password ? "border-destructive pr-10" : "pr-10"}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4 text-muted-foreground" />
                    ) : (
                      <Eye className="h-4 w-4 text-muted-foreground" />
                    )}
                  </Button>

                  <Button
                    type="button"
                    variant="outline"
                    className="w-full mt-3"
                    onClick={async () => {
                      const values = getValues();
                      const email = values.email;
                      const password = values.password;
                      const name = (email || '').split('@')[0] || 'Usuario';
                      try {
                        setIsLoading(true);
                        await fetch('/api/auth/register', {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ email, password, name })
                        });
                        toast({ title: 'Usuario creado', description: 'Ahora inicia sesión.' });
                      } catch (e: any) {
                        toast({ variant: 'destructive', title: 'No se pudo registrar', description: e?.message || 'Error' });
                      } finally {
                        setIsLoading(false);
                      }
                    }}
                  >
                    Crear usuario
                  </Button>
                </div>
                {errors.password && <p className="text-sm text-destructive">{errors.password.message}</p>}
              </div>

              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {t("auth.loginButton")}
              </Button>
            </form>

            {/* Demo Credentials */}
            <div className="mt-6 p-4 bg-muted/50 rounded-lg space-y-2">
              <p className="text-sm font-medium text-muted-foreground">Credenciales de prueba:</p>
              <div className="text-xs space-y-1 text-muted-foreground">
                <p>
                  <strong>Admin:</strong> admin@eafit.edu.co / admin123
                </p>
                <p>
                  <strong>Auditor:</strong> auditor@eafit.edu.co / auditor123
                </p>
                <p>
                  <strong>Usuario:</strong> cualquier email válido / 8+ caracteres
                </p>
              </div>
            </div>

            {/* OAuth Placeholder */}
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-background px-2 text-muted-foreground">O continúa con</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <Button variant="outline" disabled>
                <svg className="mr-2 h-4 w-4" viewBox="0 0 24 24">
                  <path
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                    fill="#4285F4"
                  />
                  <path
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                    fill="#34A853"
                  />
                  <path
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                    fill="#FBBC05"
                  />
                  <path
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                    fill="#EA4335"
                  />
                </svg>
                Google
              </Button>
              <Button variant="outline" disabled>
                <svg className="mr-2 h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12.017 0C5.396 0 .029 5.367.029 11.987c0 5.079 3.158 9.417 7.618 11.174-.105-.949-.199-2.403.041-3.439.219-.937 1.219-5.160 1.219-5.160s-.219-.438-.219-1.085c0-1.016.219-1.775.657-1.775.219 0 .438.219.438.657 0 .438-.219 1.095-.438 1.533-.219.657.219 1.314.876 1.314 1.095 0 1.971-1.314 1.971-2.847 0-1.533-1.095-2.628-2.628-2.628-1.752 0-2.847 1.314-2.847 2.628 0 .657.219 1.095.438 1.533-.041.219-.219.438-.438.438-.219 0-.438-.219-.438-.438 0-.876-.657-1.533-1.533-1.533-.876 0-1.533.657-1.533 1.533 0 .876.657 1.533 1.533 1.533.219 0 .438-.041.657-.041.219.876.876 1.533 1.752 1.533.876 0 1.533-.657 1.533-1.533 0-.219-.041-.438-.041-.657.876-.219 1.533-.876 1.533-1.752 0-.876-.657-1.533-1.533-1.533z" />
                </svg>
                Microsoft
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Footer */}
        <p className="text-center text-sm text-muted-foreground">
          © 2024 EAFIT - ClasifiCode. Todos los derechos reservados.
        </p>
      </div>
    </div>
  )
}
