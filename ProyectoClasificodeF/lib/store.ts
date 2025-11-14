import { create } from "zustand"
import { devtools, persist } from "zustand/middleware"

// Auth State
interface User {
  id: string
  name: string
  email: string
  roles: ("user" | "auditor" | "admin")[]
}

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  login: (user: User, token: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  devtools(
    persist(
      (set) => ({
        user: null,
        token: null,
        isAuthenticated: false,
        login: (user, token) => {
          try { 
            if (typeof window !== "undefined") {
              sessionStorage.setItem("token", token)
            }
          } catch {}
          set({ user, token, isAuthenticated: true })
        },
        logout: () => {
          try { 
            if (typeof window !== "undefined") {
              sessionStorage.removeItem("token")
            }
          } catch {}
          set({ user: null, token: null, isAuthenticated: false })
        },
      }),
      {
        name: "auth-storage",
      },
    ),
  ),
)

// Classification State
interface UploadedFile {
  id: string
  name: string
  size: number
  type: string
  url: string
}

// Tipo según respuesta real del backend Flask
interface BackendClassificationResult {
  hs?: string
  title?: string
  confidence?: number | string
  rationale?: string | Record<string, any>
  topK?: Array<{ 
    hs: string; 
    confidence: number;
    title?: string;
  }>
  candidates?: Array<{
    hs?: string
    hs_code?: string
    national_code?: string
    confidence?: number
    score?: number
    title?: string
  }>
}

interface Prediction {
  hs: string
  title?: string
  confidence: number
  topK: Array<{ 
    hs: string; 
    confidence: number;
    title?: string;
  }>
}

interface Similarity {
  id: string
  title: string
  snippet: string
  hs: string
  score: number
}

interface Explanation {
  factors: Array<{ name: string; weight: number; note?: string }>
  rationale: string
}

interface PredictionMeta {
  rationale: Record<string, any>
  chapterCoherence?: string
  suspectCode?: boolean
  requiresReview?: boolean
  responseTime?: number
  validationFlags?: Record<string, any> | null
}

interface ClassificationState {
  inputType: "text" | "file"
  rawText?: string
  files?: UploadedFile[]
  ocrText?: string
  preprocessedText?: string
  prediction?: Prediction
  similarities?: Similarity[]
  explanation?: Explanation
  savedCaseId?: string
  caseData?: any
  flaggedLowConfidence?: boolean
  predictionMeta?: PredictionMeta
  setInputType: (type: "text" | "file") => void
  setRawText: (text: string) => void
  setFiles: (files: UploadedFile[]) => void
  setOcrText: (text: string) => void
  setPrediction: (prediction: Prediction) => void
  setClassificationResult: (result: BackendClassificationResult) => void
  setCaseId: (id: string) => void
  setCaseData: (data: any) => void
  setSimilarities: (similarities: Similarity[]) => void
  setExplanation: (explanation: Explanation) => void
  setFlaggedLowConfidence: (flagged: boolean) => void
  reset: () => void
}

