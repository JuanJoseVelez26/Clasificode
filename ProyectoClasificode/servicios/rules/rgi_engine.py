"""
Motor de Reglas Generales de Interpretación (RGI) del Arancel

Implementación funcional (funciones puras) que aplican RGI 1, 2, 3 y 6
para filtrar y decidir un código HS6. Mantiene trazabilidad con referencias
legales: rgi_id, note_id, legal_source_id.

Citas (Decreto 1881 de 2021, Arancel de Aduanas 2022-2026):
- RGI 1: "Los títulos de las Secciones, Capítulos y Subcapítulos no tienen
  valor legal; la clasificación de las mercancías se determinará legalmente
  por los textos de las partidas y de las Notas de Sección o de Capítulo y,
  si no son contrarias a los textos de dichas partidas y Notas, de acuerdo
  con las reglas siguientes."
- RGI 2(a): Incompletos/desarmados.
- RGI 2(b): Mezclas y mercancías compuestas.
- RGI 3(a): La partida más específica tendrá prioridad sobre las partidas de
  alcance más genérico.
- RGI 3(b): Carácter esencial de los conjuntos o mezclas.
- RGI 3(c): Si no es posible la clasificación por 3(a) o 3(b), se clasificará
  por la última partida por orden de numeración.
- RGI 6: La clasificación en subpartidas está determinada legalmente por los
  textos de estas subpartidas y de las Notas de subpartida y, mutatis mutandis,
  por las reglas anteriores, considerándose únicamente subpartidas del mismo
  nivel.
"""
from __future__ import annotations
from typing import List, Dict, Any, Tuple

from ..control_conexion import ControlConexion

PRIORITY_KEYWORD_RULES = [
    {
        "category": "textiles",
        "hs_code": "610910",
        "title": "Camisetas de algodón",
        "keywords": ["camiseta", "playera", "remera", "t shirt", "t-shirt", "tshirt"],
        "feature_match": ["ropa_textil", "vestir"]
    },
    {
        "category": "textiles",
        "hs_code": "620342",
        "title": "Pantalones vaqueros",
        "keywords": ["pantalon", "pantalón", "jean", "denim", "vaquero"],
        "feature_match": ["ropa_textil"]
    },
    {
        "category": "calzado",
        "hs_code": "640219",
        "title": "Calzado deportivo",
        "keywords": ["zapato", "zapatos", "tenis", "calzado", "zapatilla"],
        "feature_match": ["calzado"]
    },
    {
        "category": "perfumes",
        "hs_code": "330300",
        "title": "Perfumes y aguas de tocador",
        "keywords": ["perfume", "fragancia", "eau de parfum", "eau de toilette", "colonia"],
        "feature_match": ["perfume_cosmetico", "cuidado_personal"]
    },
    {
        "category": "papeleria",
        "hs_code": "482010",
        "title": "Cuadernos y libretas",
        "keywords": ["cuaderno", "libreta", "notebook", "agenda"],
        "feature_match": ["papeleria", "escritura"]
    },
    {
        "category": "papeleria",
        "hs_code": "960910",
        "title": "Lápices de grafito o colores",
        "keywords": ["lapiz", "lápiz", "lapices", "lápices", "colores"],
    },
    {
        "category": "papeleria",
        "hs_code": "960810",
        "title": "Plumas y bolígrafos",
        "keywords": ["boligrafo", "bolígrafo", "pluma", "esfero", "pen"],
    },
    {
        "category": "alimentos",
        "hs_code": "090121",
        "title": "Café tostado",
        "keywords": ["cafe", "café", "arábica", "robusta"],
        "feature_match": ["alimento_bebida", "consumo_humano"]
    },
    {
        "category": "alimentos",
        "hs_code": "150910",
        "title": "Aceite de oliva",
        "keywords": ["aceite de oliva", "extra virgen", "oliva"],
        "feature_match": ["alimento_bebida"]
    },
    {
        "category": "alimentos",
        "hs_code": "180632",
        "title": "Chocolate en tabletas",
        "keywords": ["chocolate", "cacao 70", "chocolate negro"],
    },
    {
        "category": "alimentos",
        "hs_code": "200799",
        "title": "Mermeladas",
        "keywords": ["mermelada", "confitura"],
    },
    {
        "category": "alimentos",
        "hs_code": "220300",
        "title": "Cerveza",
        "keywords": ["cerveza", "ipa", "lager", "ale"],
        "feature_match": ["bebidas"]
    },
    {
        "category": "alimentos",
        "hs_code": "220421",
        "title": "Vinos",
        "keywords": ["vino", "reserva", "tempranillo", "cabernet"],
    },
    {
        "category": "alimentos",
        "hs_code": "210310",
        "title": "Salsa de soja",
        "keywords": ["salsa de soja", "soya", "soy sauce"],
    },
    {
        "category": "alimentos",
        "hs_code": "220900",
        "title": "Vinagre",
        "keywords": ["vinagre", "balsamico", "balsámico"],
    },
    {
        "category": "medico",
        "hs_code": "902519",
        "title": "Termómetros digitales",
        "keywords": ["termometro", "termómetro", "infrarrojo"],
        "feature_match": ["producto_medico", "medicion_medica"]
    },
    {
        "category": "medico",
        "hs_code": "901890",
        "title": "Tensiómetros u otros aparatos",
        "keywords": ["tensiometro", "tensiómetro", "oximetro", "oxímetro"],
    },
    {
        "category": "medico",
        "hs_code": "901831",
        "title": "Jeringas",
        "keywords": ["jeringa", "jeringuilla"],
    },
    {
        "category": "medico",
        "hs_code": "630790",
        "title": "Mascarillas",
        "keywords": ["mascarilla", "tapabocas", "n95"],
    },
    {
        "category": "automotriz",
        "hs_code": "842123",
        "title": "Filtros de aceite",
        "keywords": ["filtro de aceite", "filtro motor"],
        "feature_match": ["repuesto_automotriz", "automotriz"]
    },
    {
        "category": "automotriz",
        "hs_code": "870830",
        "title": "Frenos y sus partes",
        "keywords": ["pastillas de freno", "freno disco"],
    },
    {
        "category": "automotriz",
        "hs_code": "851110",
        "title": "Bujías",
        "keywords": ["bujia", "bujía"],
    },
    {
        "category": "automotriz",
        "hs_code": "841330",
        "title": "Bombas para combustibles",
        "keywords": ["bomba de combustible", "bomba gasolina"],
    },
    {
        "category": "higiene",
        "hs_code": "330610",
        "title": "Preparaciones dentífricas",
        "keywords": ["pasta dental", "crema dental", "dentifrico"],
        "feature_match": ["higiene_personal"],
    },
    {
        "category": "higiene",
        "hs_code": "960321",
        "title": "Cepillos dentales",
        "keywords": ["cepillo de dientes", "cepillo dental"],
        "feature_match": ["higiene_personal"],
    },
    {
        "category": "limpieza",
        "hs_code": "340130",
        "title": "Preparaciones orgánicas para higiene",
        "keywords": ["jabon antibacterial", "jabón liquido"],
        "feature_match": ["limpieza_hogar"],
    },
    {
        "category": "limpieza",
        "hs_code": "340220",
        "title": "Detergentes y preparaciones",
        "keywords": ["detergente en polvo", "detergente ropa"],
        "feature_match": ["limpieza_hogar"],
    },
    {
        "category": "cocina",
        "hs_code": "732393",
        "title": "Artículos de cocina de acero inoxidable",
        "keywords": ["olla", "termo", "cacerola"],
        "feature_match": ["producto_cocina_menaje"],
    },
    {
        "category": "cocina",
        "hs_code": "761510",
        "title": "Artículos de aluminio para cocina",
        "keywords": ["sarten", "bandeja horneado"],
        "feature_match": ["producto_cocina_menaje"],
    },
    {
        "category": "cocina",
        "hs_code": "691110",
        "title": "Platos de cerámica",
        "keywords": ["plato de ceramica", "plato cerámica"],
    },
    {
        "category": "cocina",
        "hs_code": "701349",
        "title": "Vasos de vidrio",
        "keywords": ["vaso de vidrio", "vaso templado"],
    },
    {
        "category": "herramientas",
        "hs_code": "821192",
        "title": "Cuchillos de cocina",
        "keywords": ["cuchillo de cocina", "cuchillo chef"],
    },
    {
        "category": "herramientas",
        "hs_code": "821300",
        "title": "Tijeras",
        "keywords": ["tijeras multiusos", "tijera multiusos"],
    },
    {
        "category": "hogar",
        "hs_code": "392410",
        "title": "Artículos de plástico para el hogar",
        "keywords": ["esponja cocina", "espátula silicona"],
    },
    {
        "category": "hogar",
        "hs_code": "392310",
        "title": "Cajas y contenedores plásticos",
        "keywords": ["caja plastica", "organizador plastico"],
    },
    {
        "category": "deportes",
        "hs_code": "950662",
        "title": "Balones deportivos",
        "keywords": ["balon baloncesto", "balón baloncesto"],
    },
    {
        "category": "deportes",
        "hs_code": "560749",
        "title": "Cuerdas de fibras textiles",
        "keywords": ["cuerda de salto", "soga de salto"],
    },
    {
        "category": "iluminacion",
        "hs_code": "851310",
        "title": "Linternas eléctricas",
        "keywords": ["linterna", "linterna led"],
    },
    {
        "category": "iluminacion",
        "hs_code": "854370",
        "title": "Dispositivos LED",
        "keywords": ["bombillo led", "bombilla led"],
    },
    {
        "category": "banio",
        "hs_code": "392490",
        "title": "Cortinas y artículos de plástico para baño",
        "keywords": ["cortina de baño", "cortina baño"],
    },
    {
        "category": "banio",
        "hs_code": "570500",
        "title": "Tapetes de baño",
        "keywords": ["tapete baño", "alfombra baño"],
    },
    {
        "category": "accesorios",
        "hs_code": "660191",
        "title": "Paraguas y sombrillas",
        "keywords": ["paraguas", "sombrilla"],
    },
    {
        "category": "accesorios",
        "hs_code": "420292",
        "title": "Mochilas",
        "keywords": ["mochila", "bolso deportivo"],
    },
    {
        "category": "accesorios",
        "hs_code": "420321",
        "title": "Cinturones",
        "keywords": ["cinturon", "cinturón"],
    },
    {
        "category": "accesorios",
        "hs_code": "711711",
        "title": "Bisutería de metal común",
        "keywords": ["pulsera acero", "brazalete inox"],
    },
    {
        "category": "decoracion",
        "hs_code": "701399",
        "title": "Artículos de vidrio para decoración",
        "keywords": ["jarron", "florero"],
    },
    {
        "category": "decoracion",
        "hs_code": "441400",
        "title": "Marcos y portarretratos de madera",
        "keywords": ["portarretratos", "marco foto"],
    },
    {
        "category": "pinturas",
        "hs_code": "320820",
        "title": "Pinturas y barnices en aerosol",
        "keywords": ["pintura aerosol", "spray pintura"],
    },
    {
        "category": "adhesivos",
        "hs_code": "350610",
        "title": "Colas y adhesivos",
        "keywords": ["adhesivo instantaneo", "pegamento escolar", "pegamento barra"],
        "feature_match": ["adhesivo_quimico"],
    },
    {
        "category": "oficina",
        "hs_code": "391910",
        "title": "Cintas adhesivas",
        "keywords": ["cinta adhesiva transparente", "cinta cristal"],
    },
    {
        "category": "oficina",
        "hs_code": "847290",
        "title": "Grapadoras y perforadoras",
        "keywords": ["grapadora", "perforadora"],
        "feature_match": ["papeleria_avanzada"],
    },
    {
        "category": "oficina",
        "hs_code": "482030",
        "title": "Carpetas de plástico",
        "keywords": ["carpeta plastica"],
    },
    {
        "category": "precision",
        "hs_code": "901380",
        "title": "Instrumentos ópticos simples",
        "keywords": ["lupa"],
    },
    {
        "category": "iluminacion",
        "hs_code": "940520",
        "title": "Lámparas de escritorio",
        "keywords": ["lampara escritorio", "lámpara mesa"],
    },
    {
        "category": "muebles",
        "hs_code": "940370",
        "title": "Mesas de plástico",
        "keywords": ["mesa plegable", "mesa plastica"],
    },
    {
        "category": "muebles",
        "hs_code": "940161",
        "title": "Sillas de madera",
        "keywords": ["silla comedor", "silla madera"],
    },
    {
        "category": "herramientas",
        "hs_code": "732690",
        "title": "Cajas de herramientas",
        "keywords": ["caja herramientas"],
    },
    {
        "category": "herramientas",
        "hs_code": "820412",
        "title": "Llaves ajustables",
        "keywords": ["llave inglesa", "llave ajustable"],
    },
    {
        "category": "construccion",
        "hs_code": "252329",
        "title": "Cemento Portland",
        "keywords": ["cemento portland", "cemento tipo i"],
        "feature_match": ["construccion"],
    },
    {
        "category": "construccion",
        "hs_code": "690410",
        "title": "Ladrillos cerámicos",
        "keywords": ["ladrillo ceramico", "ladrillo hueco"],
    },
    {
        "category": "herramientas",
        "hs_code": "846721",
        "title": "Taladros inalámbricos",
        "keywords": ["taladro inalambrico", "taladro inalámbrico"],
    },
    {
        "category": "herramientas",
        "hs_code": "820520",
        "title": "Martillos de carpintería",
        "keywords": ["martillo carpintero"],
    },
    {
        "category": "herramientas",
        "hs_code": "820540",
        "title": "Destornilladores",
        "keywords": ["destornillador phillips", "destornillador philips"],
    },
    {
        "category": "herramientas",
        "hs_code": "901780",
        "title": "Instrumentos de medida manual",
        "keywords": ["cinta metrica", "cinta métrica"],
    },
    {
        "category": "maquinaria",
        "hs_code": "850152",
        "title": "Motores eléctricos trifásicos",
        "keywords": ["motor electrico", "motor eléctrico"],
        "feature_match": ["maquinaria_industrial"],
    },
    {
        "category": "maquinaria",
        "hs_code": "848180",
        "title": "Válvulas de compuerta",
        "keywords": ["valvula compuerta", "válvula compuerta"],
        "feature_match": ["maquinaria_industrial"],
    },
    {
        "category": "maquinaria",
        "hs_code": "854449",
        "title": "Cables eléctricos aislados",
        "keywords": ["cable electrico", "cable eléctrico"],
        "feature_match": ["maquinaria_industrial"],
    },
    {
        "category": "maquinaria",
        "hs_code": "850421",
        "title": "Transformadores de distribución",
        "keywords": ["transformador distribucion", "transformador distribución"],
        "feature_match": ["maquinaria_industrial"],
    },
    {
        "category": "vehiculos",
        "hs_code": "870380",
        "title": "Automóviles eléctricos",
        "keywords": ["automovil electrico", "vehiculo electrico"],
    },
    {
        "category": "vehiculos",
        "hs_code": "871150",
        "title": "Motocicletas de cilindrada intermedia",
        "keywords": ["motocicleta 250cc", "moto 250cc"],
    },
    {
        "category": "electrodomesticos",
        "hs_code": "841810",
        "title": "Refrigeradores y congeladores",
        "keywords": ["refrigerador", "nevera", "frigorifico"],
        "feature_match": ["electrodomestico"],
    },
    {
        "category": "electrodomesticos",
        "hs_code": "845020",
        "title": "Lavadoras automáticas",
        "keywords": ["lavadora", "lavarropas"],
        "feature_match": ["electrodomestico"],
    },
    {
        "category": "electrodomesticos",
        "hs_code": "851650",
        "title": "Hornos microondas",
        "keywords": ["microondas"],
        "feature_match": ["electrodomestico"],
    },
    {
        "category": "electrodomesticos",
        "hs_code": "850910",
        "title": "Aspiradoras",
        "keywords": ["aspiradora"],
        "feature_match": ["electrodomestico"],
    },
    {
        "category": "electrodomesticos",
        "hs_code": "841510",
        "title": "Aires acondicionados",
        "keywords": ["aire acondicionado", "split"],
        "feature_match": ["electrodomestico"],
    },
    {
        "category": "electrodomesticos",
        "hs_code": "850940",
        "title": "Licuadoras y batidoras",
        "keywords": ["licuadora", "batidora"],
        "feature_match": ["electrodomestico", "producto_cocina_menaje"],
    },
    {
        "category": "electrodomesticos",
        "hs_code": "851640",
        "title": "Planchas eléctricas",
        "keywords": ["plancha de vapor", "plancha ropa"],
        "feature_match": ["electrodomestico"],
    },
    {
        "category": "electrodomesticos",
        "hs_code": "841451",
        "title": "Ventiladores",
        "keywords": ["ventilador de techo", "ventilador"],
    },
    {
        "category": "electrodomesticos",
        "hs_code": "842139",
        "title": "Purificadores de aire",
        "keywords": ["purificador de aire", "purificador hepa"],
    },
]

