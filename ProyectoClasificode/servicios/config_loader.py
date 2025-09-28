import os
import json
from typing import Any, Dict, Optional


def load_config() -> Dict[str, Any]:
    """Carga la configuración de la app.
    Orden de búsqueda:
    1) config/config.json
    2) configuracion/config.json (compatibilidad)
    3) Variables de entorno mínimas
    """
    base_dir = os.path.dirname(os.path.dirname(__file__))
    candidates = [
        os.path.join(base_dir, 'config', 'config.json'),
        os.path.join(base_dir, 'configuracion', 'config.json'),
    ]

    last_err: Optional[Exception] = None
    for path in candidates:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            last_err = e
            continue

    # Fallback a variables de entorno mínimas
    cfg = {
        'DatabaseProvider': os.getenv('DATABASE_PROVIDER', 'Postgres'),
        'ConnectionStrings': {
            'Postgres': os.getenv('POSTGRES_URL', 'postgresql+psycopg://postgres:postgres@127.0.0.1:5432/postgres')
        },
        'Jwt': {
            'Key': os.getenv('JWT_KEY', ''),
            'Issuer': os.getenv('JWT_ISSUER', 'clasificode'),
            'Audience': os.getenv('JWT_AUDIENCE', 'clasificode')
        },
        'EMBED_PROVIDER': os.getenv('EMBED_PROVIDER', 'huggingface'),
        'EMBED_MODEL': os.getenv('EMBED_MODEL', 'sentence-transformers/all-MiniLM-L6-v2'),
        'Host': os.getenv('HOST', '127.0.0.1'),
        'Port': int(os.getenv('PORT', '5000')),
        'Debug': os.getenv('DEBUG', 'false').lower() == 'true',
    }

    if not cfg['Jwt']['Key']:
        # Señalar claramente que no hay archivo ni JWT_KEY
        raise FileNotFoundError(
            f"No se pudo cargar configuración desde {candidates} y no está definida JWT_KEY en el entorno"
        )
    return cfg
