# Clasificode - API de Clasificación de Códigos HS

Sistema de clasificación automática de códigos HS usando NLP y reglas de negocio.

## Estructura del Proyecto

```
ProyectoClasificode/
├── config/
│   └── config.json                 # Configuración de BD y JWT
├── controladores/                  # Controladores de la API
│   ├── __init__.py
│   ├── auth_controller.py         # Autenticación y autorización
│   ├── cases_controller.py        # Gestión de casos
│   ├── classify_controller.py     # Clasificación con NLP
│   ├── admin_controller.py        # Funciones administrativas
│   └── health_controller.py       # Endpoints de salud
├── modelos/                       # Modelos SQLAlchemy 2.x
│   ├── __init__.py
│   ├── base.py                    # Modelo base
│   ├── user.py                    # Usuarios (admin/auditor/operator)
│   ├── case.py                    # Casos legales
│   ├── candidate.py               # Candidatos de clasificación
│   ├── validation.py              # Validaciones de casos
│   ├── hs_item.py                 # Items del catálogo HS
│   ├── hs_note.py                 # Notas del catálogo HS
│   ├── rgi_rule.py                # Reglas RGI
│   ├── legal_source.py            # Fuentes legales
│   └── embedding.py               # Embeddings vectoriales (pgvector)
├── servicios/                     # Lógica de negocio
│   ├── __init__.py
│   ├── control_conexion.py        # Conexión a BD (reutilizado)
│   ├── token_service.py           # JWT (reutilizado)
│   ├── security.py                # Decoradores de seguridad
│   ├── repos.py                   # Repositorios tipados por entidad
│   ├── agente/
│   │   └── rule_engine.py         # Motor de reglas
│   └── modeloPln/
│       ├── nlp_service.py         # Servicios de NLP
│       ├── embedding_service.py   # Generación de embeddings
│       └── vector_index.py        # Índice vectorial
├── migrations/                    # Migraciones Alembic
│   ├── env.py
│   ├── alembic.ini
│   ├── script.py.mako
│   └── versions/
│       └── 0001_initial_migration.py  # Migración inicial con pgvector
├── scripts/                       # Scripts de utilidad
│   ├── seed.py                    # Poblar BD con datos iniciales
│   └── embed_hs_catalog.py        # Generar embeddings del catálogo HS
├── main.py                        # Aplicación principal
├── requirements.txt               # Dependencias
└── README.md                      # Este archivo
```

## Configuración

### Base de Datos

El proyecto usa PostgreSQL con pgvector para embeddings vectoriales:

```json
{
    "DatabaseProvider": "Postgres",
    "ConnectionStrings": {
        "Postgres": "postgresql+psycopg://clasificode:clasificode@127.0.0.1:5432/clasificode"
    },
    "Jwt": {
        "Key": "cambia_esto",
        "Issuer": "clasificode",
        "Audience": "clasificode"
    }
}
```

### Dependencias

Instalar las dependencias:

```bash
pip install -r requirements.txt
```

**Dependencias adicionales para NLP:**
```bash
# Para spaCy (opcional, fallback automático)
python -m spacy download es_core_news_sm

# Para modelos de HuggingFace (opcional)
pip install transformers torch
```

## Instalación y Configuración

1. **Crear base de datos PostgreSQL:**
   ```sql
   CREATE DATABASE clasificode;
   CREATE USER clasificode WITH PASSWORD 'clasificode';
   GRANT ALL PRIVILEGES ON DATABASE clasificode TO clasificode;
   ```

2. **Instalar extensión pgvector:**
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

3. **Ejecutar migraciones:**
   ```bash
   alembic upgrade head
   ```

4. **Poblar base de datos:**
   ```bash
   python scripts/seed.py
   ```

5. **Generar embeddings del catálogo HS:**
   ```bash
   python scripts/embed_hs_catalog.py --generate
   ```

6. **Configurar proveedor de embeddings:**
   - Editar `config/config.json`
   - Configurar `EMBED_PROVIDER` y `EMBED_MODEL`
   - Agregar API keys si es necesario

7. **Ejecutar la aplicación:**
   ```bash
   python main.py
   ```

## Modelos de Datos

### Usuarios (User)
- **Roles:** admin, auditor, operator
- **Campos:** id, email (UNIQUE), password_hash, name, role, is_active, created_at, updated_at