# Tipos simples
Candidate = Dict[str, Any]  # {'hs_code': 'XXXX.XX.XX', 'title': str, 'score': float, 'meta': {...}}
TraceStep = Dict[str, Any]  # {'rgi': 'RGI1', 'decision': str, 'affected': [...], 'legal_refs': {...}}


# Utilidades ---------------------------------------------------------------
def _clean_hs(code: str) -> str:
    if not code:
        return ''
    # Normaliza a formato HS con puntos y garantiza sólo dígitos
    keep = [c for c in code if c.isdigit()]
    s = ''.join(keep)
    # Inserta puntos 2-2-2 (HS6) o mantiene puntos existentes si ya viene con 8/10
    if len(s) >= 6:
        return f"{s[0:2]}.{s[2:4]}.{s[4:6]}"
    if len(s) == 4:
        return f"{s[0:2]}.{s[2:4]}"
    return s


def _hs_chapter(code: str) -> str:
    c = _clean_hs(code)
    return c[0:2] if len(c) >= 2 else ''


def _hs_heading(code: str) -> str:
    c = _clean_hs(code)
    return c[0:2] + c[3:5] if len(c) >= 5 else ''  # e.g., '84' + '71' -> '8471'


def _hs6(code: str) -> str:
    c = _clean_hs(code)
    return c[0:2] + c[3:5] + c[6:8] if len(c) >= 8 else ''  # '847130' -> '847130'


def _fetch_df(cc: ControlConexion, query: str, params: Tuple = ()):
    try:
        return cc.ejecutar_consulta_sql(query, params)
    except Exception:
        # Tolerante a ausencia de tablas durante desarrollo
        import pandas as pd
        return pd.DataFrame()


