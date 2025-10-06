import i18n from "i18next"
import { initReactI18next, useTranslation } from "react-i18next"

const resources = {
  es: {
    translation: {
      // Auth
      "auth.login": "Iniciar Sesión",
      "auth.email": "Correo Electrónico",
      "auth.password": "Contraseña",
      "auth.loginButton": "Ingresar",
      "auth.welcome": "Bienvenido a ClasifiCode",
      "auth.subtitle": "Sistema inteligente de clasificación de productos",

      // Navigation
      "nav.form": "Clasificar",
      "nav.history": "Historial",
      "nav.audit": "Auditoría",
      "nav.kpis": "KPIs",
      "nav.logs": "Bitácora",
      "nav.logout": "Cerrar Sesión",

      // Form
      "form.inputType": "Tipo de entrada",
      "form.text": "Texto",
      "form.file": "Documento/Imagen",
      "form.textPlaceholder": "Describe el producto que deseas clasificar...",
      "form.uploadFiles": "Subir archivos",
      "form.process": "Preprocesar y Buscar HS",
      "form.minChars": "Mínimo 15 caracteres requeridos",

      // Results
      "results.prediction": "Predicción",
      "results.confidence": "Confianza",
      "results.alternatives": "Alternativas",
      "results.explanation": "Explicación",
      "results.similarities": "Productos Similares",
      "results.export": "Exportar",
      "results.save": "Guardar Caso",
      "results.flagLowConfidence": "Notificar Baja Confianza",

      // Confidence levels
      "confidence.high": "Alta",
      "confidence.medium": "Media",
      "confidence.low": "Baja",

      // Logs
      "logs.title": "Logs del Sistema",
      "logs.subtitle": "Registro detallado de todas las actividades del sistema",
      "logs.filters": "Filtros",
      "logs.search": "Buscar",
      "logs.status": "Estado",
      "logs.action": "Acción",
      "logs.period": "Período",
      "logs.results": "Resultados",
      "logs.refresh": "Actualizar",
      "logs.export": "Exportar",
      "logs.timestamp": "Timestamp",
      "logs.user": "Usuario",
      "logs.details": "Detalles",
      "logs.duration": "Duración",

      // Audit
      "audit.title": "Cola de Auditoría",
      "audit.subtitle": "Casos pendientes de revisión por baja confianza",
      "audit.pending": "Pendientes",
      "audit.inReview": "En Revisión",
      "audit.completed": "Completados",
      "audit.approve": "Aprobar",
      "audit.correct": "Corregir",
      "audit.reject": "Rechazar",
      "audit.comment": "Comentario",
      "audit.newHsCode": "Nuevo Código HS",

      // History
      "history.title": "Historial de Clasificaciones",
      "history.subtitle": "Registro de todas las clasificaciones realizadas",
      "history.filters": "Filtros",
      "history.dateRange": "Rango de Fechas",
      "history.inputType": "Tipo de Entrada",
      "history.status": "Estado",
      "history.export": "Exportar",

      // KPIs
      "kpis.title": "KPIs y Métricas",
      "kpis.subtitle": "Panel de control con métricas clave del sistema",
      "kpis.totalClassifications": "Total Clasificaciones",
      "kpis.averageAccuracy": "Precisión Promedio",
      "kpis.averageConfidence": "Confianza Promedio",
      "kpis.pendingAudits": "Auditorías Pendientes",
      "kpis.volume": "Volumen",
      "kpis.confidence": "Confianza",
      "kpis.categories": "Categorías",
      "kpis.audit": "Auditoría",

      // Common
      "common.loading": "Cargando...",
      "common.error": "Error",
      "common.success": "Éxito",
      "common.cancel": "Cancelar",
      "common.save": "Guardar",
      "common.edit": "Editar",
      "common.delete": "Eliminar",
      "common.all": "Todos",
      "common.approved": "Aprobado",
      "common.rejected": "Rechazado",
      "common.pending": "Pendiente",
      "common.high": "Alta",
      "common.medium": "Media",
      "common.low": "Baja",
    },
  },
  en: {
    translation: {
      // Auth
      "auth.login": "Sign In",
      "auth.email": "Email",
      "auth.password": "Password",
      "auth.loginButton": "Sign In",
      "auth.welcome": "Welcome to ClasifiCode",
      "auth.subtitle": "Intelligent product classification system",

      // Navigation
      "nav.form": "Classify",
      "nav.history": "History",
      "nav.audit": "Audit",
      "nav.kpis": "KPIs",
      "nav.logs": "Logs",
      "nav.logout": "Sign Out",

      // Form
      "form.inputType": "Input Type",
      "form.text": "Text",
      "form.file": "Document/Image",
      "form.textPlaceholder": "Describe the product you want to classify...",
      "form.uploadFiles": "Upload Files",
      "form.process": "Preprocess and Search HS",
      "form.minChars": "Minimum 15 characters required",

      // Results
      "results.prediction": "Prediction",
      "results.confidence": "Confidence",
      "results.alternatives": "Alternatives",
      "results.explanation": "Explanation",
      "results.similarities": "Similar Products",
      "results.export": "Export",
      "results.save": "Save Case",
      "results.flagLowConfidence": "Flag Low Confidence",

      // Confidence levels
      "confidence.high": "High",
      "confidence.medium": "Medium",
      "confidence.low": "Low",

      // Logs
      "logs.title": "System Logs",
      "logs.subtitle": "Detailed record of all system activities",
      "logs.filters": "Filters",
      "logs.search": "Search",
      "logs.status": "Status",
      "logs.action": "Action",
      "logs.period": "Period",
      "logs.results": "Results",
      "logs.refresh": "Refresh",
      "logs.export": "Export",
      "logs.timestamp": "Timestamp",
      "logs.user": "User",
      "logs.details": "Details",
      "logs.duration": "Duration",

      // Audit
      "audit.title": "Audit Queue",
      "audit.subtitle": "Cases pending review due to low confidence",
      "audit.pending": "Pending",
      "audit.inReview": "In Review",
      "audit.completed": "Completed",
      "audit.approve": "Approve",
      "audit.correct": "Correct",
      "audit.reject": "Reject",
      "audit.comment": "Comment",
      "audit.newHsCode": "New HS Code",

      // History
      "history.title": "Classification History",
      "history.subtitle": "Record of all performed classifications",
      "history.filters": "Filters",
      "history.dateRange": "Date Range",
      "history.inputType": "Input Type",
      "history.status": "Status",
      "history.export": "Export",

      // KPIs
      "kpis.title": "KPIs & Metrics",
      "kpis.subtitle": "Dashboard with key system metrics",
      "kpis.totalClassifications": "Total Classifications",
      "kpis.averageAccuracy": "Average Accuracy",
      "kpis.averageConfidence": "Average Confidence",
      "kpis.pendingAudits": "Pending Audits",
      "kpis.volume": "Volume",
      "kpis.confidence": "Confidence",
      "kpis.categories": "Categories",
      "kpis.audit": "Audit",

      // Common
      "common.loading": "Loading...",
      "common.error": "Error",
      "common.success": "Success",
      "common.cancel": "Cancel",
      "common.save": "Save",
      "common.edit": "Edit",
      "common.delete": "Delete",
      "common.all": "All",
      "common.approved": "Approved",
      "common.rejected": "Rejected",
      "common.pending": "Pending",
      "common.high": "High",
      "common.medium": "Medium",
      "common.low": "Low",
    },
  },
}

i18n.use(initReactI18next).init({
  resources,
  lng: "es",
  fallbackLng: "es",
  interpolation: {
    escapeValue: false,
  },
})

export const useI18n = () => {
  return useTranslation()
}

export default i18n