### Casos (Case)
- **Estados:** open, validated, rejected
- **Campos:** id, created_by (FK User), status, product_title, product_desc, attrs_json (JSONB), created_at, closed_at

### Candidatos (Candidate)
- **Campos:** id, case_id (FK Case), hs_code, title, confidence (0..1), rationale, legal_refs_json (JSONB), rank
- **Constraint:** UNIQUE(case_id, rank)

### Validaciones (Validation)
- **Campos:** id, case_id (FK Case), validator_id (FK User), final_hs_code, comment, created_at

### Items HS (HSItem)
- **Campos:** id, hs_code (UNIQUE), title, keywords, level, chapter, parent_code

### Notas HS (HSNote)
- **Scope:** SECTION, CHAPTER, HEADING, SUBHEADING
- **Campos:** id, scope, scope_code, note_number, text

### Reglas RGI (RGIRule)
- **Tipos:** RGI1, RGI2A, RGI2B, RGI3A, RGI3B, RGI3C, RGI4, RGI5A, RGI5B, RGI6
- **Campos:** id, rgi, description

### Fuentes Legales (LegalSource)
- **Tipos:** RGI, NOTA, RESOLUCION, MANUAL, OTRO
- **Campos:** id, source_type, ref_code, url, fetched_at, content_hash, summary

### Embeddings (Embedding)
- **Campos:** id, owner_type (hs_item|case), owner_id, provider, model, dim, vector (pgvector), text_norm
- **Constraint:** UNIQUE(owner_type, owner_id, provider, model)

## Endpoints de la API

### Autenticación
- `POST /auth/register` - Registrar nuevo usuario
- `POST /auth/login` - Iniciar sesión
- `POST /auth/logout` - Cerrar sesión
- `POST /auth/validate` - Validar token

### Casos
- `GET /cases` - Listar casos (con filtros: query, page, status)
- `POST /cases` - Crear caso
- `GET /cases/<id>` - Obtener caso específico
- `POST /cases/<id>/validate` - Validar caso (requiere rol auditor)
- `GET /cases/<id>/candidates` - Obtener candidatos del caso
- `POST /cases/<id>/candidates` - Agregar candidatos al caso

### Clasificación
- `POST /classify/<case_id>` - Clasificar caso (parámetro k para número de candidatos)
- `GET /explanations/<case_id>` - Obtener explicaciones de clasificación
- `POST /analyze` - Analizar texto sin clasificar

### Administración
- `GET /admin/params` - Obtener parámetros de configuración
- `POST /admin/params` - Actualizar parámetros de configuración
- `GET /admin/legal-sources` - Obtener fuentes legales
- `POST /admin/legal-sources` - Agregar fuente legal
- `POST /admin/embed-hs` - Recalcular embeddings del catálogo HS
- `GET /admin/stats` - Estadísticas del sistema
- `GET /admin/health` - Verificación de salud (admin)

### Salud
- `GET /health` - Verificación completa de salud
- `GET /health/simple` - Verificación simple (sin autenticación)
- `GET /health/ready` - Verificación de readiness
- `GET /health/live` - Verificación de liveness

## Características de Seguridad

- **Autenticación JWT:** Todos los endpoints protegidos requieren token válido
- **Autorización basada en roles:** admin, auditor, operator
- **CORS limitado:** Solo permite conexiones desde localhost:8080
- **Sin rutas CRUD genéricas:** Eliminadas por seguridad
- **Validación de entrada:** Todos los endpoints validan datos de entrada
- **Hashing de contraseñas:** bcrypt para almacenamiento seguro
- **Decoradores de seguridad:** require_auth, require_role, require_admin, require_auditor, require_operator
- **Respuestas JSON estandarizadas:** {code, message, details} para todos los endpoints
- **Sanitización de entrada:** Prevención de inyecciones
- **Validación de fortaleza de contraseñas:** Requisitos mínimos de seguridad

## Pipeline de Clasificación Completo

### 1. Procesamiento de Lenguaje Natural (NLP)
- **Normalización:** lowercase, espacios, limpieza básica
- **Lematización:** spaCy ES con fallback silencioso
- **Clasificación:** electronics, textiles, food, machinery, chemicals
- **Análisis de sentimientos:** positive, negative, neutral
- **Extracción de entidades:** materiales, marcas, medidas, países
- **Extracción de palabras clave:** TF-IDF mejorado
- **Términos técnicos:** códigos HS, medidas, materiales específicos
- **Complejidad del texto:** métricas de legibilidad