def _priority_candidates_from_text(text: str, features: Dict[str, Any]) -> List[Candidate]:
    """Genera candidatos prioritarios basados en palabras clave críticas detectadas en los tests."""
    matches: List[Candidate] = []
    seen: set[str] = set()
    text_lower = (text or '').lower()
    features = features or {}
    tipo_bien = features.get('tipo_de_bien')
    uso_principal = features.get('uso_principal')

    def add_candidate(hs_code: str, title: str, category: str, keywords: List[str] | None = None):
        hs = _clean_hs(hs_code)
        if hs in seen:
            return
        seen.add(hs)
        matches.append({
            'hs_code': hs,
            'title': title,
            'score': 1.05,
            'meta': {
                'priority_rule': True,
                'category': category,
                'keywords': keywords or []
            }
        })

    if 'cafe' in text_lower:
        if features.get('es_instantaneo'):
            add_candidate('210111', 'Preparaciones a base de café instantáneo', 'alimentos', ['cafe', 'instantaneo'])
        else:
            add_candidate('090121', 'Café tostado', 'alimentos', ['cafe'])
    has_plain_te = any(token in text_lower for token in [' te ', ' te,', ' te.', ' té ', ' té,', ' té.'])
    starts_te = text_lower.startswith('te ') or text_lower.startswith('té ')
    if (has_plain_te or starts_te) and 'tecnologia' not in text_lower and 'tecnología' not in text_lower:
        if 'negro' in text_lower or 'earl grey' in text_lower:
            if features.get('es_instantaneo') or 'instant' in text_lower:
                add_candidate('210120', 'Preparaciones instantáneas de té', 'alimentos', ['te', 'instantaneo'])
            else:
                add_candidate('090240', 'Té negro', 'alimentos', ['te', 'negro'])
        elif features.get('es_instantaneo') or 'instant' in text_lower or 'soluble' in text_lower:
            add_candidate('210120', 'Preparaciones a base de té o mate', 'alimentos', ['te', 'instantaneo'])
        else:
            add_candidate('090220', 'Té verde', 'alimentos', ['te'])
    if 'infusion' in text_lower or 'infusión' in text_lower:
        if 'instant' in text_lower or features.get('es_instantaneo'):
            add_candidate('210120', 'Preparaciones instantáneas de infusiones', 'alimentos', ['infusion'])
        else:
            add_candidate('090220', 'Infusiones naturales', 'alimentos', ['infusion'])
    if 'salsa de soja' in text_lower or 'salsa soja' in text_lower or 'soya' in text_lower:
        add_candidate('210310', 'Salsa de soja', 'alimentos', ['salsa', 'soja'])
    if 'vinagre' in text_lower:
        add_candidate('220900', 'Vinagre y sucedáneos', 'alimentos', ['vinagre'])
    if 'mermelada' in text_lower or 'conserva de fruta' in text_lower:
        add_candidate('200799', 'Mermeladas', 'alimentos', ['mermelada'])
    if 'miel' in text_lower:
        add_candidate('040900', 'Miel natural', 'alimentos', ['miel'])
    if features.get('es_semilla'):
        add_candidate('120930', 'Semillas para siembra', 'agricola', ['semilla'])
    if features.get('es_fertilizante'):
        add_candidate('310520', 'Fertilizante NPK', 'agricola', ['fertilizante'])
    if features.get('es_bebida_listo_consumo'):
        add_candidate('220300', 'Bebidas fermentadas', 'alimentos', ['bebida'])

    for rule in PRIORITY_KEYWORD_RULES:
        keywords = rule.get('keywords', [])
        feature_match = rule.get('feature_match', [])
        kw_hit = any(kw in text_lower for kw in keywords)
        feature_hit = tipo_bien in feature_match or uso_principal in feature_match if feature_match else False

        if not (kw_hit or feature_hit):
            continue

        hs = _clean_hs(rule['hs_code'])
        if hs in seen:
            continue
        seen.add(hs)

        matches.append({
            'hs_code': hs,
            'title': rule.get('title') or f"Regla prioritaria {hs}",
            'score': 1.05,
            'meta': {
                'priority_rule': True,
                'category': rule.get('category'),
                'keywords': [kw for kw in keywords if kw in text_lower],
            }
        })

    return matches


def _fetch_rgi_map(cc: ControlConexion) -> Dict[str, int]:
    """Devuelve un mapa {'RGI1': id, 'RGI2A': id, ...} si existen."""
    df = _fetch_df(cc, "SELECT id, rgi FROM rgi_rules")
    mapping: Dict[str, int] = {}
    if not df.empty:
        for _, r in df.iterrows():
            mapping[str(r['rgi']).upper()] = int(r['id'])
    return mapping