export const useClassificationStore = create<ClassificationState>()(
  devtools(
    persist(
      (set) => ({
        inputType: "text",
        setInputType: (type) => set({ inputType: type }),
        setRawText: (text) => set({ rawText: text }),
        setFiles: (files) => set({ files }),
        setOcrText: (text) => set({ ocrText: text }),
        setPrediction: (prediction) => set({ prediction }),
        setClassificationResult: (result) => {
          const rawRationale = result.rationale as any
          let rationaleText = "Clasificación generada automáticamente"
          let factors: Array<{ name: string; weight: number; note?: string }> = []
          let requiresReview = false
          let rationaleData: Record<string, any> = {}

          if (typeof rawRationale === "string") {
            rationaleText = rawRationale
          } else if (rawRationale && typeof rawRationale === "object") {
            rationaleText = rawRationale.decision || rationaleText
            requiresReview = Boolean(rawRationale.requires_review)
            rationaleData = rawRationale

            const rawFactors = Array.isArray(rawRationale.factores_clave) ? rawRationale.factores_clave : []
            const rawValidations = Array.isArray(rawRationale.validations)
              ? rawRationale.validations
              : rawRationale.validations && typeof rawRationale.validations === "object"
                ? Object.values(rawRationale.validations)
                : []
            const total = rawFactors.length || 1

            factors = rawFactors.map((factor: string, idx: number) => {
              return {
                name: factor,
                weight: Number((1 / total).toFixed(2)),
                note: rawValidations[idx],
              }
            })

            // Añadir información de coherencia y código sospechoso como notas adicionales
            if (rawRationale.chapter_coherence) {
              factors.push({
                name: `coherencia_capitulo=${rawRationale.chapter_coherence}`,
                weight: 0.1,
              })
            }
            if (typeof rawRationale.suspect_code !== "undefined") {
              factors.push({
                name: `codigo_sospechoso=${rawRationale.suspect_code ? "sí" : "no"}`,
                weight: 0.1,
              })
            }
          }

          const topK = (result.topK || result.candidates || []).map((item: any) => ({
            hs: item.hs || item.hs_code || item.national_code || "0000.00.00",
            confidence: Number(item.confidence ?? item.score ?? 0),
            title: item.title,
          }))

          const prediction: Prediction = {
            hs: result.hs || "0000.00.00",
            title: result.title,
            confidence: Number(result.confidence ?? 0.5),
            topK,
          }

          const rawChapter = rationaleData?.chapter_coherence
          let chapterCoherence: string | undefined
          if (typeof rawChapter === "string") {
            chapterCoherence = rawChapter
          } else if (rawChapter === true) {
            chapterCoherence = "OK"
          } else if (rawChapter === false) {
            chapterCoherence = "FAIL"
          }

          const predictionMeta: PredictionMeta = {
            rationale: rationaleData,
            chapterCoherence,
            suspectCode: typeof rationaleData.suspect_code === "boolean" ? rationaleData.suspect_code : undefined,
            requiresReview,
            responseTime:
              typeof (result as any).response_time === "number"
                ? Number((result as any).response_time)
                : undefined,
            validationFlags: (result as any).validation_flags || rationaleData.validation_flags || null,
          }

          set({
            prediction,
            explanation: {
              rationale: rationaleText,
              factors,
            },
            flaggedLowConfidence: requiresReview,
            predictionMeta,
          })
        },
        setCaseId: (id) => set({ savedCaseId: id }),
        setCaseData: (data) => set({ caseData: data }),
        setSimilarities: (similarities) => set({ similarities }),
        setExplanation: (explanation) => set({ explanation }),
        setFlaggedLowConfidence: (flagged) => set({ flaggedLowConfidence: flagged }),
        reset: () =>
          set({
            rawText: undefined,
            files: undefined,
            ocrText: undefined,
            preprocessedText: undefined,
            prediction: undefined,
            similarities: undefined,
            explanation: undefined,
            savedCaseId: undefined,
            caseData: undefined,
            flaggedLowConfidence: undefined,
            predictionMeta: undefined,
          }),
      }),
      {
        name: "classification-storage",
      },
    ),
  ),
)

// Audit Queue State
interface AuditCase {
  caseId: string
  originalHS: string
  alternatives: Array<{ hs: string; confidence: number }>
  explanation: string
  note?: string
  status: "pending" | "corrected" | "rejected"
  correctedHS?: string
  reviewer?: string
  updatedAt: string
}

interface AuditState {
  cases: AuditCase[]
  setCases: (cases: AuditCase[]) => void
  updateCase: (caseId: string, updates: Partial<AuditCase>) => void
}

export const useAuditStore = create<AuditState>()(
  devtools((set, get) => ({
    cases: [],
    setCases: (cases) => set({ cases }),
    updateCase: (caseId, updates) =>
      set({
        cases: get().cases.map((c) => (c.caseId === caseId ? { ...c, ...updates } : c)),
      }),
  })),
)
