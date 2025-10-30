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
  confidence?: number
  rationale?: string
  topK?: Array<{ 
    hs: string; 
    confidence: number;
    title?: string;
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
          const prediction: Prediction = {
            hs: result.hs || "0000.00.00",
            title: result.title,
            confidence: result.confidence || 0.5,
            topK: result.topK || [],
          }
          set({ 
            prediction,
            explanation: {
              rationale: result.rationale || "Clasificación generada automáticamente",
              factors: [],
            }
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
