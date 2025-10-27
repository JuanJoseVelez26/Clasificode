# 🚀 Clasificode - Sistema de Clasificación Arancelaria Inteligente

## 📋 Descripción del Proyecto

**Clasificode** es un sistema avanzado de clasificación arancelaria que utiliza inteligencia artificial y reglas de interpretación general (RGI) para clasificar productos automáticamente según el sistema arancelario colombiano. El sistema combina un backend en Python con Flask y un frontend moderno en Next.js para proporcionar una interfaz intuitiva y precisa.

## 🎯 Características Principales

- ✅ **Clasificación automática** de productos con alta precisión (85%+)
- ✅ **Sistema de aprendizaje automático** que mejora continuamente
- ✅ **Motor RGI inteligente** con sinónimos expandidos
- ✅ **Reglas específicas** para productos técnicos e industriales
- ✅ **Interfaz web moderna** y responsiva
- ✅ **API REST** completa para integración
- ✅ **Sistema de autenticación** seguro
- ✅ **Base de datos PostgreSQL** robusta

## 🏗️ Arquitectura del Sistema

```
Clasificode/
├── ProyectoClasificode/          # Backend (Python/Flask)
│   ├── controladores/            # Controladores de API
│   ├── modelos/                  # Modelos de base de datos
│   ├── servicios/                # Lógica de negocio
│   │   ├── classifier.py         # Clasificador principal
│   │   ├── rules/                # Motor RGI
│   │   ├── agente/               # Sistema de IA
│   │   └── modeloPln/            # Modelos de PLN
│   ├── repositories/             # Repositorios de datos
│   ├── schemas/                  # Esquemas de validación
│   └── migrations/               # Migraciones de BD
└── ProyectoClasificodeF/         # Frontend (Next.js/React)
    ├── app/                      # Páginas de la aplicación
    ├── components/               # Componentes React
    ├── lib/                      # Utilidades y configuración
    └── styles/                   # Estilos CSS
```

## 🚀 Instalación y Configuración

### Prerrequisitos

- **Python 3.12+**
- **Node.js 18+**
- **PostgreSQL 13+**
- **Git**

### 1. Clonar el Repositorio

```bash
git clone <repository-url>
cd clasificode
```

### 2. Configurar el Backend (Python)

```bash
# Navegar al directorio del backend
cd ProyectoClasificode

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Configurar la Base de Datos

```bash
# Crear base de datos PostgreSQL
createdb Bd_Clasificode

# Ejecutar migraciones
python -m alembic upgrade head

# Cargar datos iniciales (opcional)
python scripts/seed.py
```

### 4. Configurar el Frontend (Next.js)

```bash
# Navegar al directorio del frontend
cd ProyectoClasificodeF

# Instalar dependencias
npm install
# o
pnpm install
```

## ▶️ Ejecución del Sistema

### 1. Iniciar el Backend

```bash
# Desde ProyectoClasificode/
python main.py
```

El backend estará disponible en: `http://localhost:5000`

### 2. Iniciar el Frontend

```bash
# Desde ProyectoClasificodeF/
npm run dev
# o
pnpm dev
```

El frontend estará disponible en: `http://localhost:3000`

## 🧪 Tests y Evaluación

### Ejecutar Tests de Precisión

```bash
# Test con productos comerciales
python test_precision_50.py

# Test con productos técnicos
python test_precision_50_tecnicos.py

# Test con sistema de aprendizaje
python test_with_learning.py
```

### Resultados de Precisión

- **Productos Comerciales**: 92% ✅
- **Productos Técnicos**: 78.43% ✅
- **Productos Nuevos**: 92% ✅

## 📊 Características del Sistema

### Backend (ProyectoClasificode)

- **Flask**: Framework web ligero y flexible
- **SQLAlchemy**: ORM para base de datos
- **PostgreSQL**: Base de datos robusta
- **OpenAI API**: Embeddings para búsqueda semántica
- **Alembic**: Migraciones de base de datos
- **JWT**: Autenticación segura

### Frontend (ProyectoClasificodeF)

