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
          try { if (typeof window !== "undefined") sessionStorage.setItem("token", token) } catch {}
          set({ user, token, isAuthenticated: true })
        },
        logout: () => {
          try { if (typeof window !== "undefined") sessionStorage.removeItem("token") } catch {}
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

interface Prediction {
  hs: string
  confidence: number
  topK: Array<{ hs: string; confidence: number }>
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

interface ClassificationState {
  inputType: "text" | "file"
  rawText?: string
  files?: UploadedFile[]
  ocrText?: string
  lang?: "es" | "en"
  preprocessedText?: string
  prediction?: Prediction
  similarities?: Similarity[]
  explanation?: Explanation
  savedCaseId?: string
  flaggedLowConfidence?: boolean
  setInputType: (type: "text" | "file") => void
  setRawText: (text: string) => void
  setFiles: (files: UploadedFile[]) => void
  setOcrText: (text: string) => void
  setLang: (lang: "es" | "en") => void
  setPrediction: (prediction: Prediction) => void
  setSimilarities: (similarities: Similarity[]) => void
  setExplanation: (explanation: Explanation) => void
  setSavedCaseId: (id: string) => void
  setFlaggedLowConfidence: (flagged: boolean) => void
  reset: () => void
}

export const useClassificationStore = create<ClassificationState>()(
  devtools((set) => ({
    inputType: "text",
    setInputType: (type) => set({ inputType: type }),
    setRawText: (text) => set({ rawText: text }),
    setFiles: (files) => set({ files }),
    setOcrText: (text) => set({ ocrText: text }),
    setLang: (lang) => set({ lang }),
    setPrediction: (prediction) => set({ prediction }),
    setSimilarities: (similarities) => set({ similarities }),
    setExplanation: (explanation) => set({ explanation }),
    setSavedCaseId: (id) => set({ savedCaseId: id }),
    setFlaggedLowConfidence: (flagged) => set({ flaggedLowConfidence: flagged }),
    reset: () =>
      set({
        rawText: undefined,
        files: undefined,
        ocrText: undefined,
        lang: undefined,
        preprocessedText: undefined,
        prediction: undefined,
        similarities: undefined,
        explanation: undefined,
        savedCaseId: undefined,
        flaggedLowConfidence: undefined,
      }),
  })),
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