### 2. Motor de Reglas RGI
- **Reglas RGI1-RGI6:** Implementación completa de reglas de interpretación
- **Notas del Sistema Armonizado:** SECTION, CHAPTER, HEADING, SUBHEADING
- **Filtros de descarte:** palabras clave que indican exclusión
- **Bonos automáticos:** palabras clave que indican inclusión
- **Análisis de atributos:** material, origen, uso específico
- **Trazas detalladas:** registro de reglas aplicadas

### 3. Embeddings Vectoriales
- **Proveedores:** OpenAI, HuggingFace, Mock (desarrollo)
- **Modelos soportados:** text-embedding-ada-002, sentence-transformers
- **Dimensiones:** 384-3072 según modelo
- **Métricas:** coseno, L2, producto punto
- **Configuración:** desde config.json o variables de entorno

### 4. Índice Vectorial (pgvector)
- **Búsqueda KNN:** eficiente con IVFFLAT
- **Métricas:** cosine, L2, dot product
- **Upsert:** inserción/actualización automática
- **Metadatos:** JSON flexible para información adicional
- **Estadísticas:** monitoreo de uso y rendimiento

### 5. Re-ranking Híbrido
- **Score Semántico:** 1/(1+distance) de embeddings
- **Score Léxico:** RapidFuzz contra título/keywords
- **Score de Reglas:** bonos/penas de reglas RGI
- **Combinación:** pesos configurables (semantic: 0.4, lexical: 0.3, rules: 0.3)
- **Rationale:** explicaciones automáticas del ranking
- **Referencias legales:** JSON con detalles de clasificación

## Repositorios Tipados

El sistema incluye repositorios específicos para cada entidad:

- **UserRepository:** Gestión de usuarios y autenticación
- **CaseRepository:** Gestión de casos y validaciones
- **CandidateRepository:** Gestión de candidatos de clasificación
- **ValidationRepository:** Gestión de validaciones
- **HSItemRepository:** Búsqueda en catálogo HS
- **EmbeddingRepository:** Gestión de embeddings vectoriales
- **RGIRuleRepository:** Gestión de reglas RGI
- **LegalSourceRepository:** Gestión de fuentes legales

## Scripts de Utilidad

### seed.py
Pobla la base de datos con:
- Usuarios iniciales (admin, auditor, operator) con contraseñas hasheadas
- Casos de ejemplo con atributos JSON
- Reglas RGI completas (RGI1 a RGI6)
- Fuentes legales de diferentes tipos
- Items HS de ejemplo con códigos reales
- Candidatos de clasificación para casos de ejemplo

### embed_hs_catalog.py
- `--generate`: Genera embeddings para el catálogo HS
- `--search "texto"`: Busca códigos HS similares
- `--top-k N`: Número de resultados (default: 5)

## Desarrollo

### Crear nueva migración:
```bash
alembic revision --autogenerate -m "Descripción del cambio"
alembic upgrade head
```

### Ejecutar tests:
```bash
# Por implementar
```

### Formatear código:
```bash
# Por implementar
```

## Índices de Base de Datos

### Índices B-Tree
- Usuarios: email, role, is_active
- Casos: status, created_by, created_at
- Candidatos: case_id, hs_code, confidence, rank
- Validaciones: case_id, validator_id
- Items HS: hs_code, chapter, level, parent_code
- Notas HS: scope, scope_code
- Fuentes legales: source_type, ref_code
- Reglas RGI: rgi

### Índices GIN
- Casos: attrs_json (JSONB)

### Índices Vectoriales (pgvector)
- Embeddings: vector (cosine y L2 con IVFFLAT)

## Notas Importantes

1. **Seguridad:** Cambiar la clave JWT en producción
2. **Base de datos:** Usar credenciales seguras en producción
3. **pgvector:** Asegurar que la extensión esté instalada en PostgreSQL
4. **CORS:** Configurar orígenes permitidos según el entorno
5. **Logs:** Implementar logging apropiado para producción
6. **Tests:** Agregar tests unitarios y de integración
7. **Contraseñas:** Las contraseñas se hashean con bcrypt automáticamente
8. **Roles:** Sistema de roles jerárquico (admin > auditor > operator)
9. **Respuestas:** Todos los endpoints devuelven JSON estandarizado
10. **Migración:** Usar `main.py` en lugar de `app.py` (legacy)

## Licencia

[Especificar licencia]
