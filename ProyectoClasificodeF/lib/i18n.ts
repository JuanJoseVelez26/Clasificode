// Sistema monolingüe en español - Internacionalización eliminada
// ClasifiCode funciona exclusivamente en español para simplificar el sistema

export const useI18n = () => {
  // Función de compatibilidad que devuelve texto en español
  return {
    t: (key: string) => {
      // Mapeo básico de claves a texto en español
      const translations: Record<string, string> = {
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
      }
      return translations[key] || key
    },
    i18n: {
      changeLanguage: () => {} // Función vacía para compatibilidad
    }
  }
}

export default {
  use: () => {},
  init: () => {}
}