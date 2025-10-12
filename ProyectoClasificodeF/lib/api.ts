// API adapter wired to backend endpoints (Flask).
import { apiClient } from "@/lib/apiClient"

export interface LoginRequest { email: string; password: string }
export interface LoginResponse {
  user: { id: string; name: string; email: string; roles: ("user"|"auditor"|"admin")[] }
  token: string
}

export interface ClassifyResponse {
  hs: string; confidence: number;
  topK: { hs: string; confidence: number }[];
  explanation: { factors: { name: string; weight: number; note?: string }[]; rationale: string };
  similarities?: { id: string; title: string; snippet: string; hs: string; score: number }[];
  warnings?: string[];
}

const enableMock = (process.env.NEXT_PUBLIC_ENABLE_MOCK || "false") === "true"
const forceRole = (process.env.NEXT_PUBLIC_FORCE_ROLE || "").toLowerCase()

function mapRoles(role: string | string[] | undefined): ("user"|"auditor"|"admin")[] {
  if (!role) role = ["user"]
  if (Array.isArray(role)) {
    const roles = role.map(r => String(r).toLowerCase())
    if (forceRole && !roles.includes(forceRole)) roles.push(forceRole)
    return Array.from(new Set(roles)) as any
  }
  const r = String(role).toLowerCase()
  const roles: any[] = ["user"]
  if (r.includes("auditor")) roles.push("auditor")
  if (r.includes("admin")) roles.push("admin")
  if (forceRole && !roles.includes(forceRole)) roles.push(forceRole)
  return Array.from(new Set(roles)) as any
}

function mapClassification(details: any): ClassifyResponse {
  const d = details?.details || details?.analysis || details || {}
  const hs = d.best_hs || d.hs || d.bestHS || d.suggested_hs || "0000.00.00"
  const confidence = Number(d.confidence ?? d.score ?? d.best_confidence ?? 0.7)
  const topK = (d.candidates || d.topK || []).map((c: any) => ({
    hs: c.hs || c.hs_code || c.code || "0000.00.00",
    confidence: Number(c.confidence ?? c.score ?? 0),
  }))
  const rationale = d.rationale || d.explanation || d.reason || "Clasificación generada por el modelo."
  const factors = (d.factors || []).map((f: any) => ({
    name: f.name || f.factor || "Factor",
    weight: Number(f.weight ?? f.score ?? 0),
    note: f.note || f.description || undefined,
  }))
  const similarities = (d.similarities || d.related || []).map((s: any, i: number) => ({
    id: String(s.id ?? i + 1),
    title: s.title || s.name || "Relacionado",
    snippet: s.snippet || s.text || "",
    hs: s.hs || s.hs_code || hs,
    score: Number(s.score ?? 0),
  }))
  const warnings = d.warnings || []
  return { hs, confidence, topK, explanation: { factors, rationale }, similarities, warnings }
}

