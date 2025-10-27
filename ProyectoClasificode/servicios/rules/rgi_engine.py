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


def _fetch_rgi_map(cc: ControlConexion) -> Dict[str, int]:
    """Devuelve un mapa {'RGI1': id, 'RGI2A': id, ...} si existen."""
    df = _fetch_df(cc, "SELECT id, rgi FROM rgi_rules")
    mapping: Dict[str, int] = {}
    if not df.empty:
        for _, r in df.iterrows():
            mapping[str(r['rgi']).upper()] = int(r['id'])
    return mapping


def _keyword_candidates(cc: ControlConexion, text: str, limit: int = 50) -> List[Candidate]:
    """Búsqueda mejorada por keywords que maneja múltiples términos y sinónimos."""
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
            out.append({
                'hs_code': _clean_hs(hs_code),
                'title': r.get('title'),
                'score': 1.0,
                'meta': {
                    'id': int(r['id']),
                    'level': int(r.get('level') or 0),
                    'chapter': int(r.get('chapter') or 0),
                    'keywords': r.get('keywords')
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
def apply_rgi1(description: str, extra_texts: List[str] | None = None) -> Tuple[List[Candidate], List[TraceStep]]:
    """
    Aplica RGI 1 con apoyo en textos legales y Notas (de Sección/Capítulo/Partida).
    - Filtra candidatos por coincidencias con hs_notes y títulos del catálogo.
    - Registra referencias legales (note_id, y si hay, rule_id/legal_source_id vía vínculos).
    """
    cc = ControlConexion()
    steps: List[TraceStep] = []
    try:
        text = ' '.join([t for t in [description] + (extra_texts or []) if t])
        cand = _keyword_candidates(cc, text, limit=100)
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
                if (ch in matched_chapters) or (hd in matched_headings):
                    filtered.append(c)
        else:
            filtered = cand

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
                        # Boost específico para laptops (8471300000)
                        if '847130' in c['hs_code'] or '847130' in (c.get('title') or ''):
                            score_contexto += 50.0
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