def _keyword_candidates(cc: ControlConexion, text: str, limit: int = 50, features: Dict[str, Any] = None) -> List[Candidate]:
    """
    Búsqueda mejorada por keywords que maneja múltiples términos, sinónimos y validación contextual.
    
    Args:
        cc: Controlador de conexión a la base de datos
        text: Texto del producto a clasificar
        limit: Límite de candidatos a retornar
        features: Características extraídas del producto para validación contextual
        
    Returns:
        Lista de candidatos HS con scores mejorados por validación contextual
    """
    text = (text or '').strip().lower()
    if not text:
        return []
    
    # Dividir el texto en palabras individuales (palabras de más de 2 caracteres)
    words = [word.strip() for word in text.split() if len(word.strip()) > 2]
    
    if not words:
        return []
    
    # Mapeo de sinónimos comunes para mejorar la búsqueda (expandido)
    synonyms = {
        # Animales
        'ternero': ['bovino', 'ganado', 'vaca', 'toro', 'animal', 'bovinos', 'terneros', 'bovino', 'vivo', 'cría'],
        'vivo': ['animal', 'ganado', 'bovino', 'vivos', 'animales', 'vivo'],
        'cerdo': ['porcino', 'cochino', 'marrano', 'chancho', 'cerdo'],
        'pollo': ['ave', 'gallina', 'gallinácea', 'pollo'],
        'pescado': ['pez', 'marisco', 'crustáceo', 'molusco', 'pescado'],
        
        # Textiles y ropa
        'camiseta': ['camisa', 'prenda', 'vestido', 'ropa', 'textil', 'playera', 'remera', 'tshirt', 't shirt', 'camiseta'],
        'algodon': ['algodón', 'textil', 'fibra', 'tela', 'algodon', '100%'],
        'chaqueta': ['abrigo', 'parka', 'anorak', 'cazadora', 'impermeable', 'sobretodo', 'saco', 'chaqueta', 'cuero', 'leather'],
        'plumas': ['pluma', 'relleno de plumas', 'acolchado', 'plumas'],
        'pantalon': ['pantalón', 'vaquero', 'jean', 'mezclilla', 'denim', 'pantalon'],
        'zapatos': ['calzado', 'tenis', 'zapatillas', 'zapatos', 'deportivo', 'botin', 'bota', 'sandalia'],
        'suela': ['piso', 'base', 'planta', 'suela'],
        'malla': ['textil', 'tejido', 'red', 'transpirable', 'malla'],
        'gorra': ['sombrero', 'casquete', 'boina', 'gorra'],
        'guantes': ['manos', 'protección', 'cubrir', 'guantes'],
        'bufanda': ['escarf', 'chal', 'bufanda'],
        'cinturon': ['cinturón', 'correa', 'cinturon'],
        'vestido': ['vestido', 'dress', 'prenda', 'verano', 'summer', 'poliéster', 'poliester'],
        
        # Electrónicos y computación
        'computadora': ['ordenador', 'pc', 'computador', 'equipo', 'computadora', 'laptop', 'notebook', 'desktop', 'escritorio'],
        'portatil': ['portátil', 'laptop', 'notebook', 'móvil', 'portatil', 'macbook', 'dell', 'hp', 'lenovo', 'asus', 'acer'],
        'telefono': ['teléfono', 'móvil', 'celular', 'smartphone', 'telefono', 'iphone', 'samsung', 'huawei', 'xiaomi', 'android'],
        'mouse': ['ratón', 'mouse', 'periférico', 'dispositivo', 'gaming', 'óptico', 'inalámbrico', 'dpi'],
        'gaming': ['juegos', 'gaming', 'gamer', 'videojuegos', 'entretenimiento'],
        'teclado': ['keyboard', 'teclado', 'periférico', 'dispositivo', 'gaming'],
        'auriculares': ['headphones', 'auriculares', 'audífonos', 'cascos', 'gaming', 'bluetooth'],
        'monitor': ['pantalla', 'monitor', 'display', 'gaming', 'pantalla', 'lcd', 'led', 'ips'],
        'webcam': ['cámara', 'webcam', 'cámara web', 'videoconferencia'],
        'microfono': ['micrófono', 'microphone', 'mic', 'grabación'],
        'altavoces': ['speakers', 'altavoces', 'parlantes', 'sonido', 'audio', 'bluetooth', 'portátil', 'portatil'],
        'parlante': ['speaker', 'altavoz', 'parlante', 'sonido', 'audio', 'bluetooth', 'portátil', 'portatil'],
        'impresora': ['printer', 'impresora', 'tinta', 'láser'],
        'escanner': ['scanner', 'escáner', 'digitalización', 'escanear'],
        'tablet': ['tableta', 'tablet', 'ipad', 'android'],
        'smartwatch': ['reloj inteligente', 'smartwatch', 'wearable'],
        'drone': ['dron', 'drone', 'aeronave', 'vuelo'],
        'bateria': ['batería', 'battery', 'pila', 'energía', 'power'],
        
        # Productos adicionales comunes
        'cafe': ['café', 'coffee', 'grano', 'tostado', 'molido', 'colombia', 'brasil'],
        'chocolate': ['cacao', 'cocoa', 'hershey', 'nestle', 'ferrero'],
        'zapato': ['zapatos', 'zapatilla', 'zapatillas', 'tenis', 'sneakers', 'calzado', 'shoe', 'shoes'],
        'carro': ['auto', 'coche', 'vehiculo', 'vehículo', 'automovil', 'automóvil', 'car', 'vehicle'],
        'moto': ['motocicleta', 'motorcycle', 'scooter', 'moto'],
        'bici': ['bicicleta', 'bicycle', 'bike', 'bici'],
        'mesa': ['table', 'mesa', 'escritorio', 'desk'],
        'silla': ['chair', 'silla', 'asiento', 'seat'],
        'cama': ['bed', 'cama', 'colchon', 'colchón', 'mattress'],
        'herramienta': ['tool', 'herramienta', 'taladro', 'martillo', 'destornillador', 'llave', 'cuchillo'],
        'juguete': ['toy', 'juguete', 'juego', 'game', 'muñeca', 'pelota', 'balón'],
        'arroz': ['rice', 'arroz', 'grano'],
        'azucar': ['sugar', 'azúcar', 'azucar', 'dulce'],
        'aceite': ['oil', 'aceite', 'oliva', 'girasol'],
        'leche': ['milk', 'leche', 'lacteo', 'lácteo'],
        'pan': ['bread', 'pan', 'hogaza', 'baguette'],
        'cargador': ['charger', 'cargador', 'carga', 'energía', 'power'],
        'cable': ['cable', 'wire', 'conexión', 'usb', 'hdmi', 'auxiliar', 'aux'],
        'adaptador': ['adapter', 'adaptador', 'conversor', 'conexión'],
        
        # Vehículos
        'automovil': ['automóvil', 'carro', 'vehículo', 'coche', 'automovil'],
        'motocicleta': ['moto', 'motociclo', 'vehículo', 'motocicleta'],
        'bicicleta': ['bici', 'ciclo', 'vehículo', 'bicicleta'],
        'neumatico': ['neumático', 'llanta', 'tire', 'neumatico'],
        'faro': ['luz', 'farola', 'led', 'faro'],
        'camion': ['camión', 'truck', 'vehículo pesado', 'camion'],
        'bus': ['autobús', 'ómnibus', 'colectivo', 'bus'],
        
        # Electrodomésticos
        'refrigerador': ['nevera', 'frigorífico', 'heladera', 'refrigerador'],
        'lavadora': ['lavarropas', 'máquina', 'lavadora'],
        'microondas': ['horno', 'microondas'],
        'horno': ['horno eléctrico', 'horno de gas', 'horno'],
        'licuadora': ['batidora', 'mezcladora', 'licuadora'],
        'tostadora': ['tostador', 'tostadora'],
        'plancha': ['plancha', 'planchado', 'ropa', 'plancha', 'vapor', 'steam'],
        
        # Alimentos y bebidas
        'cafe': ['café', 'grano', 'semilla', 'cafe'],
        'aceite': ['óleo', 'grasa', 'líquido', 'aceite', 'oliva', 'olive'],
        'chocolate': ['cacao', 'dulce', 'confitería', 'chocolate', 'negro', 'dark'],
        'miel': ['abeja', 'dulce', 'natural', 'miel', 'bee'],
        'vino': ['bebida', 'alcohólico', 'uva', 'vino'],
        'cerveza': ['bebida', 'alcohólico', 'malta', 'cerveza'],
        'leche': ['lácteo', 'dairy', 'leche'],
        'queso': ['lácteo', 'dairy', 'queso'],
        'pan': ['panadería', 'bollería', 'pan'],
        'arroz': ['cereal', 'grano', 'arroz'],
        'azucar': ['azúcar', 'dulce', 'azucar'],
        'sal': ['condimento', 'sal'],
        'harina': ['cereal', 'grano', 'harina'],
        
        # Materiales de construcción
        'cemento': ['construcción', 'material', 'aglomerante', 'cemento'],
        'ladrillo': ['construcción', 'material', 'cerámico', 'ladrillo'],
        'pintura': ['color', 'revestimiento', 'acabado', 'pintura'],
        'madera': ['leño', 'tronco', 'tabla', 'madera', 'pino', 'pine'],
        'acero': ['metal', 'hierro', 'acero'],
        'vidrio': ['cristal', 'vidrio', 'templado', 'tempered'],
        'plastico': ['plástico', 'polímero', 'plastico'],
        
        # Herramientas
        'taladro': ['herramienta', 'perforar', 'taladrar', 'taladro'],
        'martillo': ['herramienta', 'golpear', 'clavar', 'martillo'],
        'destornillador': ['herramienta', 'atornillar', 'desatornillar', 'destornillador'],
        'sierra': ['cortar', 'madera', 'herramienta', 'sierra'],
        'nivel': ['medir', 'horizontal', 'vertical', 'nivel', 'burbuja', 'bubble'],
        'multimetro': ['multímetro', 'medir', 'eléctrico', 'multimetro'],
        'tijeras': ['cortar', 'podar', 'herramienta', 'tijeras'],
        'llave': ['herramienta', 'tuerca', 'tornillo', 'llave'],
        'alicate': ['herramienta', 'cortar', 'alicate'],
        
        # Juguetes
        'bloques': ['construcción', 'juguete', 'piezas', 'bloques'],
        'muñeca': ['juguete', 'niña', 'figura', 'muñeca'],
        'puzzle': ['rompecabezas', 'juego', 'piezas', 'puzzle', '1000'],
        'pelota': ['balón', 'esfera', 'juego', 'pelota'],
        'tren': ['juguete', 'vehículo', 'tren'],
        'carro': ['juguete', 'vehículo', 'carro'],
        'oso': ['peluche', 'juguete', 'oso'],
        
        # Productos médicos y farmacéuticos
        'termometro': ['termómetro', 'temperatura', 'medir', 'termometro'],
        'mascarilla': ['máscara', 'protección', 'filtro', 'mascarilla'],
        'vendaje': ['venda', 'curación', 'herida', 'vendaje'],
        'jeringa': ['inyección', 'aguja', 'jeringa'],
        'oximetro': ['oxímetro', 'pulso', 'saturación', 'oximetro'],
        'medicina': ['medicamento', 'fármaco', 'medicina'],
        'vitamina': ['suplemento', 'nutriente', 'vitamina'],
        'antibiotico': ['antibiótico', 'medicamento', 'antibiotico'],
        
        # Material de oficina y escolar
        'lapiz': ['lápiz', 'escribir', 'dibujar', 'lapiz'],
        'cuaderno': ['libro', 'escribir', 'papel', 'cuaderno'],
        'boligrafo': ['bolígrafo', 'escribir', 'pluma', 'boligrafo'],
        'pincel': ['pintar', 'brocha', 'arte', 'pincel'],
        'papel': ['hoja', 'documento', 'papel'],
        'goma': ['borrador', 'goma'],
        'regla': ['medir', 'línea', 'regla'],
        'calculadora': ['computar', 'calcular', 'calculadora'],
        
        # Productos químicos y limpieza
        'detergente': ['jabón', 'limpiador', 'detergente', 'liquid', 'líquido'],
        'jabon': ['jabón', 'soap', 'limpiador', 'jabon', 'tocador', 'barra'],
        'shampoo': ['champú', 'shampoo', 'cabello', 'pelo', 'hair'],
        'crema': ['loción', 'ungüento', 'pomada', 'crema', 'hidratante', 'moisturizer'],
        'pasta': ['pasta', 'pasta dental', 'dentífrico', 'dental', 'toothpaste'],
        'desodorante': ['desodorante', 'antitranspirante', 'deodorant'],
        'perfume': ['perfume', 'fragancia', 'colonia'],
        'cosmetico': ['cosmético', 'maquillaje', 'makeup'],
        
        # Jardinería y agricultura
        'semillas': ['semilla', 'planta', 'germinar', 'semillas'],
        'fertilizante': ['abono', 'nutriente', 'planta', 'fertilizante'],
        'manguera': ['tubo', 'riego', 'agua', 'manguera'],
        'maceta': ['macetero', 'planta', 'jardín', 'maceta'],
        'pala': ['herramienta', 'cavar', 'pala'],
        'rastrillo': ['herramienta', 'jardín', 'rastrillo'],
        'tijeras': ['cortar', 'podar', 'herramienta', 'tijeras'],
        
        # Joyería y accesorios
        'reloj': ['tiempo', 'pulsera', 'cronómetro', 'reloj'],
        'perfume': ['fragancia', 'aroma', 'colonia', 'perfume'],
        'collar': ['joya', 'cadena', 'adorno', 'collar'],
        'anillo': ['joya', 'dedo', 'anillo'],
        'aretes': ['pendientes', 'orejas', 'aretes'],
        'pulsera': ['muñeca', 'joya', 'pulsera'],
        
        # Óptica y visión
        'gafas': ['lentes', 'protección', 'ver', 'gafas'],
        'lentes': ['gafas', 'óptica', 'lentes'],
        'microscopio': ['lupa', 'magnificar', 'microscopio'],
        'telescopio': ['astronomía', 'observar', 'telescopio'],
        
        # Deportes y recreación
        'balon': ['balón', 'pelota', 'deporte', 'balon'],
        'raqueta': ['tenis', 'deporte', 'raqueta'],
        'bicicleta': ['bici', 'ciclo', 'vehículo', 'bicicleta'],
        'patin': ['patín', 'ruedas', 'patin'],
        'casco': ['protección', 'cabeza', 'casco'],
        'guantes': ['manos', 'protección', 'cubrir', 'guantes'],
        
        # Productos químicos y limpieza
        'detergente': ['limpieza', 'jabón', 'detergente'],
        'jabon': ['jabón', 'limpieza', 'jabon'],
        'shampoo': ['champú', 'cabello', 'shampoo'],
        'crema': ['cosmético', 'piel', 'crema'],
        'desodorante': ['axilas', 'perfume', 'desodorante'],
        'pasta': ['dientes', 'dental', 'pasta'],
        'cepillo': ['dientes', 'cabello', 'cepillo']
    }
    
    # Expandir palabras con sinónimos
    expanded_words = set(words)
    for word in words:
        if word in synonyms:
            expanded_words.update(synonyms[word])
    
    # Construir consulta que busque cualquiera de las palabras expandidas
    conditions = []
    params = {}
    
    # Inferir dominios por palabras - Sistema mejorado
    computer_terms = ['mouse', 'ratón', 'gaming', 'teclado', 'keyboard', 'monitor', 'pantalla', 'auriculares', 'headphones', 'computadora', 'laptop', 'smartphone', 'tablet', 'impresora', 'scanner', 'parlante', 'altavoz', 'speaker', 'microfono', 'micrófono', 'webcam', 'cámara', 'camera', 'televisor', 'tv', 'radio', 'bateria', 'batería', 'cargador', 'cable', 'adaptador']
    audio_terms = ['parlante', 'altavoz', 'speaker', 'sonido', 'audio', 'bluetooth', 'inalámbrico', 'wireless', 'auriculares', 'headphones', 'microfono', 'micrófono', 'amplificador', 'amplifier']
    garment_terms = ['camiseta', 'camisa', 'pantalon', 'chaqueta', 'abrigo', 'impermeable', 'prenda', 'ropa', 'algodon', 'poliester', 'tejido', 'bolso', 'gorra', 'vestido', 'falda', 'blusa']
    footwear_terms = ['zapato', 'zapatilla', 'tenis', 'calzado', 'deportivo', 'botin', 'bota', 'sandalia', 'suela', 'malla', 'antideslizante', 'empeine', 'plantilla']
    vehicle_terms = ['automovil', 'carro', 'vehiculo', 'moto', 'motocicleta', 'bicicleta', 'camion', 'bus', 'neumatico', 'llanta', 'chasis', 'faro']
    medical_terms = ['tensiometro', 'termometro', 'oximetro', 'mascarilla', 'guantes', 'vendaje', 'venda', 'jeringa', 'medicina', 'medicamento', 'fármaco', 'vitamina', 'antibiótico', 'curación', 'herida']
    mineral_terms = ['mineral', 'mena', 'concentrado', 'manganeso', 'hierro', 'cobre', 'turba', 'carbon']
    food_terms = ['cafe', 'azucar', 'harina', 'bebida', 'alimento', 'chocolate', 'leche', 'queso', 'pan', 'arroz', 'aceite', 'miel', 'vino', 'cerveza']
    tool_terms = ['taladro', 'martillo', 'destornillador', 'sierra', 'nivel', 'multímetro', 'tijeras', 'llave', 'alicate', 'herramienta']
    toy_terms = ['juguete', 'muñeca', 'puzzle', 'pelota', 'tren', 'carro', 'oso', 'bloques', 'juego', 'rompecabezas']
    construction_terms = ['cemento', 'ladrillo', 'pintura', 'madera', 'acero', 'vidrio', 'plástico', 'construcción', 'material']
    office_terms = ['lápiz', 'cuaderno', 'bolígrafo', 'pincel', 'papel', 'goma', 'regla', 'calculadora', 'oficina', 'escolar']
    garden_terms = ['semillas', 'fertilizante', 'manguera', 'maceta', 'pala', 'rastrillo', 'jardín', 'planta']
    jewelry_terms = ['reloj', 'perfume', 'collar', 'anillo', 'aretes', 'pulsera', 'joya', 'joyería']
    optical_terms = ['gafas', 'lentes', 'microscopio', 'telescopio', 'óptica', 'visión']
    sport_terms = ['balón', 'raqueta', 'patín', 'casco', 'deporte', 'recreación']
    cleaning_terms = ['detergente', 'jabón', 'shampoo', 'crema', 'desodorante', 'pasta', 'cepillo', 'limpieza', 'cosmético', 'jabon', 'tocador', 'hidratante', 'dental']
    animal_terms = ['ternero', 'vivo', 'cerdo', 'pollo', 'pescado', 'animal', 'ganado', 'bovino']

    has_computer_terms = any(term in text for term in computer_terms)
    has_audio_terms = any(term in text for term in audio_terms)
    has_garment_terms = any(term in text for term in garment_terms)
    has_footwear_terms = any(term in text for term in footwear_terms)
    has_vehicle_terms = any(term in text for term in vehicle_terms)
    has_medical_terms = any(term in text for term in medical_terms)
    has_mineral_terms = any(term in text for term in mineral_terms)
    has_food_terms = any(term in text for term in food_terms)
    has_tool_terms = any(term in text for term in tool_terms)
    has_toy_terms = any(term in text for term in toy_terms)
    has_construction_terms = any(term in text for term in construction_terms)
    has_office_terms = any(term in text for term in office_terms)
    has_garden_terms = any(term in text for term in garden_terms)
    has_jewelry_terms = any(term in text for term in jewelry_terms)
    has_optical_terms = any(term in text for term in optical_terms)
    has_sport_terms = any(term in text for term in sport_terms)
    has_cleaning_terms = any(term in text for term in cleaning_terms)
    has_animal_terms = any(term in text for term in animal_terms)

    # Filtros por capítulo cuando la intención es clara
    if has_computer_terms:
        conditions.append("(chapter = 84 OR chapter = 85)")
    if has_audio_terms:
        conditions.append("(chapter = 85)")  # Capítulo 85 para equipos de audio
    if has_garment_terms:
        conditions.append("(chapter IN (61,62,63))")
    if has_footwear_terms:
        conditions.append("(chapter = 64)")
    if has_vehicle_terms:
        conditions.append("(chapter = 87)")
    if has_medical_terms:
        conditions.append("(chapter IN (30,90))")
    if has_mineral_terms:
        conditions.append("(chapter IN (25,26,27))")
    if has_food_terms:
        conditions.append("(chapter BETWEEN 16 AND 22)")
    if has_tool_terms:
        conditions.append("(chapter = 82)")
    if has_toy_terms:
        conditions.append("(chapter = 95)")
    if has_construction_terms:
        conditions.append("(chapter BETWEEN 25 AND 27 OR chapter = 68 OR chapter = 69)")
    if has_office_terms:
        conditions.append("(chapter = 96)")
    if has_garden_terms:
        conditions.append("(chapter = 12 OR chapter = 14)")
    if has_jewelry_terms:
        conditions.append("(chapter = 71)")
    if has_optical_terms:
        conditions.append("(chapter = 90)")
    if has_sport_terms:
        conditions.append("(chapter = 95)")
    if has_cleaning_terms:
        conditions.append("(chapter = 34)")
    if has_animal_terms:
        conditions.append("(chapter = 1 OR chapter = 2 OR chapter = 3)")
    
    for i, word in enumerate(expanded_words):
        param_title = f"word_title_{i}"
        param_keywords = f"word_keywords_{i}"
        conditions.append(f"(LOWER(title) ILIKE :{param_title} OR LOWER(keywords) ILIKE :{param_keywords})")
        params[param_title] = f"%{word}%"
        params[param_keywords] = f"%{word}%"
    
    # Si no hay condiciones, usar búsqueda más amplia
    if not conditions:
        conditions = ["(LOWER(title) ILIKE :text OR LOWER(keywords) ILIKE :text)"]
        params["text"] = f"%{text}%"
    
    # Construir prioridad de capítulos dinámica
    chapter_priority = []
    if has_garment_terms:
        chapter_priority.extend([(61, 1), (62, 2), (63, 3)])
    if has_footwear_terms:
        chapter_priority.append((64, 1))
    if has_vehicle_terms:
        chapter_priority.append((87, 1))
    if has_computer_terms:
        chapter_priority.extend([(84, 1), (85, 2)])
    if has_audio_terms:
        chapter_priority.append((85, 1))  # Prioridad alta para audio en capítulo 85
    if has_medical_terms:
        chapter_priority.extend([(30, 1), (90, 2)])
    if has_mineral_terms:
        chapter_priority.extend([(25, 1), (26, 2), (27, 3)])
    if has_food_terms:
        chapter_priority.extend([(16, 1), (17, 2), (18, 3), (19, 4), (20, 5), (21, 6), (22, 7)])

    case_lines = []
    for ch, pri in chapter_priority:
        case_lines.append(f"WHEN chapter = {int(ch)} THEN {int(pri)}")
    case_expr = ("CASE " + " ".join(case_lines) + " ELSE 99 END,") if case_lines else ""

    query = f"""
        SELECT id, hs_code, title, keywords, level, chapter 
        FROM hs_items 
        WHERE {' AND '.join(conditions) if conditions else '1=1'}
        ORDER BY 
            CASE 
                WHEN LOWER(title) ILIKE :exact_match THEN 1
                WHEN LOWER(keywords) ILIKE :exact_match THEN 2
                ELSE 3
            END,
            {case_expr}
            hs_code 
        LIMIT :lim
    """
    params["exact_match"] = f"%{text}%"
    params["lim"] = int(limit)
    
    df = _fetch_df(cc, query, params)
    out: List[Candidate] = []
    
    if not df.empty:
        for _, r in df.iterrows():
            hs_code = str(r['hs_code'])
            title_lower = (r.get('title') or '').lower()
            keywords_lower = (r.get('keywords') or '').lower()
            keyword_hits = sum(
                1
                for word in expanded_words
                if (word in title_lower) or (word in keywords_lower)
            )
            out.append({
                'hs_code': _clean_hs(hs_code),
                'title': r.get('title'),
                'score': 1.0,
                'meta': {
                    'id': int(r['id']),
                    'level': int(r.get('level') or 0),
                    'chapter': int(r.get('chapter') or 0),
                    'keywords': r.get('keywords'),
                    'keyword_hits': keyword_hits
                }
            })
    
    return out