export const api = {
  auth: {
    login: async (data: LoginRequest): Promise<LoginResponse> => {
      if (enableMock) return { user: { id: "1", name: "Admin", email: data.email, roles: ["user","auditor","admin"] }, token: "mock" }
      // Backend real: /auth/login
      const res = await apiClient.post("/auth/login", data)
      const payload = res.data?.details || res.data
      const token = payload?.token || payload?.access_token || res.data?.token || ""
      const userObj = payload?.user || {}
      return { user: { id: String(userObj.id || "1"), name: userObj.name || "Usuario", email: userObj.email || data.email, roles: mapRoles(userObj.role || userObj.roles) }, token }
    },
    logout: async (): Promise<void> => { try { await apiClient.post("/logout") } catch {}; if (typeof window !== "undefined") sessionStorage.removeItem("token") },
  },
  classify: {
    // High-level helper used by ResultPage
    process: async (payload: { text: string; lang?: string }): Promise<{
      topK: { hs: string; confidence: number; description?: string }[]
      explanation: { factors: { name: string; weight: number; note?: string }[]; rationale: string }
      similarities?: { id: string; title: string; snippet: string; hs: string; score: number }[]
      warnings?: string[]
    }> => {
      try {
        // Create case
        const title = payload.text.slice(0, 80)
        const desc = payload.text.slice(80)
        const caseRes = await apiClient.post("/cases", { product_title: title, product_desc: desc })
        
        if (!caseRes.data) {
          throw new Error("No se pudo crear el caso")
        }
        
        const caseId = caseRes.data?.details?.case_id || caseRes.data?.details?.id || caseRes.data?.case_id
        if (!caseId) {
          throw new Error("ID de caso no válido")
        }
        
        // Classify using v1 (national code)
        const classifyRes = await apiClient.post(`/api/v1/classify/${caseId}`, {})
        
        if (!classifyRes.data) {
          throw new Error("No se pudo clasificar el producto")
        }
        
        const d = classifyRes.data?.details || classifyRes.data || {}
        const national = d.national_code || d.hs6 || "0000000000"
        const conf = d.confidence || 0.85
        
        return {
          topK: [
            {
              hs: national,
              confidence: conf,
              description: d.title || "",
            },
          ],
          explanation: {
            rationale: d.rationale || "Clasificación basada en descripción del producto",
            factors: (d.legal_notes || []).map((ln: any) => ({ name: ln?.title || "Nota", weight: 0.5, note: ln?.text || ln })),
          },
          similarities: [],
          warnings: conf < 0.7 ? ["Clasificación de baja confianza"] : [],
        }
      } catch (error: any) {
        console.error("Error en clasificación:", error)
        throw new Error(error.message || "Error al procesar la clasificación")
      }
    },
    text: async (payload: { text: string; lang?: string }): Promise<ClassifyResponse> => {
      if (enableMock) return { hs: "8471.30.00", confidence: 0.84, topK: [{hs:"8471.30.00",confidence:0.84}], explanation: { factors: [], rationale: "Mock" } }
      // Backend requiere product_title/product_desc
      const title = payload.text.slice(0, 80)
      const desc = payload.text.slice(80)
      const caseRes = await apiClient.post("/cases", { product_title: title, product_desc: desc })
      const caseId = caseRes.data?.details?.case_id || caseRes.data?.details?.id || caseRes.data?.case_id
      // Usar endpoint v1 nacional
      const classifyRes = await apiClient.post(`/api/v1/classify/${caseId}`, {})
      return mapClassification(classifyRes.data)
    },
    file: async (formData: FormData): Promise<ClassifyResponse> => {
      if (enableMock) return { hs: "8517.12.00", confidence: 0.79, topK: [{hs:"8517.12.00",confidence:0.79}], explanation: { factors: [], rationale: "Mock" } }
      // Actualmente backend no expone carga de archivo directa; fallback a texto vacío -> error controlado
      throw new Error("Clasificación por archivo no disponible en el backend")
    },
  },
  history: {
    list: async (params: { page?: number; query?: string; status?: string } = {}) => {
      const res = await apiClient.get("/cases", { params });
      const d = res.data?.details || res.data;
      return { items: d?.cases || d?.items || [], total: d?.pagination?.total || d?.total || 0 }
    },
    get: async (caseId: number | string) => (await apiClient.get(`/cases/${caseId}`)).data?.details || (await apiClient.get(`/cases/${caseId}`)).data,
  },
  audit: {
    validate: async (caseId: number | string, finalHS: string, note?: string) => (await apiClient.post(`/cases/${caseId}/validate`, { final_hs_code: finalHS, comment: note || ""})).data?.details,
    candidates: async (caseId: number | string) => (await apiClient.get(`/cases/${caseId}/candidates`)).data?.details?.candidates || [],
    addCandidate: async (caseId: number | string, hs: string, confidence: number) => (
      await apiClient.post(`/cases/${caseId}/candidates`, { candidates: [{ hs_code: hs, title: "Propuesta manual", confidence }] })
    ).data?.details,
  },
  kpis: { summary: async (params: { from?: string; to?: string } = {}) => (await apiClient.get("/stats", { params })).data?.details || {} },
  health: { check: async () => (await apiClient.get("/health")).data },
  ocr: {
    // Stub para evitar errores en la UI mientras no exista endpoint en backend
    process: async (_: { file: File }) => ({ ocrText: "", lang: "es" as const }),
  }
}
