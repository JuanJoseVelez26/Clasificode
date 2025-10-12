import axios from "axios"

const baseURL = process.env.NEXT_PUBLIC_API_BASE_URL || ""

export const apiClient = axios.create({ baseURL, withCredentials: true })

apiClient.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    let token = sessionStorage.getItem("token")
    if (!token) {
      try {
        const raw = localStorage.getItem("auth-storage")
        if (raw) {
          const parsed = JSON.parse(raw)
          token = parsed?.state?.token || null
        }
      } catch {}
    }
    if (token) config.headers.Authorization = `Bearer ${token}`
  }
  try { config.headers["X-Request-Id"] = (crypto?.randomUUID?.() || Math.random().toString(36).slice(2)) as any } catch {}
  return config
})

apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    const message = err?.response?.data?.message ?? err.message ?? "Error de red"
    return Promise.reject({ message, status: err?.response?.status, data: err?.response?.data })
  }
)