def _load_notes_links(cc: ControlConexion) -> Tuple[Any, Any]:
    notes = _fetch_df(cc, "SELECT id, scope, scope_code, note_number, text FROM hs_notes")
    # Tabla relacional opcional rule_link_hs (si existe): rule_id, note_id, hs_code
    links = _fetch_df(cc, "SELECT * FROM rule_link_hs")
    return notes, links


def _trace(steps: List[TraceStep], rgi: str, decision: str, affected: List[str], legal_refs: Dict[str, List[int]]):
    steps.append({
        'rgi': rgi,
        'decision': decision,
        'affected': affected,
        'legal_refs': legal_refs,
    })


# RGI 1 -------------------------------------------------------------------
def apply_rgi1(description: str, extra_texts: List[str] | None = None, features: Dict[str, Any] = None) -> Tuple[List[Candidate], List[TraceStep]]:
    """
    Aplica RGI 1 con apoyo en textos legales y Notas (de Sección/Capítulo/Partida).
    - Filtra candidatos por coincidencias con hs_notes y títulos del catálogo.
    - Registra referencias legales (note_id, y si hay, rule_id/legal_source_id vía vínculos).
    """
    cc = ControlConexion()
    steps: List[TraceStep] = []
    try:
        text = ' '.join([t for t in [description] + (extra_texts or []) if t])
        priority_candidates = _priority_candidates_from_text(text, features or {})
        cand = priority_candidates + _keyword_candidates(cc, text, limit=100, features=features or {})
        notes, links = _load_notes_links(cc)
        rgi_map = _fetch_rgi_map(cc)

        used_note_ids: List[int] = []
        used_legal_ids: List[int] = []

        # Filtro por notas: si una nota menciona una palabra clave, prioriza capítulos/partidas
        matched_chapters: set[str] = set()
        matched_headings: set[str] = set()

        if not notes.empty and text:
            low = text.lower()
            for _, n in notes.iterrows():
                note_text = str(n.get('text') or '').lower()
                if not note_text:
                    continue
                # Simple heurística: intersección de palabras clave
                hits = 0
                for kw in [w for w in low.split() if len(w) > 3]:
                    if kw in note_text:
                        hits += 1
                        if hits >= 3:
                            break
                if hits >= 3:
                    used_note_ids.append(int(n['id']))
                    scope = str(n.get('scope') or '').upper()
                    scope_code = str(n.get('scope_code') or '')
                    if scope == 'CHAPTER' and scope_code:
                        matched_chapters.add(scope_code.zfill(2)[:2])
                    if scope in ('HEADING', 'PARTIDA') and scope_code:
                        # heading sin punto, e.g., 8471
                        matched_headings.add(scope_code[:4])

        # Reducir candidatos por match de capítulo o partida
        filtered: List[Candidate] = []
        if matched_chapters or matched_headings:
            for c in cand:
                ch = _hs_chapter(c['hs_code'])
                hd = _hs_heading(c['hs_code'])
                c.setdefault('meta', {})
                if (ch in matched_chapters) or (hd in matched_headings):
                    c['meta']['note_match'] = True
                    c['meta']['note_hits'] = len(used_note_ids)
                    filtered.append(c)
        else:
            for c in cand:
                c.setdefault('meta', {})
                c['meta'].setdefault('note_hits', 0)
            filtered = cand
        for c in filtered:
            c['meta'].setdefault('note_hits', c['meta'].get('note_hits', 0))

        # Legal refs adicionales desde links si existen
        if not links.empty and used_note_ids:
            if 'legal_source_id' in links.columns:
                used_legal_ids = list({int(x) for x in links.loc[links['note_id'].isin(used_note_ids)]['legal_source_id'].dropna().tolist()})

        _trace(
            steps,
            'RGI1',
            'Filtrado inicial por textos de partida y Notas legales',
            affected=[c['hs_code'] for c in filtered],
            legal_refs={
                'rgi_id': [rgi_map.get('RGI1')] if rgi_map.get('RGI1') else [],
                'note_id': used_note_ids,
                'legal_source_id': used_legal_ids,
            },
        )
        return filtered, steps
    finally:
        try:
            cc.cerrar_bd()
        except Exception:
            pass