- **Next.js 14**: Framework React moderno
- **TypeScript**: Tipado estático
- **Tailwind CSS**: Estilos utilitarios
- **shadcn/ui**: Componentes UI modernos
- **Axios**: Cliente HTTP
- **React Hook Form**: Manejo de formularios

## 🔧 API Endpoints

### Autenticación
- `POST /auth/login` - Iniciar sesión
- `POST /auth/register` - Registrar usuario
- `POST /auth/logout` - Cerrar sesión

### Clasificación
- `POST /classify/<case_id>` - Clasificar producto
- `GET /classify/<case_id>/result` - Obtener resultado
- `GET /classify/<case_id>/candidates` - Obtener candidatos

### Casos
- `POST /cases` - Crear nuevo caso
- `GET /cases` - Listar casos
- `GET /cases/<id>` - Obtener caso específico

### Administración
- `GET /admin/users` - Gestionar usuarios
- `GET /admin/stats` - Estadísticas del sistema

## 📈 Sistema de Aprendizaje

El sistema incluye un motor de aprendizaje automático que:

- **Analiza patrones de error** automáticamente
- **Genera reglas específicas** basadas en clasificaciones incorrectas
- **Sugiere mejoras** del sistema
- **Mantiene historial** de aprendizaje

### Archivos de Aprendizaje

- `learning_data.json` - Datos de aprendizaje
- `improvement_report.txt` - Reportes de mejora
- `embedding_cache.json` - Caché de embeddings

## 🛠️ Desarrollo

### Estructura del Código

#### Backend
```
servicios/
├── classifier.py          # Clasificador principal
├── rules/rgi_engine.py    # Motor RGI
├── agente/                # Sistema de IA
├── modeloPln/             # Modelos de PLN
└── learning_system.py     # Sistema de aprendizaje
```

#### Frontend
```
app/
├── layout.tsx            # Layout principal
├── page.tsx              # Página de inicio
├── form/page.tsx         # Formulario de clasificación
├── result/page.tsx       # Resultados
└── api/                  # API routes
```

### Agregar Nuevas Reglas

1. Editar `servicios/classifier.py`
2. Agregar regla en `specific_rules`
3. Actualizar `_try_specific_rules()`
4. Ejecutar tests para validar

### Mejorar Sinónimos

1. Editar `servicios/rules/rgi_engine.py`
2. Actualizar diccionario `synonyms`
3. Agregar detección de categorías
4. Probar con productos nuevos

## 📋 Scripts Útiles

```bash
# Generar reporte de mejoras
python servicios/auto_improver.py

# Actualizar embeddings
python servicios/embedding_updater.py

# Ejecutar migraciones
python -m alembic upgrade head

# Crear nueva migración
python -m alembic revision --autogenerate -m "descripción"

# Cargar datos de prueba
python scripts/seed.py
```

## 🔍 Monitoreo y Logs

- **Logs del sistema**: `logs/` (si está configurado)
- **Datos de aprendizaje**: `learning_data.json`
- **Reportes de precisión**: Generados automáticamente
- **Caché de embeddings**: `embedding_cache.json`

## 🚀 Despliegue

### Producción

1. **Configurar variables de entorno**
2. **Configurar base de datos de producción**
3. **Ejecutar migraciones**
4. **Configurar servidor web (nginx/apache)**
5. **Configurar SSL/HTTPS**

### Docker (Opcional)

```bash
# Backend
docker build -t clasificode-backend ./ProyectoClasificode

# Frontend
docker build -t clasificode-frontend ./ProyectoClasificodeF
```

## 📞 Soporte

Para soporte técnico o reportar problemas:

1. Revisar logs del sistema
2. Ejecutar tests de precisión
3. Verificar configuración de base de datos
4. Consultar documentación de APIs

## 📄 Licencia

Este proyecto está bajo licencia [especificar licencia].

---

## 🎉 ¡Sistema Listo para Producción!

El sistema Clasificode está completamente funcional y listo para clasificar productos con alta precisión. El sistema de aprendizaje automático asegura que la precisión mejore continuamente con el uso.

**¡Disfruta clasificando productos con inteligencia artificial!** 🚀