# RGI 2 -------------------------------------------------------------------
def apply_rgi2(description: str, candidates: List[Candidate], steps: List[TraceStep]) -> Tuple[List[Candidate], List[TraceStep]]:
    """
    Aplica RGI 2(a) y 2(b) de forma heurística por palabras clave:
    - 2(a): incompleto, desarmado, sin terminar -> tratar como completo si conserva el carácter esencial.
    - 2(b): mezclas, conjuntos, mercancías compuestas.
    En ausencia de estructura de componentes, registra trazabilidad sin filtrar agresivamente.
    """
    cc = ControlConexion()
    try:
        rgi_map = _fetch_rgi_map(cc)
        text = (description or '').lower()
        note_ids: List[int] = []
        decision = []

        incompleto = any(k in text for k in ['incompleto', 'desarmado', 'sin terminar', 'semiarmado'])
        mezcla = any(k in text for k in ['mezcla', 'mixto', 'conjunto', 'set', 'combinado'])

        # Heurística mejorada: priorizar capítulos más relevantes semánticamente
        new_cands = candidates[:]
        if candidates:
            # Mapeo de palabras clave a capítulos preferidos
            text_lower = text.lower()
            preferred_chapters = []
            
            # Animales vivos (priorizar capítulo 01 para animales vivos)
            if any(word in text_lower for word in ['ternero', 'vivo', 'animal', 'ganado', 'bovino', 'vaca', 'toro']):
                if 'vivo' in text_lower:
                    preferred_chapters.extend([1])  # Solo capítulo 01 para animales vivos
                else:
                    preferred_chapters.extend([1, 2, 3, 4, 5])  # Incluir carne si no especifica "vivo"
            
            # Textiles y prendas
            if any(word in text_lower for word in ['camiseta', 'camisa', 'prenda', 'ropa', 'vestido', 'textil', 'algodón']):
                preferred_chapters.extend([61, 62, 63])
            
            # Máquinas y equipos
            if any(word in text_lower for word in ['computadora', 'máquina', 'equipo', 'motor', 'herramienta']):
                preferred_chapters.extend([84, 85])
            
            # Alimentos
            if any(word in text_lower for word in ['café', 'alimento', 'comida', 'bebida', 'carne']):
                preferred_chapters.extend([16, 17, 18, 19, 20])
            
            # Si hay capítulos preferidos, filtrar por ellos
            if preferred_chapters:
                new_cands = [c for c in candidates if int(_hs_chapter(c['hs_code']) or '0') in preferred_chapters]
                if new_cands:
                    decision.append(f"Prioriza capítulos semánticamente relevantes: {preferred_chapters}")
                else:
                    new_cands = candidates[:]  # Si no hay coincidencias, mantener todos
            elif mezcla and candidates:
                # Lógica original para mezclas sin preferencias semánticas
                chapters = {}
                for c in candidates:
                    ch = _hs_chapter(c['hs_code'])
                    chapters[ch] = chapters.get(ch, 0) + 1
                if chapters:
                    dominant = max(chapters.items(), key=lambda x: x[1])[0]
                    new_cands = [c for c in candidates if _hs_chapter(c['hs_code']) == dominant]
                    decision.append(f"Prioriza capítulo dominante {dominant} (mezcla/conjunto)")
                else:
                    new_cands = candidates[:]  # Si no hay capítulos, mantener todos

        if incompleto:
            decision.append("Tratar mercancía incompleta/desarmada como completa si conserva carácter esencial")

        _trace(
            steps,
            'RGI2',
            "; ".join(decision) if decision else 'Sin cambios por RGI2',
            affected=[c['hs_code'] for c in new_cands],
            legal_refs={
                'rgi_id': [rgi_map.get('RGI2A'), rgi_map.get('RGI2B')] if (rgi_map.get('RGI2A') or rgi_map.get('RGI2B')) else [],
                'note_id': note_ids,
                'legal_source_id': [],
            },
        )
        return new_cands, steps
    finally:
        try:
            cc.cerrar_bd()
        except Exception:
            pass


# RGI 3 -------------------------------------------------------------------
def apply_rgi3(candidates: List[Candidate], steps: List[TraceStep], features: Dict[str, Any] = None) -> Tuple[List[Candidate], List[TraceStep]]:
    """
    Aplica RGI 3(a)-(c):
    - 3(a) preferir partida más específica: se aproxima por mayor nivel de detalle (HS6 sobre HS4/HS2) y mejor score.
    - 3(b) carácter esencial: como aproximación, mantener el heading con mayor densidad de candidatos.
    - 3(c) si persiste empate, la última por orden de numeración.
    
    --- MEJORA CLASIFICACIÓN HS CONTEXTUAL ---
    Incorpora banderas contextuales (features) para priorizar según tipo_de_bien, uso_principal y nivel_procesamiento.
    --- FIN MEJORA CLASIFICACIÓN HS CONTEXTUAL ---
    """
    cc = ControlConexion()
    try:
        rgi_map = _fetch_rgi_map(cc)
        if not candidates:
            _trace(steps, 'RGI3', 'Sin candidatos', [], {'rgi_id': [rgi_map.get('RGI3A'), rgi_map.get('RGI3B'), rgi_map.get('RGI3C')], 'note_id': [], 'legal_source_id': []})
            return candidates, steps

        # 3(a) y 3(b): puntaje por especificidad + densidad por heading + relevancia semántica
        heading_freq = {}
        for c in candidates:
            hd = _hs_heading(c['hs_code'])
            heading_freq[hd] = heading_freq.get(hd, 0) + 1

        def score(c: Candidate) -> Tuple[int, float, int, int, float]:
            # Priorizar por especificidad (HS6 completo)
            hs6_len = 1 if len(_hs6(c['hs_code'])) == 6 else 0
            # Score original
            sc = float(c.get('score') or 0.0)
            # Densidad por heading
            dens = heading_freq.get(_hs_heading(c['hs_code']), 0)
            
            # --- MEJORA CLASIFICACIÓN HS CONTEXTUAL ---
            # Score de contexto basado en features
            score_contexto = 0.0
            if features:
                title_lower = (c.get('title') or '').lower()
                
                # Penalizar "partes y accesorios" si el producto es terminado
                if features.get('tipo_de_bien') == 'producto_terminado':
                    if any(term in title_lower for term in ['parte', 'partes', 'accesorio', 'accesorios', 'componente']):
                        score_contexto -= 50.0  # Penalización fuerte
                
                # Priorizar materia_prima en capítulos 1-27
                if features.get('tipo_de_bien') == 'materia_prima':
                    chapter = int(_hs_chapter(c['hs_code']) or '0')
                    if 1 <= chapter <= 27:  # Materias primas (animales, vegetales, minerales)
                        score_contexto += 20.0
                    else:  # Penalizar capítulos de manufacturados
                        score_contexto -= 30.0
                
                # Priorizar según uso_principal
                uso = features.get('uso_principal', 'otro')
                chapter = int(_hs_chapter(c['hs_code']) or '0')
                
                if uso == 'computo':
                    if chapter in [84, 85]:  # Máquinas y aparatos eléctricos
                        score_contexto += 30.0
                        # Ajuste moderado para laptops (8471300000) evitando sesgos
                        if '847130' in c['hs_code'] or '847130' in (c.get('title') or ''):
                            score_contexto += 15.0
                    else:
                        score_contexto -= 20.0
                
                elif uso == 'construccion':
                    if chapter in [25, 68, 69]:  # Materiales de construcción
                        score_contexto += 30.0
                    else:
                        score_contexto -= 20.0
                
                elif uso == 'alimentario':
                    if chapter in [16, 17, 18, 19, 20, 9]:  # Alimentos y café
                        score_contexto += 25.0
                        # Boost para café sin tostar (090111)
                        if '0901' in c['hs_code'] or ('cafe' in title_lower and 'sin tostar' in title_lower):
                            score_contexto += 40.0
                    else:
                        score_contexto -= 15.0
                
                elif uso == 'vestimenta':
                    if chapter in [61, 62, 63, 64]:  # Textiles y calzado
                        score_contexto += 25.0
                
                elif uso == 'agropecuario':
                    if chapter in [1, 2, 3, 4, 5]:  # Animales vivos
                        score_contexto += 30.0
                    else:
                        score_contexto -= 20.0
                
                elif uso == 'medico':
                    if chapter in [30, 38, 90]:  # Farmacéuticos y aparatos médicos
                        score_contexto += 25.0
            # --- FIN MEJORA CLASIFICACIÓN HS CONTEXTUAL ---
            
            # Priorizar capítulos más relevantes (textiles=61-63, animales=01-05, etc.)
            chapter = int(_hs_chapter(c['hs_code']) or '0')
            chapter_priority = 0
            if chapter in [61, 62, 63]:  # Textiles
                chapter_priority = 3
            elif chapter in [1, 2, 3, 4, 5]:  # Animales vivos
                chapter_priority = 3
            elif chapter in [84, 85]:  # Máquinas
                chapter_priority = 2
            elif chapter in [16, 17, 18, 19, 20]:  # Alimentos
                chapter_priority = 2
            else:
                chapter_priority = 1
            
            return (hs6_len, chapter_priority, sc, dens, score_contexto)

        # Escoge top-N por score para seguir (mantener algunos para RGI6)
        sorted_c = sorted(candidates, key=score, reverse=True)
        top = sorted_c[:5] if len(sorted_c) > 5 else sorted_c

        # 3(c) desempate final: última por numeración
        if top:
            max_code = max(top, key=lambda c: _hs6(c['hs_code']) or _hs_heading(c['hs_code']) or _hs_chapter(c['hs_code']))
            final_list = [max_code]
        else:
            final_list = []

        _trace(
            steps,
            'RGI3',
            'Preferencia por especificidad (HS6), densidad por heading y última por numeración como desempate',
            affected=[c['hs_code'] for c in top],
            legal_refs={
                'rgi_id': [rgi_map.get('RGI3A'), rgi_map.get('RGI3B'), rgi_map.get('RGI3C')],
                'note_id': [],
                'legal_source_id': [],
            },
        )
        return final_list, steps
    finally:
        try:
            cc.cerrar_bd()
        except Exception:
            pass


# RGI 6 -------------------------------------------------------------------
def apply_rgi6(candidates: List[Candidate], steps: List[TraceStep]) -> Tuple[List[Candidate], List[TraceStep]]:
    """
    RGI 6: Comparar únicamente subpartidas del mismo nivel. Si hay más de un HS6
    bajo distintas partidas, restringe al heading de la mejor opción previa.
    """
    cc = ControlConexion()
    try:
        rgi_map = _fetch_rgi_map(cc)
        if not candidates:
            _trace(steps, 'RGI6', 'Sin candidatos', [], {'rgi_id': [rgi_map.get('RGI6')], 'note_id': [], 'legal_source_id': []})
            return candidates, steps

        base = candidates[0]
        base_heading = _hs_heading(base['hs_code'])
        same_heading = [c for c in candidates if _hs_heading(c['hs_code']) == base_heading]
        if same_heading:
            decision = f"Comparación al mismo nivel de subpartida; restringe a heading {base_heading}"
            result = [same_heading[0]]
        else:
            decision = "Sin cambios (ya en el mismo nivel)"
            result = candidates

        _trace(steps, 'RGI6', decision, [c['hs_code'] for c in result], {'rgi_id': [rgi_map.get('RGI6')], 'note_id': [], 'legal_source_id': []})
        return result, steps
    finally:
        try:
            cc.cerrar_bd()
        except Exception:
            pass


# Orquestador --------------------------------------------------------------
def apply_all(description: str, extra_texts: List[str] | None = None, features: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Aplica RGI 1 -> 2 -> 3 -> 6 y retorna un dict con:
    {
        'hs6': '847130',
        'trace': [TraceStep, ...],
        'candidates_final': [Candidate]
    }
    
    --- MEJORA CLASIFICACIÓN HS CONTEXTUAL ---
    Ahora acepta features para priorización contextual.
    --- FIN MEJORA CLASIFICACIÓN HS CONTEXTUAL ---
    """
    # RGI1: generar y filtrar candidatos
    cand, trace = apply_rgi1(description, extra_texts)

    # RGI2: ajustar por incompletos/mezclas
    cand, trace = apply_rgi2(description, cand, trace)

    # RGI3: resolver empates y especificidad (con features)
    cand, trace = apply_rgi3(cand, trace, features=features)

    # RGI6: confirmar nivel de comparación
    cand, trace = apply_rgi6(cand, trace)

    hs6 = _hs6(cand[0]['hs_code']) if cand else ''
    return {
        'hs6': hs6,
        'trace': trace,
        'candidates_final': cand,
    }


def _calculate_contextual_score(hs_code: str, features: Dict[str, Any]) -> float:
    """
    Calcula score contextual basado en características del producto para mejorar precisión.
    
    Args:
        hs_code: Código HS a evaluar
        features: Características extraídas del producto
        
    Returns:
        Score contextual entre 0.0 y 1.0
    """
    try:
        contextual_score = 1.0
        
        # Extraer capítulo del código HS
        hs_chapter = hs_code[:2] if len(hs_code) >= 2 else "00"
        
        # 1. Validar coherencia de capítulo con uso principal
        uso_principal = features.get('uso_principal', '').lower()
        if uso_principal:
            chapter_usage_map = {
                # Animales vivos y productos de origen animal (01-05)
                '01': ['alimentacion', 'alimento', 'comida', 'nutricion', 'ganaderia'],
                '02': ['alimentacion', 'alimento', 'comida', 'nutricion', 'carnes'],
                '03': ['alimentacion', 'alimento', 'comida', 'nutricion', 'pescado'],
                '04': ['alimentacion', 'alimento', 'comida', 'nutricion', 'lacteos'],
                '05': ['alimentacion', 'alimento', 'comida', 'nutricion', 'animal'],
                
                # Productos vegetales (06-14)
                '06': ['jardineria', 'jardín', 'decoracion', 'flores'],
                '07': ['alimentacion', 'alimento', 'comida', 'nutricion', 'vegetales'],
                '08': ['alimentacion', 'alimento', 'comida', 'nutricion', 'frutas'],
                '09': ['alimentacion', 'alimento', 'comida', 'nutricion', 'especias'],
                '10': ['alimentacion', 'alimento', 'comida', 'nutricion', 'cereales'],
                '11': ['alimentacion', 'alimento', 'comida', 'nutricion', 'harinas'],
                '12': ['alimentacion', 'alimento', 'comida', 'nutricion', 'semillas'],
                '13': ['alimentacion', 'alimento', 'comida', 'nutricion', 'resinas'],
                '14': ['jardineria', 'jardín', 'decoracion', 'vegetales'],
                
                # Grasas y aceites (15)
                '15': ['alimentacion', 'alimento', 'comida', 'nutricion', 'aceites'],
                
                # Preparaciones de carne, pescado, crustáceos (16)
                '16': ['alimentacion', 'alimento', 'comida', 'nutricion', 'conservas'],
                
                # Azúcares y confitería (17-18)
                '17': ['alimentacion', 'alimento', 'comida', 'nutricion', 'azucar'],
                '18': ['alimentacion', 'alimento', 'comida', 'nutricion', 'cacao'],
                
                # Preparaciones alimenticias (19-22)
                '19': ['alimentacion', 'alimento', 'comida', 'nutricion', 'preparaciones'],
                '20': ['alimentacion', 'alimento', 'comida', 'nutricion', 'conservas'],
                '21': ['alimentacion', 'alimento', 'comida', 'nutricion', 'preparaciones'],
                '22': ['alimentacion', 'alimento', 'comida', 'nutricion', 'bebidas'],
                
                # Residuos y desperdicios (23)
                '23': ['alimentacion', 'alimento', 'comida', 'nutricion', 'forraje'],
                
                # Tabaco (24)
                '24': ['tabaco', 'fumar', 'cigarrillos'],
                
                # Minerales (25-27)
                '25': ['construccion', 'construcción', 'edificacion', 'obra', 'minerales'],
                '26': ['construccion', 'construcción', 'edificacion', 'obra', 'minerales'],
                '27': ['construccion', 'construcción', 'edificacion', 'obra', 'combustibles'],
                
                # Productos químicos (28-38)
                '28': ['quimicos', 'químicos', 'industria', 'laboratorio'],
                '29': ['quimicos', 'químicos', 'industria', 'laboratorio'],
                '30': ['medicina', 'medicinal', 'farmaceutico', 'salud'],
                '31': ['agricultura', 'fertilizantes', 'cultivo'],
                '32': ['construccion', 'construcción', 'edificacion', 'obra', 'pinturas'],
                '33': ['cosmetica', 'cosmética', 'perfumeria', 'higiene'],
                '34': ['limpieza', 'detergentes', 'jabones'],
                '35': ['textil', 'papel', 'adhesivos'],
                '36': ['pirotecnia', 'explosivos', 'seguridad'],
                '37': ['fotografia', 'fotografía', 'peliculas'],
                '38': ['quimicos', 'químicos', 'industria', 'laboratorio'],
                
                # Plásticos y caucho (39-40)
                '39': ['plastico', 'plástico', 'envases', 'embalaje'],
                '40': ['caucho', 'neumaticos', 'llantas', 'automotriz'],
                
                # Cuero (41-43)
                '41': ['cuero', 'calzado', 'marroquineria'],
                '42': ['cuero', 'calzado', 'marroquineria'],
                '43': ['cuero', 'calzado', 'marroquineria'],
                
                # Madera (44-46)
                '44': ['construccion', 'construcción', 'edificacion', 'obra', 'madera'],
                '45': ['construccion', 'construcción', 'edificacion', 'obra', 'corcho'],
                '46': ['construccion', 'construcción', 'edificacion', 'obra', 'mimbre'],
                
                # Papel (47-49)
                '47': ['papel', 'impresion', 'impresión', 'oficina'],
                '48': ['papel', 'impresion', 'impresión', 'oficina'],
                '49': ['papel', 'impresion', 'impresión', 'oficina'],
                
                # Textiles (50-63)
                '50': ['textil', 'ropa', 'vestimenta', 'confeccion'],
                '51': ['textil', 'ropa', 'vestimenta', 'confeccion'],
                '52': ['textil', 'ropa', 'vestimenta', 'confeccion'],
                '53': ['textil', 'ropa', 'vestimenta', 'confeccion'],
                '54': ['textil', 'ropa', 'vestimenta', 'confeccion'],
                '55': ['textil', 'ropa', 'vestimenta', 'confeccion'],
                '56': ['textil', 'ropa', 'vestimenta', 'confeccion'],
                '57': ['textil', 'ropa', 'vestimenta', 'confeccion'],
                '58': ['textil', 'ropa', 'vestimenta', 'confeccion'],
                '59': ['textil', 'ropa', 'vestimenta', 'confeccion'],
                '60': ['textil', 'ropa', 'vestimenta', 'confeccion'],
                '61': ['textil', 'ropa', 'vestimenta', 'confeccion'],
                '62': ['textil', 'ropa', 'vestimenta', 'confeccion'],
                '63': ['textil', 'ropa', 'vestimenta', 'confeccion'],
                
                # Calzado (64-67)
                '64': ['calzado', 'zapatos', 'botas', 'sandalias'],
                '65': ['sombreros', 'gorras', 'accesorios'],
                '66': ['paraguas', 'bastones', 'accesorios'],
                '67': ['plumas', 'flores', 'artificiales'],
                
                # Piedra, cerámica, vidrio (68-70)
                '68': ['construccion', 'construcción', 'edificacion', 'obra', 'piedra'],
                '69': ['construccion', 'construcción', 'edificacion', 'obra', 'ceramica'],
                '70': ['construccion', 'construcción', 'edificacion', 'obra', 'vidrio'],
                
                # Metales preciosos (71)
                '71': ['joyeria', 'joyería', 'metales', 'preciosos'],
                
                # Metales comunes (72-83)
                '72': ['construccion', 'construcción', 'edificacion', 'obra', 'hierro'],
                '73': ['construccion', 'construcción', 'edificacion', 'obra', 'hierro'],
                '74': ['construccion', 'construcción', 'edificacion', 'obra', 'cobre'],
                '75': ['construccion', 'construcción', 'edificacion', 'obra', 'niquel'],
                '76': ['construccion', 'construcción', 'edificacion', 'obra', 'aluminio'],
                '78': ['construccion', 'construcción', 'edificacion', 'obra', 'plomo'],
                '79': ['construccion', 'construcción', 'edificacion', 'obra', 'zinc'],
                '80': ['construccion', 'construcción', 'edificacion', 'obra', 'estano'],
                '81': ['construccion', 'construcción', 'edificacion', 'obra', 'metales'],
                '82': ['herramientas', 'ferreteria', 'ferretería', 'utensilios'],
                '83': ['herramientas', 'ferreteria', 'ferretería', 'utensilios'],
                
                # Máquinas y equipos (84-85)
                '84': ['maquinas', 'máquinas', 'equipos', 'industria', 'computo'],
                '85': ['electronica', 'electrónica', 'electricidad', 'telecomunicaciones'],
                
                # Vehículos (86-89)
                '86': ['transporte', 'ferrocarril', 'trenes'],
                '87': ['transporte', 'automotriz', 'vehiculos', 'vehículos'],
                '88': ['transporte', 'aereo', 'aéreo', 'aviones'],
                '89': ['transporte', 'maritimo', 'marítimo', 'barcos'],
                
                # Instrumentos ópticos y médicos (90-92)
                '90': ['medicina', 'medicinal', 'farmaceutico', 'salud', 'instrumentos'],
                '91': ['relojes', 'cronometros', 'cronómetros'],
                '92': ['musica', 'música', 'instrumentos'],
                
                # Armas (93)
                '93': ['armas', 'militar', 'seguridad'],
                
                # Manufacturas diversas (94-96)
                '94': ['muebles', 'hogar', 'decoracion', 'decoración'],
                '95': ['juguetes', 'deportes', 'recreacion', 'recreación'],
                '96': ['manufacturas', 'diversas', 'accesorios'],
                
                # Arte y antigüedades (97)
                '97': ['arte', 'antiguedades', 'antigüedades', 'coleccion', 'colección']
            }
            
            expected_usages = chapter_usage_map.get(hs_chapter, [])
            if expected_usages and not any(usage in uso_principal for usage in expected_usages):
                contextual_score -= 0.3  # Penalización fuerte por incoherencia
        
        # 2. Validar tipo de bien vs código HS
        tipo_bien = features.get('tipo_de_bien', '').lower()
        if tipo_bien == 'producto_terminado':
            # Productos terminados no deberían estar en capítulos de partes
            if hs_chapter in ['84', '85', '86', '87', '88', '89', '90', '91', '92', '93', '94', '95', '96', '97']:
                contextual_score -= 0.2  # Penalización moderada
        
        # 3. Validar nivel de procesamiento
        nivel_procesamiento = features.get('nivel_procesamiento', '').lower()
        if nivel_procesamiento == 'terminado':
            # Productos terminados no deberían estar en capítulos de materias primas
            if hs_chapter in ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24', '25', '26', '27', '28', '29', '30', '31', '32', '33', '34', '35', '36', '37', '38', '39', '40', '41', '42', '43', '44', '45', '46', '47', '48', '49', '50', '51', '52', '53', '54', '55', '56', '57', '58', '59', '60', '61', '62', '63', '64', '65', '66', '67', '68', '69', '70', '71', '72', '73', '74', '75', '76', '77', '78', '79', '80', '81', '82', '83']:
                contextual_score -= 0.2  # Penalización moderada
        
        # 4. Validar material vs código HS
        material = features.get('material', '').lower()
        if material:
            material_chapter_map = {
                'algodon': ['50', '51', '52', '53', '54', '55', '56', '57', '58', '59', '60', '61', '62', '63'],
                'algodón': ['50', '51', '52', '53', '54', '55', '56', '57', '58', '59', '60', '61', '62', '63'],
                'metal': ['72', '73', '74', '75', '76', '77', '78', '79', '80', '81', '82', '83'],
                'acero': ['72', '73', '74', '75', '76', '77', '78', '79', '80', '81', '82', '83'],
                'plastico': ['39', '40', '41', '42', '43', '44', '45', '46', '47', '48', '49'],
                'plástico': ['39', '40', '41', '42', '43', '44', '45', '46', '47', '48', '49'],
                'madera': ['44', '45', '46', '47', '48', '49'],
                'ceramica': ['69', '70', '71'],
                'cerámica': ['69', '70', '71'],
                'vidrio': ['70', '71'],
                'caucho': ['40', '41', '42', '43', '44', '45', '46', '47', '48', '49'],
            }
            
            expected_chapters = material_chapter_map.get(material, [])
            if expected_chapters and hs_chapter not in expected_chapters:
                contextual_score -= 0.2  # Penalización moderada por incoherencia de material
        
        return max(0.1, contextual_score)  # Mínimo 0.1 para evitar scores muy bajos
        
    except Exception as e:
        print(f"[ERROR] Error calculando score contextual: {e}")
        return 0.5  # Score neutro en caso de error
