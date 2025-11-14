from typing import Dict, Any, List, Tuple, Optional
import json
import numpy as np
from rapidfuzz import fuzz
import unicodedata
import os
from datetime import datetime
import logging
from sqlalchemy import text
from pathlib import Path

from .control_conexion import ControlConexion
from .modeloPln.embedding_service import EmbeddingService
from .modeloPln.nlp_service import NLPService
from .rules.rgi_engine import apply_all as rgi_apply_all
from .repos import CandidateRepository
from .learning_integration import learning_integration
from .incremental_validation import incremental_validation
from .metrics_service import MetricsService


class NationalClassifier:
    """
    Clasificador principal del sistema ClasifiCode para clasificación arancelaria HS.
    
    Este clasificador utiliza múltiples estrategias para determinar el código HS correcto:
    
    1. **Reglas Específicas**: Mapeo directo de productos comunes conocidos a códigos HS específicos.
    2. **Motor RGI (Rule-Guided Inference)**: Sistema jerárquico de clasificación basado en características.
    3. **Validación de Consistencia**: Verificación de coherencia entre características y código HS.
    4. **Métricas y Monitoreo**: Registro automático de métricas para monitoreo del sistema.
    """
    
    def __init__(self):
        """Inicializa el clasificador nacional con todos los servicios necesarios."""
        self.cc = ControlConexion()
        self.embed = EmbeddingService()
        self.nlp = NLPService()
        self.candidate_repo = CandidateRepository()
        self.metrics_service = MetricsService()
        
        # Códigos HS sospechosos que aparecen frecuentemente como comodines
        self._SUSPECT_CODES = [
            "1905000000",  # Pan y productos de panadería
            "0901110000",  # Café sin tostar
            "7001000000",  # Vidrio en bruto
            "7207110000",  # Hierro o acero sin alear
            "8711100000",  # Motocicletas
            "2201100000"   # Agua mineral
        ]
        
        self._fallback_rules = [
            {'hs6': '847130', 'keywords': ['servidor', 'rack', 'xeon', 'workstation']},
            {'hs6': '851762', 'keywords': ['router', 'wi fi', 'wifi', 'modem', 'acceso', 'inalambrico']},
            {'hs6': '851770', 'keywords': ['sensor', 'arduino', 'modulo', 'telemetria']},
            {'hs6': '853950', 'keywords': ['foco', 'bombilla', 'lampara', 'led']},
            {'hs6': '854420', 'keywords': ['cable coaxial', 'coaxial', 'rg6']},
            {'hs6': '392321', 'keywords': ['bolsa biodegradable', 'compostable', 'bolsa vegetal']},
            {'hs6': '940490', 'keywords': ['almohada', 'cojin', 'memory foam']},
            {'hs6': '020712', 'keywords': ['pollo congelado', 'aves evisceradas']},
            {'hs6': '391910', 'keywords': ['cinta adhesiva', 'cinta empaque']},
            {'hs6': '150910', 'keywords': ['aceite de oliva']},
            {'hs6': '151319', 'keywords': ['aceite de coco', 'coco virgen']},
            {'hs6': '210111', 'keywords': ['café instantáneo', 'cafe instantaneo']},
            {'hs6': '330510', 'keywords': ['champu', 'shampoo']},
            {'hs6': '844332', 'keywords': ['impresora', 'impresora térmica', 'impresora termica']},
            {'hs6': '900211', 'keywords': ['lente 50mm', 'lente de cámara', 'objetivo']},
            {'hs6': '570330', 'keywords': ['alfombra poliester', 'alfombra']},
            {'hs6': '040120', 'keywords': ['leche deslactosada', 'leche uht']},
            {'hs6': '640340', 'keywords': ['botas de seguridad', 'punta de acero']},
            {'hs6': '820590', 'keywords': ['herramienta multifuncional', 'multiherramienta']},
            {'hs6': '340220', 'keywords': ['jabón líquido', 'jabón antibacterial', 'jabon liquido']},
            {'hs6': '620520', 'keywords': ['camisa formal', 'camisa algodón', 'camisa manga larga']},
            {'hs6': '761010', 'keywords': ['ventana corrediza', 'ventana aluminio']},
            {'hs6': '854442', 'keywords': ['cable usb-c', 'usb c lightning']},
            {'hs6': '841850', 'keywords': ['refrigerador comercial', 'refrigerador industrial']},
            {'hs6': '350610', 'keywords': ['adhesivo', 'epoxico', 'adhesivo epoxico', 'pegamento epoxico']},
            {'hs6': '840721', 'keywords': ['motor fuera de borda', 'fueraborda']},
            {'hs6': '392020', 'keywords': ['stretch film', 'película stretch', 'film pallet']},
            {'hs6': '250510', 'keywords': ['arena sílica', 'arena silica']},
            {'hs6': '401519', 'keywords': ['guantes nitrilo', 'guantes desechables']},
            {'hs6': '330300', 'keywords': ['perfume', 'fragancia']},
            {'hs6': '851822', 'keywords': ['altavoz bluetooth', 'parlante bluetooth']},
            {'hs6': '852691', 'keywords': ['gps rastreo', 'dispositivo gps']},
            {'hs6': '731815', 'keywords': ['tornillo drywall', 'tornillo fosfatado']},
            {'hs6': '320890', 'keywords': ['pintura', 'pintura epoxica', 'pintura para pisos']},
            {'hs6': '190120', 'keywords': ['harina de maíz', 'harina de maiz']},
            {'hs6': '852580', 'keywords': ['cámara de seguridad', 'camara de seguridad', 'camara ip']},
            {'hs6': '845210', 'keywords': ['máquina de coser', 'maquina de coser']},
            {'hs6': '842121', 'keywords': ['purificador de agua', 'filtro de agua']},
            {'hs6': '481810', 'keywords': ['papel higiénico', 'papel sanitario']},
            {'hs6': '100510', 'keywords': ['semillas de maíz', 'semillas de maiz']},
            {'hs6': '120930', 'keywords': ['semillas de tomate', 'semilla hibrida']},
            {'hs6': '870380', 'keywords': ['vehículo eléctrico', 'vehiculo electrico']},
            {'hs6': '820520', 'keywords': ['martillo carpintero', 'martillo']},
            {'hs6': '900410', 'keywords': ['gafas de sol', 'lentes de sol']},
            {'hs6': '252329', 'keywords': ['cemento blanco']},
            {'hs6': '853669', 'keywords': ['tomacorriente', 'tomacorriente doble']},
            {'hs6': '850760', 'keywords': ['batería 18650', 'bateria 18650']},
            {'hs6': '321390', 'keywords': ['pintura acrílica', 'pintura manualidades']},
            {'hs6': '902519', 'keywords': ['termometro', 'terma', 'terma 3metro']},
            {'hs6': '630231', 'keywords': ['microfibra', 'sabanas microfibra', 'sa banas microfibra']},
            {'hs6': '570110', 'keywords': ['alfombra lana', 'alfombra natural']},
            {'hs6': '420221', 'keywords': ['bolso de cuero', 'bolso cuero']},
            {'hs6': '650500', 'keywords': ['gorro deportivo', 'gorro térmico', 'gorro termico']},
            {'hs6': '650610', 'keywords': ['bufanda', 'bufanda alpaca']},
            {'hs6': '381090', 'keywords': ['removedor', 'removedor de oxido']},
            {'hs6': '390730', 'keywords': ['resina', 'resina epoxica', 'resina epoxico', 'resina epoxica']},
            {'hs6': '380892', 'keywords': ['trampa cromatica', 'trampa adhesiva']},
            {'hs6': '380893', 'keywords': ['bioestimulante', 'extracto de algas']},
            {'hs6': '380891', 'keywords': ['insecticida', 'insecticida biológico', 'insecticida biologico']},
            {'hs6': '901819', 'keywords': ['monitor signos vitales', 'oxímetro', 'oximetro']},
            {'hs6': '871390', 'keywords': ['silla de ruedas']},
            {'hs6': '842959', 'keywords': ['retroexcavadora']},
            {'hs6': '842482', 'keywords': ['sistema de riego', 'pivote central']},
            {'hs6': '842710', 'keywords': ['carretilla elevadora', 'montacargas']},
            {'hs6': '841370', 'keywords': ['bomba centrífuga', 'bomba centrifuga']},
            {'hs6': '845819', 'keywords': ['torno', 'torno cnc']},
            {'hs6': '846721', 'keywords': ['taladro', 'taladro percutor']},
            {'hs6': '850161', 'keywords': ['generador', 'generador electrico', 'generador diesel']},
            {'hs6': '846719', 'keywords': ['pulidora', 'pulidora angular']},
            {'hs6': '721631', 'keywords': ['perfil', 'perfil estructural', 'perfil galvanizado']},
            {'hs6': '680710', 'keywords': ['membrana', 'membrana asfaltica', 'impermeabilizacion']},
            {'hs6': '820750', 'keywords': ['broca', 'carburo']},
            {'hs6': '620193', 'keywords': ['chaqueta', 'chaqueta impermeable', 'chaqueta outdoor']},
            {'hs6': '611610', 'keywords': ['guantes', 'guantes seguridad', 'guantes anticorte']},
            {'hs6': '611595', 'keywords': ['calcetines', 'calcetines deportivos', 'calcetines compresion']},
            {'hs6': '220290', 'keywords': ['bebida', 'bebida isotonica', 'bebida deportiva']},
            {'hs6': '110620', 'keywords': ['harina', 'harina almendra', 'harina de almendra']},
            {'hs6': '340220', 'keywords': ['detergente', 'detergente industrial', 'detergente enzimatico']},
            {'hs6': '321410', 'keywords': ['sellador', 'sellador poliuretanico']},
            {'hs6': '330499', 'keywords': ['serum', 'serum facial', 'crema hidratante']},
            {'hs6': '310520', 'keywords': ['fertilizante', 'fertilizante npk', 'fertilizante granular']},
            {'hs6': '380892', 'keywords': ['herbicida', 'gramineas']},
            {'hs6': '902519', 'keywords': ['termometro infrarrojo']},
            {'hs6': '401511', 'keywords': ['guantes quirurgicos', 'guantes latex']},
            {'hs6': '610910', 'keywords': ['camiseta', 'playera', 't shirt', 'remera']},
            {'hs6': '620342', 'keywords': ['pantalon mezclilla', 'jeans', 'denim']},
            {'hs6': '640219', 'keywords': ['zapatos deportivos', 'tenis deportivos']},
            {'hs6': '620113', 'keywords': ['chaqueta invierno', 'abrigo plumas']},
            {'hs6': '420221', 'keywords': ['bolso cuero', 'bolsa cuero']},
            {'hs6': '650500', 'keywords': ['gorra algodon', 'gorro baseball']},
            {'hs6': '090121', 'keywords': ['cafe en grano', 'café tostado']},
            {'hs6': '090220', 'keywords': ['te verde', 'té verde']},
            {'hs6': '090240', 'keywords': ['te negro', 'té negro', 'earl grey']},
            {'hs6': '150910', 'keywords': ['aceite oliva extra virgen', 'aceite prensado']},
            {'hs6': '180632', 'keywords': ['chocolate negro', 'tableta chocolate']},
            {'hs6': '200799', 'keywords': ['mermelada', 'mermelada fresa']},
            {'hs6': '220300', 'keywords': ['cerveza', 'cerveza artesanal']},
            {'hs6': '220421', 'keywords': ['vino tinto', 'vino reserva']},
            {'hs6': '210310', 'keywords': ['salsa soja', 'soya japonesa']},
            {'hs6': '220900', 'keywords': ['vinagre balsamico', 'vinagre']},
            {'hs6': '040900', 'keywords': ['miel de abeja', 'miel eucalipto']},
            {'hs6': '210111', 'keywords': ['cafe instantaneo', 'café soluble']},
            {'hs6': '210120', 'keywords': ['te instantaneo', 'té instantáneo', 'mezcla instantanea de te']},
            {'hs6': '330300', 'keywords': ['perfume', 'fragancia', 'eau de parfum']},
            {'hs6': '960910', 'keywords': ['lapices colores', 'lapiz grafito']},
            {'hs6': '960810', 'keywords': ['boligrafo', 'bolígrafo tinta']},
            {'hs6': '482010', 'keywords': ['cuaderno', 'libreta']},
            {'hs6': '320910', 'keywords': ['pintura acrilica', 'pintura manualidades']},
            {'hs6': '350610', 'keywords': ['pegamento termofusible', 'adhesivo hot melt']},
            {'hs6': '902519', 'keywords': ['termometro digital', 'termometro clinico']},
            {'hs6': '901890', 'keywords': ['tensiómetro', 'tensiometro', 'oximetro']},
            {'hs6': '901831', 'keywords': ['jeringa', 'jeringas desechables']},
            {'hs6': '630790', 'keywords': ['mascarilla', 'mascarilla quirurgica', 'n95']},
            {'hs6': '820130', 'keywords': ['pala jardin', 'herramienta jardineria']},
            {'hs6': '391739', 'keywords': ['manguera riego', 'manguera expandible']},
            {'hs6': '691490', 'keywords': ['maceta terracota', 'maceta barro']},
            {'hs6': '820150', 'keywords': ['tijeras de podar', 'podadora manual']},
            {'hs6': '842123', 'keywords': ['filtro aceite', 'filtro motor']},
            {'hs6': '870830', 'keywords': ['pastillas freno', 'freno disco']},
            {'hs6': '271019', 'keywords': ['aceite motor', 'lubricante sintético']},
            {'hs6': '851110', 'keywords': ['bujia', 'bujia encendido']},
            {'hs6': '841330', 'keywords': ['bomba combustible', 'bomba gasolina']},
            {'hs6': '382000', 'keywords': ['liquido refrigerante', 'coolant']},
            {'hs6': '846729', 'keywords': ['destornillador electrico', 'atornillador']},
            {'hs6': '960321', 'keywords': ['cepillo de dientes', 'cepillo dental']},
            {'hs6': '330610', 'keywords': ['pasta dental', 'dentifrico', 'crema dental']},
            {'hs6': '340130', 'keywords': ['jabon antibacterial', 'jabón antibacterial', 'jabón liquido']},
            {'hs6': '481820', 'keywords': ['toallas de papel', 'rollos cocina']},
            {'hs6': '392410', 'keywords': ['esponja cocina', 'espatula silicona', 'espátula cocina']},
            {'hs6': '732393', 'keywords': ['olla acero', 'termo acero', 'termo inoxidable']},
            {'hs6': '761510', 'keywords': ['sarten antiadherente', 'bandeja aluminio']},
            {'hs6': '691110', 'keywords': ['plato ceramica', 'plato cerámica']},
            {'hs6': '701349', 'keywords': ['vaso vidrio', 'vaso templado']},
            {'hs6': '821192', 'keywords': ['cuchillo cocina', 'cuchillo chef']},
            {'hs6': '821300', 'keywords': ['tijeras multiusos', 'tijera multiusos']},
            {'hs6': '392330', 'keywords': ['botella deportiva', 'botella plastico']},
            {'hs6': '950662', 'keywords': ['balon baloncesto', 'balón baloncesto']},
            {'hs6': '851310', 'keywords': ['linterna led', 'linterna mano']},
            {'hs6': '854370', 'keywords': ['bombillo led', 'bombilla led']},
            {'hs6': '392490', 'keywords': ['cortina baño', 'cortina de baño']},
            {'hs6': '570500', 'keywords': ['tapete baño', 'alfombra baño']},
            {'hs6': '732399', 'keywords': ['estante metalico', 'organizador metalico']},
            {'hs6': '392310', 'keywords': ['caja plastica', 'organizador plastico']},
            {'hs6': '660191', 'keywords': ['paraguas', 'sombrilla']},
            {'hs6': '420292', 'keywords': ['mochila nylon', 'mochila deporte']},
            {'hs6': '420321', 'keywords': ['cinturon sintetico', 'cinturón sintético']},
            {'hs6': '711711', 'keywords': ['pulsera acero', 'pulsera inoxidable']},
            {'hs6': '650400', 'keywords': ['sombrero paja', 'sombrero natural']},
            {'hs6': '701399', 'keywords': ['jarron decorativo', 'florero vidrio']},
            {'hs6': '441400', 'keywords': ['portarretratos', 'marco foto']},
            {'hs6': '320820', 'keywords': ['pintura aerosol', 'spray pintura']},
            {'hs6': '391910', 'keywords': ['cinta adhesiva transparente', 'cinta cristal']},
            {'hs6': '847290', 'keywords': ['grapadora', 'perforadora']},
            {'hs6': '482030', 'keywords': ['carpeta plastica', 'carpeta tamaño carta']},
            {'hs6': '901380', 'keywords': ['lupa de mano', 'lupa 3x']},
            {'hs6': '560749', 'keywords': ['cuerda de salto', 'soga de salto']},
            {'hs6': '732410', 'keywords': ['colador metalico', 'colador malla']},
            {'hs6': '960720', 'keywords': ['cremallera', 'zipper']},
            {'hs6': '731990', 'keywords': ['aguja coser', 'agujas de coser']},
            {'hs6': '550810', 'keywords': ['hilo poliester', 'hilo poliéster']},
            {'hs6': '940520', 'keywords': ['lampara escritorio', 'lámpara escritorio']},
            {'hs6': '940370', 'keywords': ['mesa plegable', 'mesa plastica plegable']},
            {'hs6': '940161', 'keywords': ['silla comedor', 'silla madera']},
            {'hs6': '732690', 'keywords': ['caja herramientas', 'caja metálica herramientas']},
            {'hs6': '820412', 'keywords': ['llave inglesa', 'llave ajustable']},
            {'hs6': '701349', 'keywords': ['vaso vidrio templado']},
            {'hs6': '691490', 'keywords': ['maceta terracota', 'maceta barro']},
            {'hs6': '392330', 'keywords': ['botella deportiva plastico']},
            {'hs6': '392330', 'keywords': ['termo plastico', 'botella gym']},
            {'hs6': '841810', 'keywords': ['refrigerador', 'nevara', 'nevera']},
            {'hs6': '845020', 'keywords': ['lavadora', 'lavadora automática']},
            {'hs6': '851650', 'keywords': ['microondas', 'horno microondas']},
            {'hs6': '850910', 'keywords': ['aspiradora', 'aspiradora robot']},
            {'hs6': '841510', 'keywords': ['aire acondicionado', 'split 12000 btu']},
            {'hs6': '850940', 'keywords': ['licuadora', 'batidora de mano']},
            {'hs6': '851640', 'keywords': ['plancha de vapor', 'plancha de ropa']},
            {'hs6': '851632', 'keywords': ['plancha de pelo', 'alisadora']},
            {'hs6': '851671', 'keywords': ['cafetera espresso', 'cafetera espresso manual']},
            {'hs6': '841451', 'keywords': ['ventilador de techo', 'ventilador']},
            {'hs6': '842139', 'keywords': ['purificador de aire', 'purificador hepa']},
            {'hs6': '252329', 'keywords': ['cemento portland', 'cemento tipo i']},
            {'hs6': '690410', 'keywords': ['ladrillo ceramico', 'ladrillo hueco']},
            {'hs6': '846721', 'keywords': ['taladro inalambrico', 'taladro inalámbrico']},
            {'hs6': '820520', 'keywords': ['martillo carpintero']},
            {'hs6': '820540', 'keywords': ['destornillador phillips']},
            {'hs6': '901780', 'keywords': ['cinta metrica', 'cinta métrica']},
            {'hs6': '850152', 'keywords': ['motor electrico trifasico', 'motor eléctrico trifásico']},
            {'hs6': '848180', 'keywords': ['valvula compuerta', 'válvula compuerta']},
            {'hs6': '854449', 'keywords': ['cable electrico cobre', 'cable eléctrico cobre']},
            {'hs6': '850421', 'keywords': ['transformador distribucion', 'transformador distribución']},
            {'hs6': '870380', 'keywords': ['automovil electrico', 'vehiculo electrico']},
            {'hs6': '871150', 'keywords': ['motocicleta 250cc', 'moto 250cc']},
        ]

        self._fallback_use_map = {
            'computo': '847130',
            'electronica': '852872',
            'electricidad': '853669',
            'construccion': '680790',
            'ferreteria': '820559',
            'industrial': '847989',
            'alimentario': '190590',
            'bebidas': '220290',
            'consumo_humano': '210111',
            'bebida_listo_consumo': '220300',
            'vestir': '610910',
            'agro': '380892',
            'agricola': '310520',
            'jardin': '820150',
            'quimicos': '380899',
            'cosmeticos': '330499',
            'salud': '901890',
            'medico': '901819',
            'escritura': '482010',
            'cuidado_personal': '330300',
            'medicion_medica': '902519',
            'automotriz': '870830',
            'semilla': '120930',
            'fertilizante': '310520',
            'implemento_riego': '391739',
            'recipiente_jardin': '691490',
            'herramienta_agricola': '820150',
            'producto_agricola': '310520',
            'higiene': '330610',
            'limpieza': '340130',
            'cocina': '732393',
            'hogar': '392310',
            'deportes': '950662',
            'oficina': '847290',
            'decoracion': '701399',
            'iluminacion': '940520',
            'banio': '392490',
            'muebles': '940370',
            'accesorios': '660191',
            'precision': '901380',
            'adhesivos': '350610',
            'mercearia': '960720',
            'envase': '392330',
            'juguetes': '950300',
            'hogar_electrico': '841810',
            'industrial_maquinaria': '841370',
            'material_construccion': '252329',
        }
        
        # Reglas específicas para productos comunes
        self._MONOPOLY_CODES = {"8471300000", "8471600000", "8528720000", "8518300000", "8413700000"}
        self._CODE_TYPE_GUARDS = {
            "2101110000": {"blocked_types": {'semilla', 'fertilizante', 'producto_agricola', 'papeleria', 'producto_medico', 'repuesto_automotriz', 'ropa_textil'}},
            "8528720000": {"blocked_types": {'alimento_bebida', 'bebida', 'bebida_instantanea', 'semilla', 'fertilizante', 'producto_agricola', 'condimento_salsa', 'papeleria', 'ropa_textil'}},
            "7207110000": {"blocked_types": {'alimento_bebida', 'bebida', 'semilla', 'fertilizante', 'producto_agricola', 'papeleria', 'perfume_cosmetico', 'ropa_textil', 'electrodomestico'}},
            "8711100000": {"blocked_types": {'alimento_bebida', 'bebida', 'semilla', 'fertilizante', 'producto_agricola', 'papeleria', 'producto_medico'}},
            "6109100000": {"blocked_types": {'alimento_bebida', 'bebida', 'semilla', 'fertilizante', 'producto_agricola', 'condimento_salsa', 'producto_medico'}},
            "0902200000": {"blocked_types": {'semilla', 'fertilizante', 'producto_agricola', 'implemento_riego', 'recipiente_jardin', 'herramienta_agricola', 'ropa_textil', 'electrodomestico'}},
            "0902400000": {"blocked_types": {'semilla', 'fertilizante', 'producto_agricola'}},
            "1905000000": {"blocked_types": {'ropa_textil', 'calzado', 'accesorio_personal', 'producto_cocina_menaje', 'implemento_riego', 'herramienta_agricola'}},
            "1905": {"blocked_types": {'ropa_textil', 'calzado', 'accesorio_personal', 'producto_cocina_menaje', 'implemento_riego', 'herramienta_agricola'}},
            "9608100000": {"blocked_types": {'ropa_textil', 'calzado', 'producto_bano', 'juguete'}},
            "960810": {"blocked_types": {'ropa_textil', 'calzado', 'producto_bano', 'juguete'}},
        }
        self._TYPE_EXPECTED_CHAPTERS = {
            'alimento_bebida': {'04', '09', '15', '18', '19', '20', '21', '22'},
            'alimento': {'04', '09', '15', '18', '19', '20', '21', '22'},
            'bebida': {'22'},
            'bebida_instantanea': {'21', '22'},
            'condimento_salsa': {'21', '22'},
            'producto_lacteo_miel': {'04'},
            'semilla': {'12'},
            'fertilizante': {'31'},
            'producto_agricola': {'12', '31', '39', '69', '82'},
            'implemento_riego': {'39'},
            'recipiente_jardin': {'69'},
            'herramienta_agricola': {'82'},
            'bebida_listo_consumo': {'22'},
            'higiene_personal': {'33', '96'},
            'limpieza_hogar': {'34', '39'},
            'producto_cocina_menaje': {'73', '76', '69', '70', '82'},
            'hogar_organizador': {'39', '73'},
            'accesorio_personal': {'42', '65', '66', '71'},
            'deporte_accesorio': {'95', '63'},
            'iluminacion': {'85', '94'},
            'producto_bano': {'39', '57', '70'},
            'decoracion': {'69', '70', '44'},
            'adhesivo_quimico': {'35', '32'},
            'papeleria_avanzada': {'48', '96', '82'},
            'herramienta_ligera': {'82'},
            'herramienta_electrica_ligera': {'84', '85'},
            'oficina_equipo': {'84', '96', '48'},
            'mueble_hogar': {'94'},
            'mercearia': {'96', '73'},
            'envase_recipient': {'39', '70', '42'},
            'precision_optica': {'90'},
            'juguete': {'95'},
            'electrodomestico': {'84', '85'},
            'maquinaria_industrial': {'84', '85', '90'},
            'material_construccion': {'25', '68', '69', '72'},
        }

        self.specific_rules = {
            'laptop': {'hs6': '847130', 'national_code': '8471300000', 'title': 'Máquinas automáticas para procesamiento de datos, portátiles'},
            'computadora portatil': {'hs6': '847130', 'national_code': '8471300000', 'title': 'Máquinas automáticas para procesamiento de datos, portátiles'},
            'notebook': {'hs6': '847130', 'national_code': '8471300000', 'title': 'Máquinas automáticas para procesamiento de datos, portátiles'},
            'smartphone': {'hs6': '851712', 'national_code': '8517120000', 'title': 'Teléfonos inteligentes'},
            'telefono movil': {'hs6': '851712', 'national_code': '8517120000', 'title': 'Teléfonos inteligentes'},
            'celular': {'hs6': '851712', 'national_code': '8517120000', 'title': 'Teléfonos inteligentes'},
            'tablet': {'hs6': '847130', 'national_code': '8471300000', 'title': 'Máquinas automáticas para procesamiento de datos, portátiles'},
            'ipad': {'hs6': '847130', 'national_code': '8471300000', 'title': 'Máquinas automáticas para procesamiento de datos, portátiles'},
            'monitor': {'hs6': '852872', 'national_code': '8528720000', 'title': 'Monitores de visualización'},
            'pantalla': {'hs6': '852872', 'national_code': '8528720000', 'title': 'Monitores de visualización'},
            'televisor': {'hs6': '852872', 'national_code': '8528720000', 'title': 'Monitores de visualización'},
            'tv': {'hs6': '852872', 'national_code': '8528720000', 'title': 'Monitores de visualización'},
            'mouse': {'hs6': '847160', 'national_code': '8471600000', 'title': 'Dispositivos de entrada para máquinas automáticas de procesamiento de datos'},
            'teclado': {'hs6': '847160', 'national_code': '8471600000', 'title': 'Dispositivos de entrada para máquinas automáticas de procesamiento de datos'},
            'auriculares': {'hs6': '851830', 'national_code': '8518300000', 'title': 'Auriculares y micrófonos'},
            'parlantes': {'hs6': '851822', 'national_code': '8518220000', 'title': 'Altavoces múltiples, montados en un chasis común'},
            'altavoces': {'hs6': '851822', 'national_code': '8518220000', 'title': 'Altavoces múltiples, montados en un chasis común'},
            'impresora': {'hs6': '844332', 'national_code': '8443320000', 'title': 'Impresoras láser'},
            'café': {'hs6': '090111', 'national_code': '0901110000', 'title': 'Café sin tostar, sin descafeinar'},
            'cafe': {'hs6': '090111', 'national_code': '0901110000', 'title': 'Café sin tostar, sin descafeinar'},
            'leche': {'hs6': '040110', 'national_code': '0401100000', 'title': 'Leche entera'},
            'pan': {'hs6': '1905', 'national_code': '1905000000', 'title': 'Pan y productos de panadería'},
            'arroz': {'hs6': '100630', 'national_code': '1006300000', 'title': 'Arroz blanco pulido'},
            'azucar': {'hs6': '170114', 'national_code': '1701140000', 'title': 'Azúcar de caña'},
            'aceite': {'hs6': '150910', 'national_code': '1509100000', 'title': 'Aceite de oliva'},
            'agua': {'hs6': '220110', 'national_code': '2201100000', 'title': 'Agua mineral'},
            'cerveza': {'hs6': '220300', 'national_code': '2203000000', 'title': 'Cerveza de malta'},
            'vino': {'hs6': '220421', 'national_code': '2204210000', 'title': 'Vino tinto'},
            'ropa': {'hs6': '610910', 'national_code': '6109100000', 'title': 'Camisetas de algodón'},
            'zapatos': {'hs6': '640399', 'national_code': '6403990000', 'title': 'Zapatos deportivos'},
            'automovil electrico': {'hs6': '870380', 'national_code': '8703800000', 'title': 'Automóviles eléctricos'},
            'automovil': {'hs6': '870323', 'national_code': '8703230000', 'title': 'Automóviles de cilindrada entre 1000 y 1500 cm³'},
            'carro': {'hs6': '870323', 'national_code': '8703230000', 'title': 'Automóviles de cilindrada entre 1000 y 1500 cm³'},
            'moto': {'hs6': '871150', 'national_code': '8711500000', 'title': 'Motocicletas con cilindrada superior a 125 cm³'},
            'motocicleta': {'hs6': '871150', 'national_code': '8711500000', 'title': 'Motocicletas con cilindrada superior a 125 cm³'},
            'motocicleta 250cc': {'hs6': '871150', 'national_code': '8711500000', 'title': 'Motocicletas de cilindrada intermedia'},
            'bicicleta': {'hs6': '871200', 'national_code': '8712000000', 'title': 'Bicicletas'},
            'medicamento': {'hs6': '300490', 'national_code': '3004900000', 'title': 'Medicamentos'},
            'vacuna': {'hs6': '300220', 'national_code': '3002200000', 'title': 'Vacunas'},
            'libro': {'hs6': '490199', 'national_code': '4901990000', 'title': 'Libros impresos'},
            'papel': {'hs6': '480100', 'national_code': '4801000000', 'title': 'Papel para periódicos'},
            'madera': {'hs6': '440710', 'national_code': '4407100000', 'title': 'Madera aserrada de coníferas'},
            'hierro': {'hs6': '720711', 'national_code': '7207110000', 'title': 'Hierro o acero sin alear'},
            'acero': {'hs6': '720711', 'national_code': '7207110000', 'title': 'Hierro o acero sin alear'},
            'olla': {'hs6': '732393', 'national_code': '7323930000', 'title': 'Artículos de cocina de acero inoxidable'},
            'sarten': {'hs6': '761510', 'national_code': '7615100000', 'title': 'Artículos domésticos de aluminio'},
            'sartén': {'hs6': '761510', 'national_code': '7615100000', 'title': 'Artículos domésticos de aluminio'},
            'plato': {'hs6': '691110', 'national_code': '6911100000', 'title': 'Platos de cerámica'},
            'vaso': {'hs6': '701349', 'national_code': '7013490000', 'title': 'Vasos de vidrio'},
            'cuchillo de cocina': {'hs6': '821192', 'national_code': '8211920000', 'title': 'Cuchillos de cocina'},
            'tijeras multiusos': {'hs6': '821300', 'national_code': '8213000000', 'title': 'Tijeras'},
            'botella deportiva': {'hs6': '392330', 'national_code': '3923300000', 'title': 'Botellas y similares de plástico'},
            'estante metálico': {'hs6': '732399', 'national_code': '7323990000', 'title': 'Estantes/soportes de hierro o acero'},
            'caja plastica': {'hs6': '392310', 'national_code': '3923100000', 'title': 'Cajas y contenedores plásticos'},
            'paraguas': {'hs6': '660191', 'national_code': '6601910000', 'title': 'Paraguas plegables'},
            'mochila': {'hs6': '420292', 'national_code': '4202920000', 'title': 'Mochilas y bolsos con asas externas'},
            'cinturon': {'hs6': '420321', 'national_code': '4203210000', 'title': 'Cinturones de materia sintética'},
            'cinturón': {'hs6': '420321', 'national_code': '4203210000', 'title': 'Cinturones de materia sintética'},
            'pulsera': {'hs6': '711711', 'national_code': '7117110000', 'title': 'Bisutería de metal común'},
            'sombrero de paja': {'hs6': '650400', 'national_code': '6504000000', 'title': 'Sombreros de paja'},
            'plastico': {'hs6': '390110', 'national_code': '3901100000', 'title': 'Polietileno'},
            'vidrio': {'hs6': '700100', 'national_code': '7001000000', 'title': 'Vidrio en bruto'},
            'cemento': {'hs6': '252310', 'national_code': '2523100000', 'title': 'Cemento Portland'},
            'arena': {'hs6': '250510', 'national_code': '2505100000', 'title': 'Arena silícea'},
            'piedra': {'hs6': '251511', 'national_code': '2515110000', 'title': 'Piedra caliza'},
            'petroleo': {'hs6': '270900', 'national_code': '2709000000', 'title': 'Petróleo crudo'},
            'gasolina': {'hs6': '271012', 'national_code': '2710120000', 'title': 'Gasolina'},
            'gasoleo': {'hs6': '271019', 'national_code': '2710190000', 'title': 'Gasóleo'},
            'electricidad': {'hs6': '271600', 'national_code': '2716000000', 'title': 'Energía eléctrica'},
            # Productos de construcción
            'ladrillo': {'hs6': '690410', 'national_code': '6904100000', 'title': 'Ladrillos de construcción'},
            'cemento portland': {'hs6': '252329', 'national_code': '2523290000', 'title': 'Cemento Portland'},
            'yeso': {'hs6': '252010', 'national_code': '2520100000', 'title': 'Yeso natural'},
            # Herramientas y maquinaria
            'motocicleta': {'hs6': '871110', 'national_code': '8711100000', 'title': 'Motocicletas con motor de cilindrada no superior a 50 cm³'},
            'pala': {'hs6': '820120', 'national_code': '8201200000', 'title': 'Palas de excavación'},
            'martillo': {'hs6': '820520', 'national_code': '8205200000', 'title': 'Martillos'},
            # Textiles y calzado
            'zapato': {'hs6': '640399', 'national_code': '6403990000', 'title': 'Zapatos deportivos'},
            'calzado': {'hs6': '640399', 'national_code': '6403990000', 'title': 'Zapatos deportivos'},
            # Electrónica y energía
            'panel solar': {'hs6': '854140', 'national_code': '8541400000', 'title': 'Células fotovoltaicas'},
            'placa solar': {'hs6': '854140', 'national_code': '8541400000', 'title': 'Células fotovoltaicas'},
            # Motor y transporte
            'motor diesel': {'hs6': '840820', 'national_code': '8408200000', 'title': 'Motores diésel'},
            'motor gasolina': {'hs6': '840790', 'national_code': '8407900000', 'title': 'Motores de encendido por chispa'},
        }
        # Configuración dinámica cargada a partir de reportes de test masivo
        self._dynamic_adjustments: Dict[str, Any] = {}
        self._dynamic_config = self._base_dynamic_config()
        self._dynamic_report_mtime: float | None = None
        self._refresh_dynamic_adjustments()
    
    def classify(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Método principal de clasificación que ejecuta el flujo completo del sistema ClasifiCode.
        
        Args:
            case (Dict[str, Any]): Diccionario con datos del caso a clasificar
                
        Returns:
            Dict[str, Any]: Diccionario con resultado completo de la clasificación
        """
        start_time = datetime.now()
        
        try:
            # Construir texto usando título + descripción completos
            title_text = case.get('product_title') or case.get('title') or case.get('product_name') or ''
            desc_text = case.get('product_desc') or case.get('product_description') or case.get('description') or ''
            raw_text = case.get('text') or ''
            text = " ".join(part.strip() for part in [title_text, desc_text, raw_text] if part and part.strip())

            if not text or len(text.strip()) < 4:
                return self._create_error_result(
                    case['id'], 
                    "Descripción insuficiente para clasificación",
                    start_time
                )
            
            # Preprocesar texto
            text_processed = self._preprocess_text(text)
            
            # Extraer características contextuales
            features = self._extract_features(text_processed)
            features_old = self._extract_features(text)
            features.update(features_old)

            # Intentar reglas específicas primero
            specific_result = self._try_specific_rules(text_processed)
            if specific_result:
                return self._process_specific_rule_result(
                    case, specific_result, features, start_time, text_processed
                )
            
            # Ejecutar motor RGI
            rgi_result = rgi_apply_all(text, [], features=features)
            hs6 = rgi_result.get('hs6')
            trace = rgi_result.get('trace', [])
            
            if not hs6:
                hs6 = self._fallback_hs6(text_processed if text_processed else text, features)
                if hs6:
                    trace.append({'rgi': 'fallback_embedding', 'decision': f'HS6 determinado por embeddings: {hs6}'})
            
            if not hs6:
                return self._create_error_result(
                    case['id'], 
                    "No se pudo determinar un HS6",
                    start_time,
                    trace=trace,
                    features=features
                )
            
            # Buscar aperturas nacionales
            attrs = self._get_attrs_for_hs6(hs6)
            options = self._get_national_options(hs6, attrs)

            if not options:
                return self._create_error_result(
                    case['id'], 
                    "Sin apertura nacional",
                    start_time,
                    hs6=hs6,
                    trace=trace,
                    features=features
                )
            
            # Calcular scores combinados para candidatos y ordenarlos
            weight_config = self._dynamic_config.get('weights', {'semantic': 0.30, 'lexical': 0.25, 'rgi': 0.45})
            best_candidate, options_sorted = self._select_best_candidate(
                text_processed,
                options,
                features,
                attrs,
                weight_config,
                self._dynamic_config.get('suspect_penalties', {})
            )
            
            if not options_sorted:
                return self._create_error_result(
                    case['id'], 
                    "No se pudo seleccionar candidato",
                    start_time,
                    hs6=hs6,
                    trace=trace,
                    features=features
                )
            
            chosen_option = best_candidate or options_sorted[0]
            second_option = options_sorted[1] if len(options_sorted) > 1 else None
            chosen = chosen_option.copy()
            
            weight_semantic = weight_config.get('semantic', 0.30)
            weight_lexical = weight_config.get('lexical', 0.25)
            weight_rgi = weight_config.get('rgi', 0.45)
            min_semantic_threshold = self._dynamic_config.get('min_semantic', 0.60)
            max_suspect_conf = self._dynamic_config.get('max_suspect_conf', 0.65)
            suspect_margin = 0.05
            
            national_code = str(chosen.get('national_code', '')).strip()
            title = chosen.get('title') or chosen.get('description') or ''
            score_semantic = chosen.get('semantic_score_adjusted', chosen.get('semantic_score', 0.0))
            score_lexical = chosen.get('lexical_score', 0.0)
            score_rgi = chosen.get('contextual_score', self._calculate_contextual_score(national_code, features))
            
            # Reemplazo si el mejor candidato es sospechoso pero el segundo es competitivo
            if self._is_suspect_code(national_code) and second_option:
                second_semantic = second_option.get('semantic_score_adjusted', second_option.get('semantic_score', 0.0))
                if score_semantic < second_semantic + suspect_margin:
                    second_code = str(second_option.get('national_code', '')).strip()
                    second_coherence = self._chapter_coherence_check(second_code, features, text_processed)
                    if second_coherence and second_semantic >= 0.60:
                        logging.info(
                            f"Caso {case['id']}: Reemplazo de código sospechoso {national_code} por {second_code} "
                            f"(similaridad {score_semantic:.2f} vs {second_semantic:.2f})"
                        )
                        chosen = second_option.copy()
                        national_code = second_code
                        title = chosen.get('title') or chosen.get('description') or ''
                        score_semantic = second_semantic
                        score_lexical = chosen.get('lexical_score', 0.0)
                        score_rgi = chosen.get('contextual_score', self._calculate_contextual_score(national_code, features))
                        options_sorted = [second_option] + [opt for opt in options_sorted if opt is not second_option]
            
            score_total = (
                weight_semantic * score_semantic +
                weight_lexical * score_lexical +
                weight_rgi * score_rgi
            )
            confidence_raw = float(max(0.0, min(1.0, score_total)))
            
            validation_result = self._validate_classification_consistency(
                features, national_code or hs6 or '', title
            )
            validation_penalty = 0.2 * (1.0 - validation_result['validation_score'])
            
            chapter_coherence = self._chapter_coherence_check(national_code, features, text_processed)
            is_suspect = self._is_suspect_code(national_code)
            max_semantic = max(opt.get('semantic_score', 0.0) for opt in options_sorted)
            
            meta = chosen.get('meta', {}) or {}
            keyword_hits = meta.get('keyword_hits', 0)
            note_hits = meta.get('note_hits', 0)
            
            final_confidence = confidence_raw
            review_notes: List[str] = []
            chosen.setdefault('meta', {})

            if score_semantic < min_semantic_threshold:
                review_notes.append('semantic_threshold_low')
                final_confidence = min(final_confidence, 0.45)

            if keyword_hits < 1 and note_hits <= 0:
                review_notes.append('low_evidence')
                final_confidence = max(0.0, final_confidence - 0.05)

            final_confidence = max(0.0, final_confidence - validation_penalty)

            suspect_min_semantic = self._dynamic_config.get('suspect_min_semantic', min_semantic_threshold)

            if not chapter_coherence:
                review_notes.append('chapter_incoherent')
                final_confidence = max(0.0, min(final_confidence, 0.2))
                logging.warning(f"Caso {case['id']}: Incoherencia detectada, confianza contenida por revisión obligatoria")

            if is_suspect:
                final_confidence = min(final_confidence, max_suspect_conf)
                if 'suspect_code' not in review_notes:
                    review_notes.append('suspect_code')
                if score_semantic < suspect_min_semantic:
                    review_notes.append('suspect_low_semantic')
                    final_confidence = min(final_confidence, 0.50)
                if national_code == '8471300000' and score_semantic < 0.70:
                    review_notes.append('hs847130_watchlist')
                    final_confidence = min(final_confidence, 0.62)
            else:
                if max_semantic < min_semantic_threshold and 'no_semantic_candidate' not in review_notes:
                    review_notes.append('no_semantic_candidate')
                    final_confidence = min(final_confidence, 0.45)

            if chapter_coherence and not is_suspect and not review_notes and score_total >= 0.70:
                boosted_conf = max(0.72, min(0.78, round(score_total, 2)))
                final_confidence = boosted_conf
                logging.info(f"Caso {case['id']}: Cobertura automática aplicada - confianza ajustada a {boosted_conf}")

            requires_review, final_confidence, review_notes = self._evaluate_review_policy(
                chapter_coherence=chapter_coherence,
                is_suspect=is_suspect,
                final_confidence=final_confidence,
                validation_result=validation_result,
                keyword_hits=keyword_hits,
                note_hits=note_hits,
                review_notes=review_notes
            )

            if review_notes:
                chosen['review_notes'] = review_notes

            # Guardar candidato
            self._save_candidate(case['id'], national_code, hs6, title, final_confidence, trace, validation_result, features)
            
            # Registrar métricas (incluyendo requires_review)
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            self._record_metrics(case['id'], final_confidence, response_time, validation_result['validation_score'], requires_review=requires_review)
            
            # Registrar para validación incremental
            self._record_incremental_validation(
                case_id=case['id'],
                duration=response_time,
                national_code=national_code,
                validation_result=validation_result,
                method='rgi',
                confidence=final_confidence,
                is_suspect=is_suspect,
                requires_review=requires_review
            )
            
            # Construir rationale detallado (incluyendo nuevas validaciones)
            rationale = self._build_detailed_rationale(features, trace, chosen, validation_result, chapter_coherence, is_suspect, requires_review)
            
            # Feedback automático para baja confianza o casos que requieren revisión
            if final_confidence < 0.6 or requires_review:
                self._register_automatic_feedback(
                    case_id=case['id'],
                    input_text=text,
                    predicted_code=national_code,
                    confidence=final_confidence,
                    rationale=rationale,
                    requires_review=requires_review,
                    validation_result=validation_result
                )

            return {
                'case_id': case['id'],
                'hs6': hs6,
                'national_code': national_code,
                'title': title,
                'confidence': final_confidence,
                'rationale': rationale,
                'validation_flags': validation_result,
                'features': features,
                'method': 'rgi',
                'response_time': response_time,
                'topK': self._get_top_candidates(options_sorted, text_processed, features)
            }
            
        except ValueError as e:
            # Error de validación de texto (texto muy corto, vacío, etc.)
            return self._create_error_result(
                case['id'], 
                str(e),
                start_time
            )
            
        except Exception as e:
            # Error general durante la clasificación
            logging.exception(f"Error en clasificación para caso {case['id']}: {str(e)}")
            return self._create_error_result(
                case['id'], 
                f'Error interno: {str(e)}',
                start_time
            )
    
    def _create_error_result(self, case_id: int, error_msg: str, start_time: datetime, **kwargs) -> Dict[str, Any]:
        """Crea un resultado de error estandarizado."""
        return {
            'case_id': case_id,
            'hs6': kwargs.get('hs6'),
            'national_code': None,
            'title': None,
            'confidence': 0.0,
            'rationale': {
                'error': error_msg,
                'requires_review': True,
                'trace': kwargs.get('trace', []),
                'features': kwargs.get('features', {})
            },
            'validation_flags': {},
            'features': kwargs.get('features', {}),
            'method': 'error',
            'response_time': (datetime.now() - start_time).total_seconds(),
            'topK': []
        }
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocesa el texto para mejorar la clasificación."""
        if not text:
            return ""
        
        # Normalizar texto
        text = unicodedata.normalize('NFKD', text.lower().strip())
        
        # Remover caracteres especiales pero mantener espacios
        text = ''.join(c if c.isalnum() or c.isspace() else ' ' for c in text)
        
        # Limpiar espacios múltiples
        text = ' '.join(text.split())
        
        return text
    
    def _extract_features(self, text: str) -> Dict[str, Any]:
        """Extrae características contextuales del texto."""
        features = {
            'tipo_de_bien': 'producto_terminado',
            'uso_principal': 'general',
            'nivel_procesamiento': 'terminado',
            'material_principal': 'no_especificado',
            'es_instantaneo': False,
            'es_bebida_listo_consumo': False,
            'es_semilla': False,
            'es_fertilizante': False
        }
        
        text_lower = text.lower()
        tipo_asignado = False
        
        def contains(words):
            return any(word in text_lower for word in words)
        
        # Marcos semilla / fertilizante / agrícola
        if contains(['semilla', 'semillas', 'germinacion', 'germinación', 'híbrido', 'hibrido', 'siembra']):
            features['tipo_de_bien'] = 'semilla'
            features['uso_principal'] = 'agricola'
            features['es_semilla'] = True
            tipo_asignado = True
        elif contains(['fertilizante', 'npk', 'liberacion controlada', 'liberación controlada', '15-15-15', '15 15 15', '8-3-5', '8 3 5', 'granular', 'abonado']):
            features['tipo_de_bien'] = 'fertilizante'
            features['uso_principal'] = 'agricola'
            features['es_fertilizante'] = True
            tipo_asignado = True
        elif contains(['manguera', 'riego', 'aspersor', 'goteo']):
            features['tipo_de_bien'] = 'implemento_riego'
            features['uso_principal'] = 'agricola'
            tipo_asignado = True
        elif contains(['maceta', 'terracota', 'macetero', 'jardinera']):
            features['tipo_de_bien'] = 'recipiente_jardin'
            features['uso_principal'] = 'jardin'
            tipo_asignado = True
        elif contains(['tijera de podar', 'tijeras de podar', 'podadora', 'herramienta jardin', 'corte de ramas']):
            features['tipo_de_bien'] = 'herramienta_agricola'
            features['uso_principal'] = 'jardin'
            tipo_asignado = True
        elif contains(['horticola', 'hortícola', 'jardin', 'jardín']):
            features['tipo_de_bien'] = 'producto_agricola'
            features['uso_principal'] = 'jardin'
            tipo_asignado = True
        elif contains(['cemento', 'ladrillo', 'arena', 'varilla', 'tuberia', 'perfil estructural']) and not tipo_asignado:
            features['tipo_de_bien'] = 'material_construccion'
            features['uso_principal'] = 'construccion'
            tipo_asignado = True
        elif contains(['refrigerador', 'lavadora', 'microondas', 'aspiradora', 'licuadora', 'plancha', 'aire acondicionado', 'ventilador', 'cafetera', 'purificador']) and not tipo_asignado:
            features['tipo_de_bien'] = 'electrodomestico'
            features['uso_principal'] = 'hogar_electrico'
            tipo_asignado = True
        elif contains(['motor electrico', 'motor eléctrico', 'bomba', 'válvula', 'valvula', 'transformador', 'cable electrico', 'cable eléctrico']) and not tipo_asignado:
            features['tipo_de_bien'] = 'maquinaria_industrial'
            features['uso_principal'] = 'industrial'
            tipo_asignado = True
        elif contains(['cepillo de dientes', 'crema dental', 'pasta dental', 'higiene bucal']) and not tipo_asignado:
            features['tipo_de_bien'] = 'higiene_personal'
            features['uso_principal'] = 'higiene'
            tipo_asignado = True
        elif contains(['jabon', 'jabón', 'detergente', 'limpiador', 'desinfectante']) and not tipo_asignado:
            features['tipo_de_bien'] = 'limpieza_hogar'
            features['uso_principal'] = 'limpieza'
            tipo_asignado = True
        elif contains(['olla', 'sartén', 'sarten', 'plato', 'vaso', 'colador', 'espátula', 'espatula', 'bandeja', 'cuchillo de cocina', 'utensilio de cocina']) and not tipo_asignado:
            features['tipo_de_bien'] = 'producto_cocina_menaje'
            features['uso_principal'] = 'cocina'
            tipo_asignado = True
        elif contains(['botella deportiva', 'termo', 'recipiente', 'envase', 'caja plastica']) and not tipo_asignado:
            features['tipo_de_bien'] = 'envase_recipient'
            features['uso_principal'] = 'envase'
            tipo_asignado = True
        elif contains(['estante', 'organizador', 'caja organizadora']) and not tipo_asignado:
            features['tipo_de_bien'] = 'hogar_organizador'
            features['uso_principal'] = 'hogar'
            tipo_asignado = True
        elif contains(['cortina de baño', 'cortina baño', 'tapete de baño', 'alfombra de baño']) and not tipo_asignado:
            features['tipo_de_bien'] = 'producto_bano'
            features['uso_principal'] = 'banio'
            tipo_asignado = True
        elif contains(['paraguas', 'sombrilla', 'mochila', 'cinturon', 'cinturón', 'pulsera', 'sombrero']) and not tipo_asignado:
            features['tipo_de_bien'] = 'accesorio_personal'
            features['uso_principal'] = 'accesorios'
            tipo_asignado = True
        elif contains(['jarron', 'jarrón', 'florero', 'portarretratos', 'decorativo']) and not tipo_asignado:
            features['tipo_de_bien'] = 'decoracion'
            features['uso_principal'] = 'decoracion'
            tipo_asignado = True
        elif contains(['balon', 'balón', 'rodillera', 'cuerda de salto', 'equipo deportivo']) and not tipo_asignado:
            features['tipo_de_bien'] = 'deporte_accesorio'
            features['uso_principal'] = 'deportes'
            tipo_asignado = True
        elif contains(['linterna', 'bombillo', 'bombilla', 'lámpara', 'lampara']) and not tipo_asignado:
            features['tipo_de_bien'] = 'iluminacion'
            features['uso_principal'] = 'iluminacion'
            tipo_asignado = True
        elif contains(['mesa plegable', 'silla comedor', 'mueble']) and not tipo_asignado:
            features['tipo_de_bien'] = 'mueble_hogar'
            features['uso_principal'] = 'muebles'
            tipo_asignado = True
        elif contains(['adhesivo', 'pegamento', 'cianoacrilato', 'cola instantanea']) and not tipo_asignado:
            features['tipo_de_bien'] = 'adhesivo_quimico'
            features['uso_principal'] = 'adhesivos'
            tipo_asignado = True
        elif contains(['grapadora', 'perforadora', 'carpeta plastica']) and not tipo_asignado:
            features['tipo_de_bien'] = 'papeleria_avanzada'
            features['uso_principal'] = 'oficina'
            tipo_asignado = True
        elif contains(['cremallera', 'aguja', 'hilo']) and not tipo_asignado:
            features['tipo_de_bien'] = 'mercearia'
            features['uso_principal'] = 'mercearia'
            tipo_asignado = True
        elif contains(['lupa']) and not tipo_asignado:
            features['tipo_de_bien'] = 'precision_optica'
            features['uso_principal'] = 'precision'
            tipo_asignado = True
        elif contains(['llave inglesa', 'llave ajustable', 'tijera multiusos']) and not tipo_asignado:
            features['tipo_de_bien'] = 'herramienta_ligera'
            features['uso_principal'] = 'ferreteria'
            tipo_asignado = True
        elif contains(['juguete', 'muñeca', 'bloques', 'puzzle', 'juego de mesa']) and not tipo_asignado:
            features['tipo_de_bien'] = 'juguete'
            features['uso_principal'] = 'juguetes'
            tipo_asignado = True
        
        # Flags de instantáneo / bebidas listas
        if contains(['instantaneo', 'instantáneo', 'soluble', 'en polvo', 'para preparar', 'instant mix']):
            features['es_instantaneo'] = True
        if contains(['cerveza', 'vino', 'bebida', 'refresco', 'kombucha', 'soda', 'sin alcohol']):
            features['es_bebida_listo_consumo'] = True
        
        # Detectar tipo de bien (manteniendo compatibilidad)
        if not tipo_asignado and contains(['parte', 'componente', 'repuesto', 'accesorio']):
            features['tipo_de_bien'] = 'parte_componente'
            tipo_asignado = True
        elif not tipo_asignado and contains(['materia prima', 'insumo', 'material']):
            features['tipo_de_bien'] = 'materia_prima'
            tipo_asignado = True
        elif not tipo_asignado and contains(['camiseta', 'pantalon', 'pantalón', 'jean', 'mezclilla', 'denim', 'chaqueta', 'bufanda', 'gorra', 'zapato', 'bota', 'calcetin', 'calcetín', 'guante', 'cinturon', 'cinturón', 'vestido']):
            features['tipo_de_bien'] = 'ropa_textil'
            tipo_asignado = True
        elif not tipo_asignado and contains(['calzado', 'zapato', 'bota']):
            features['tipo_de_bien'] = 'calzado'
            tipo_asignado = True
        elif not tipo_asignado and contains(['perfume', 'fragancia', 'eau de parfum', 'eau de toilette', 'colonia']):
            features['tipo_de_bien'] = 'perfume_cosmetico'
            tipo_asignado = True
        elif not tipo_asignado and contains(['papel', 'cuaderno', 'libreta', 'lapiz', 'lápiz', 'boligrafo', 'bolígrafo', 'acuarela', 'pincel', 'pegamento', 'cutter']):
            features['tipo_de_bien'] = 'papeleria'
            tipo_asignado = True
        elif not tipo_asignado and contains(['termometro', 'termómetro', 'tensiometro', 'tensiómetro', 'oximetro', 'oxímetro', 'jeringa', 'vendaje', 'mascarilla', 'guante']):
            features['tipo_de_bien'] = 'producto_medico'
            tipo_asignado = True
        elif not tipo_asignado and contains(['filtro', 'bujia', 'bujía', 'pastilla de freno', 'refrigerante', 'bomba de combustible']):
            features['tipo_de_bien'] = 'repuesto_automotriz'
            tipo_asignado = True
        elif not tipo_asignado and contains(['laptop', 'computadora', 'servidor', 'monitor', 'router', 'tablet', 'pantalla']):
            features['tipo_de_bien'] = 'equipamiento_electronico'
            tipo_asignado = True
        
        # Alimentos y bebidas (pueden complementar detecciones anteriores si no clasificaron)
        alimento_keywords = ['café', 'cafe', 'té', 'te', 'chocolate', 'miel', 'mermelada', 'aceite', 'vino', 'cerveza', 'vinagre', 'salsa', 'bebida', 'infusión', 'infusion']
        if not tipo_asignado and contains(alimento_keywords):
            if features['es_instantaneo']:
                features['tipo_de_bien'] = 'bebida_instantanea'
            elif features['es_bebida_listo_consumo']:
                features['tipo_de_bien'] = 'bebida'
            elif contains(['salsa', 'vinagre', 'soja', 'soya', 'condimento']):
                features['tipo_de_bien'] = 'condimento_salsa'
            elif contains(['miel', 'lacteo', 'lácteo', 'leche']):
                features['tipo_de_bien'] = 'producto_lacteo_miel'
            else:
                features['tipo_de_bien'] = 'alimento_bebida'
            tipo_asignado = True
        
        # Detectar uso principal
        if contains(['construccion', 'obra', 'edificacion', 'cemento', 'arena', 'ladrillo']):
            features['uso_principal'] = 'construccion'
        elif features['tipo_de_bien'] in ['alimento_bebida', 'alimento', 'bebida', 'bebida_instantanea', 'condimento_salsa', 'producto_lacteo_miel']:
            features['uso_principal'] = 'consumo_humano'
            if features['es_bebida_listo_consumo'] or features['tipo_de_bien'] in ['bebida', 'bebida_listo_consumo']:
                features['uso_principal'] = 'bebida_listo_consumo'
        elif features['tipo_de_bien'] == 'ropa_textil':
            features['uso_principal'] = 'vestir'
        elif features['tipo_de_bien'] == 'papeleria':
            features['uso_principal'] = 'escritura'
        elif features['tipo_de_bien'] == 'perfume_cosmetico':
            features['uso_principal'] = 'cuidado_personal'
        elif features['tipo_de_bien'] == 'producto_medico':
            features['uso_principal'] = 'medicion_medica'
        elif features['tipo_de_bien'] == 'repuesto_automotriz':
            features['uso_principal'] = 'automotriz'
        elif features['tipo_de_bien'] in ['semilla', 'fertilizante', 'producto_agricola', 'implemento_riego', 'recipiente_jardin', 'herramienta_agricola']:
            features['uso_principal'] = 'agricola'
        elif features['tipo_de_bien'] == 'material_construccion':
            features['uso_principal'] = 'construccion'
        elif features['tipo_de_bien'] == 'higiene_personal':
            features['uso_principal'] = 'higiene'
        elif features['tipo_de_bien'] == 'limpieza_hogar':
            features['uso_principal'] = 'limpieza'
        elif features['tipo_de_bien'] == 'producto_cocina_menaje':
            features['uso_principal'] = 'cocina'
        elif features['tipo_de_bien'] == 'envase_recipient':
            features['uso_principal'] = 'envase'
        elif features['tipo_de_bien'] == 'hogar_organizador':
            features['uso_principal'] = 'hogar'
        elif features['tipo_de_bien'] == 'accesorio_personal':
            features['uso_principal'] = 'accesorios'
        elif features['tipo_de_bien'] == 'deporte_accesorio':
            features['uso_principal'] = 'deportes'
        elif features['tipo_de_bien'] == 'producto_bano':
            features['uso_principal'] = 'banio'
        elif features['tipo_de_bien'] == 'decoracion':
            features['uso_principal'] = 'decoracion'
        elif features['tipo_de_bien'] == 'adhesivo_quimico':
            features['uso_principal'] = 'adhesivos'
        elif features['tipo_de_bien'] in ['papeleria_avanzada', 'oficina_equipo']:
            features['uso_principal'] = 'oficina'
        elif features['tipo_de_bien'] == 'mercearia':
            features['uso_principal'] = 'mercearia'
        elif features['tipo_de_bien'] == 'precision_optica':
            features['uso_principal'] = 'precision'
        elif features['tipo_de_bien'] == 'iluminacion':
            features['uso_principal'] = 'iluminacion'
        elif features['tipo_de_bien'] == 'mueble_hogar':
            features['uso_principal'] = 'muebles'
        elif features['tipo_de_bien'] == 'juguete':
            features['uso_principal'] = 'juguetes'
        elif features['tipo_de_bien'] == 'electrodomestico':
            features['uso_principal'] = 'hogar_electrico'
        elif features['tipo_de_bien'] == 'maquinaria_industrial':
            features['uso_principal'] = 'industrial_maquinaria'
        elif contains(['computo', 'informatica', 'electronico', 'digital']):
            features['uso_principal'] = 'computo'
        elif contains(['automotriz', 'vehiculo', 'carro', 'moto', 'motor', 'diesel', 'gasolina']):
            features['uso_principal'] = 'automotriz'
        elif contains(['ferreteria', 'herramienta', 'herramientas', 'pala']):
            features['uso_principal'] = 'ferreteria'
        
        # Detectar material principal
        if contains(['metal', 'acero', 'hierro', 'aluminio']):
            features['material_principal'] = 'metal'
        elif contains(['plastico', 'polietileno', 'pvc']):
            features['material_principal'] = 'plastico'
        elif contains(['madera', 'pino', 'roble']):
            features['material_principal'] = 'madera'
        elif contains(['vidrio', 'cristal']):
            features['material_principal'] = 'vidrio'
        elif contains(['ceramica', 'porcelana']):
            features['material_principal'] = 'ceramica'
        elif contains(['algodon', 'algodón', 'lana', 'seda', 'poliester']):
            features['material_principal'] = 'textil'
        elif contains(['papel', 'carton', 'cartón']):
            features['material_principal'] = 'papel'
        
        return features
    
    def _try_specific_rules(self, text: str) -> Dict[str, Any]:
        """Intenta aplicar reglas específicas para productos comunes."""
        text_lower = text.lower()
        
        for keyword, rule in self.specific_rules.items():
            if keyword in text_lower:
                return rule
        
        return None
    
    def _process_specific_rule_result(self, case: Dict[str, Any], result: Dict[str, Any], features: Dict[str, Any], start_time: datetime, text: str = "") -> Dict[str, Any]:
        """Procesa el resultado de una regla específica."""
        hs6 = result.get('hs6', '')
        national_code = result.get('national_code', '')
        title = result.get('title', '')
        
        # Calcular confianza alta para reglas específicas
        confidence = 0.9
        
        # Aplicar validación de consistencia
        validation_result = self._validate_classification_consistency(features, national_code, title)
        
        # Ajustar confianza basada en validación
        validation_penalty = 0.1 * (1.0 - validation_result['validation_score'])
        final_confidence = max(0.0, confidence - validation_penalty)
        
        # NUEVAS VALIDACIONES: Verificar coherencia de capítulo y códigos sospechosos
        chapter_coherence = self._chapter_coherence_check(national_code, features, text)
        is_suspect = self._is_suspect_code(national_code)
        requires_review = False
        
        # Si hay incoherencia de capítulo, forzar baja confianza
        if not chapter_coherence:
            final_confidence = 0.0
            requires_review = True
            logging.warning(f"Caso {case['id']}: Regla específica con incoherencia detectada, confianza forzada a 0.0")
        
        # Guardar candidato
        trace = [{'method': 'specific_rule', 'decision': f'Regla específica aplicada: {national_code}'}]
        self._save_candidate(case['id'], national_code, hs6, title, final_confidence, trace, validation_result, features)
        
        # Registrar métricas
        end_time = datetime.now()
        response_time = (end_time - start_time).total_seconds()
        self._record_metrics(case['id'], final_confidence, response_time, validation_result['validation_score'], requires_review=requires_review)
        
        # Construir rationale (incluyendo nuevas validaciones)
        rationale = self._build_detailed_rationale(features, trace, result, validation_result, chapter_coherence, is_suspect, requires_review)

        # Registrar validación incremental para reglas específicas
        self._record_incremental_validation(
            case_id=case['id'],
            duration=response_time,
            national_code=national_code,
            validation_result=validation_result,
            method='specific_rule',
            confidence=final_confidence,
            is_suspect=is_suspect,
            requires_review=requires_review
        )

        # Feedback automático si requiere revisión o baja confianza
        if final_confidence < 0.6 or requires_review:
            self._register_automatic_feedback(
                case_id=case['id'],
                input_text=text or case.get('product_desc', '') or case.get('product_title', ''),
                predicted_code=national_code,
                confidence=final_confidence,
                rationale=rationale,
                requires_review=requires_review,
                validation_result=validation_result
            )

        return {
            'case_id': case['id'],
            'hs6': hs6,
            'national_code': national_code,
            'title': title,
            'confidence': final_confidence,
            'rationale': rationale,
            'validation_flags': validation_result,
            'features': features,
            'method': 'specific_rule',
            'response_time': response_time,
            'topK': []
        }

    def _fallback_hs6(self, text: str, features: Dict[str, Any]) -> Optional[str]:
        """Fallback heurístico para determinar HS6 cuando el motor RGI no aporta candidatos."""
        if not text:
            return None

        text_norm = unicodedata.normalize('NFKD', text.lower())
        text_norm = ''.join(ch for ch in text_norm if not unicodedata.combining(ch))

        feature_flags = features or {}

        if feature_flags.get('es_semilla'):
            return '120930'
        if feature_flags.get('es_fertilizante'):
            return '310520'
        if feature_flags.get('es_bebida_listo_consumo'):
            return '220300'
        
        if 'cafe' in text_norm:
            if feature_flags.get('es_instantaneo'):
                return '210111'
            return '090121'
        if 'olla' in text_norm:
            return '732393'
        if 'sarten' in text_norm or 'sartén' in text_norm:
            return '761510'
        if 'plato' in text_norm:
            return '691110'
        if 'vaso' in text_norm:
            return '701349'
        if 'cuchillo de cocina' in text_norm or ('cuchillo' in text_norm and 'cocina' in text_norm):
            return '821192'
        if 'tijeras' in text_norm and ('multiuso' in text_norm or 'multiusos' in text_norm):
            return '821300'
        if 'botella deportiva' in text_norm:
            return '392330'
        if 'estante' in text_norm and 'metal' in text_norm:
            return '732399'
        if 'caja plastica' in text_norm or ('caja' in text_norm and 'plast' in text_norm):
            return '392310'
        if 'paraguas' in text_norm or 'sombrilla' in text_norm:
            return '660191'
        if 'mochila' in text_norm:
            return '420292'
        if 'cinturon' in text_norm or 'cinturón' in text_norm:
            return '420321'
        if 'pulsera' in text_norm and 'acero' in text_norm:
            return '711711'
        if 'sombrero' in text_norm and ('paja' in text_norm or 'fibra natural' in text_norm):
            return '650400'
        if 'te negro' in text_norm or 'earl grey' in text_norm:
            if 'instant' in text_norm or 'instantaneo' in text_norm or 'instantáneo' in text_norm or 'soluble' in text_norm or feature_flags.get('es_instantaneo'):
                return '210120'
            return '090240'
        if 'te verde' in text_norm or 'té verde' in text_norm:
            if 'instant' in text_norm or feature_flags.get('es_instantaneo'):
                return '210120'
            return '090220'
        if ('te ' in text_norm or 'té ' in text_norm or 'infusion' in text_norm or 'infusión' in text_norm) and 'instant' not in text_norm and 'soluble' not in text_norm:
            return '090220'
        if ('te ' in text_norm or 'té ' in text_norm) and ('instant' in text_norm or feature_flags.get('es_instantaneo')):
            return '210120'
        if 'te ' in text_norm or 'té' in text_norm:
            return '090220'
        if 'salsa de soja' in text_norm or 'salsa soja' in text_norm or 'soya japonesa' in text_norm:
            return '210310'
        if 'vinagre' in text_norm:
            return '220900'
        if 'miel' in text_norm:
            return '040900'
        if 'mermelada' in text_norm:
            return '200799'

        for rule in self._fallback_rules:
            if any(keyword in text_norm for keyword in rule['keywords']):
                logging.info("Fallback heurístico aplicado (%s -> %s)", rule['keywords'][0], rule['hs6'])
                return rule['hs6']

        uso_principal = (features or {}).get('uso_principal')
        if uso_principal:
            fallback_hs6 = self._fallback_use_map.get(uso_principal)
            if fallback_hs6:
                logging.info("Fallback por uso_principal=%s -> HS6 %s", uso_principal, fallback_hs6)
                return fallback_hs6

        tipo_bien = (features or {}).get('tipo_de_bien')
        if tipo_bien == 'materia_prima':
            return '250510'

        return None
    
    def _get_attrs_for_hs6(self, hs6: str) -> Dict[str, Any]:
        """Obtiene atributos para un HS6 específico."""
        return {
            'hs6': hs6,
            'chapter': hs6[:2] if len(hs6) >= 2 else '00',
            'heading': hs6[:4] if len(hs6) >= 4 else '0000'
        }
    
    def _get_national_options(self, hs6: str, attrs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Obtiene opciones nacionales para un HS6."""
        # Por simplicidad, generamos opciones básicas
        options = []
        
        # Opción principal
        main_option = {
            'national_code': f"{hs6}0000",
            'title': f'Producto clasificado bajo HS6 {hs6}',
            'description': f'Descripción genérica para HS6 {hs6}',
            'semantic_score': 0.8,
            'lexical_score': 0.7
        }
        options.append(main_option)
        
        # Opciones alternativas
        for i in range(1, 4):
            alt_option = {
                'national_code': f"{hs6}{i:04d}",
                'title': f'Alternativa {i} para HS6 {hs6}',
                'description': f'Descripción alternativa {i} para HS6 {hs6}',
                'semantic_score': 0.8 - (i * 0.1),
                'lexical_score': 0.7 - (i * 0.1)
            }
            options.append(alt_option)
        
        return options
    
    def _select_best_candidate(
        self,
        text: str,
        options: List[Dict[str, Any]],
        features: Dict[str, Any],
        attrs: Dict[str, Any],
        weights: Dict[str, float],
        suspect_penalties: Dict[str, float],
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Selecciona el mejor candidato usando scores combinados y devuelve la lista ordenada."""
        if not options:
            return None, []
        
        weight_semantic = weights.get('semantic', 0.30)
        weight_lexical = weights.get('lexical', 0.25)
        weight_context = weights.get('rgi', 0.45)
        
        for option in options:
            national_code = option.get('national_code', '')
            contextual_score = self._calculate_contextual_score(national_code, features)
            semantic_original = option.get('semantic_score', 0.0)
            penalty = suspect_penalties.get(national_code, 0.0)
            semantic_score = max(0.0, semantic_original - penalty)
            monopoly_penalty = 0.0
            if national_code in self._MONOPOLY_CODES:
                tipo = features.get('tipo_de_bien')
                if tipo in {'ropa_textil', 'calzado', 'alimento_bebida', 'perfume_cosmetico',
                            'papeleria', 'producto_medico', 'repuesto_automotriz',
                            'alimento', 'bebida', 'bebida_instantanea', 'condimento_salsa',
                            'semilla', 'fertilizante', 'producto_agricola'}:
                    monopoly_penalty = 0.15
                    semantic_score *= 0.6
                    contextual_score *= 0.7
            
            guard = self._CODE_TYPE_GUARDS.get(national_code)
            if guard:
                blocked = guard.get('blocked_types', set())
                tipo_actual = features.get('tipo_de_bien')
                if blocked and tipo_actual in blocked:
                    semantic_score *= 0.5
                    contextual_score *= 0.6
            
            score_total = (
                weight_semantic * semantic_score +
                weight_lexical * option.get('lexical_score', 0.0) +
                weight_context * contextual_score
            )
            
            option['semantic_score_adjusted'] = semantic_score
            option['contextual_score'] = contextual_score
            option['total_score'] = score_total
            option.setdefault('meta', {}).setdefault('adjustments', {})
            if penalty > 0:
                option['meta']['adjustments']['semantic_penalty'] = penalty
            if monopoly_penalty:
                option['meta']['adjustments']['monopoly_context_penalty'] = monopoly_penalty
            if guard and guard.get('blocked_types') and features.get('tipo_de_bien') in guard['blocked_types']:
                option['meta']['adjustments']['type_block_penalty'] = 0.4
        
        options_sorted = sorted(
            options,
            key=lambda opt: opt.get('total_score', opt.get('semantic_score_adjusted', 0.0)),
            reverse=True
        )
        
        best_candidate = options_sorted[0].copy() if options_sorted else None
        return best_candidate, options_sorted
    
    def _calculate_contextual_score(self, national_code: str, features: Dict[str, Any]) -> float:
        """Calcula score contextual basado en coherencia entre características y código HS."""
        if not national_code or len(national_code) < 6:
            return 0.5
        
        chapter = national_code[:2]
        score = 0.5  # Score base
        
        # Mapeo de capítulos a usos principales
        chapter_usage_map = {
            '01': ['alimentacion', 'ganaderia'],
            '02': ['alimentacion', 'ganaderia'],
            '03': ['alimentacion', 'pesca'],
            '04': ['alimentacion', 'lacteos'],
            '05': ['alimentacion', 'animales'],
            '06': ['agricultura', 'plantas'],
            '07': ['alimentacion', 'vegetales'],
            '08': ['alimentacion', 'frutas'],
            '09': ['alimentacion', 'cafe', 'te'],
            '10': ['alimentacion', 'cereales'],
            '11': ['alimentacion', 'harinas'],
            '12': ['alimentacion', 'semillas'],
            '13': ['alimentacion', 'gomas'],
            '14': ['agricultura', 'plantas'],
            '15': ['alimentacion', 'aceites'],
            '16': ['alimentacion', 'preparados'],
            '17': ['alimentacion', 'azucares'],
            '18': ['alimentacion', 'cacao'],
            '19': ['alimentacion', 'preparados'],
            '20': ['alimentacion', 'conservas'],
            '21': ['alimentacion', 'preparados'],
            '22': ['alimentacion', 'bebidas'],
            '23': ['alimentacion', 'animales'],
            '24': ['tabaco'],
            '25': ['construccion', 'minerales'],
            '26': ['construccion', 'minerales'],
            '27': ['energia', 'combustibles'],
            '28': ['quimicos', 'industriales'],
            '29': ['quimicos', 'organicos'],
            '30': ['medicina', 'farmaceuticos'],
            '31': ['agricultura', 'fertilizantes'],
            '32': ['quimicos', 'tintas'],
            '33': ['cosmeticos', 'perfumes'],
            '34': ['quimicos', 'jabones'],
            '35': ['quimicos', 'proteinas'],
            '36': ['quimicos', 'explosivos'],
            '37': ['fotografia'],
            '38': ['quimicos', 'miscelaneos'],
            '39': ['plastico', 'polimeros'],
            '40': ['caucho', 'neumaticos'],
            '41': ['textil', 'cuero'],
            '42': ['textil', 'cuero'],
            '43': ['textil', 'cuero'],
            '44': ['madera', 'construccion'],
            '45': ['textil', 'corcho'],
            '46': ['textil', 'manufacturas'],
            '47': ['papel', 'celulosa'],
            '48': ['papel', 'manufacturas'],
            '49': ['papel', 'impresos'],
            '50': ['textil', 'seda'],
            '51': ['textil', 'lana'],
            '52': ['textil', 'algodon'],
            '53': ['textil', 'fibras'],
            '54': ['textil', 'filamentos'],
            '55': ['textil', 'fibras'],
            '56': ['textil', 'no tejidos'],
            '57': ['textil', 'alfombras'],
            '58': ['textil', 'tejidos'],
            '59': ['textil', 'recubrimientos'],
            '60': ['textil', 'tejidos'],
            '61': ['textil', 'prendas'],
            '62': ['textil', 'prendas'],
            '63': ['textil', 'manufacturas'],
            '64': ['calzado'],
            '65': ['textil', 'sombreros'],
            '66': ['textil', 'paraguas'],
            '67': ['textil', 'plumas'],
            '68': ['construccion', 'piedra'],
            '69': ['construccion', 'ceramica'],
            '70': ['construccion', 'vidrio'],
            '71': ['joyeria', 'metales'],
            '72': ['metal', 'hierro'],
            '73': ['metal', 'hierro'],
            '74': ['metal', 'cobre'],
            '75': ['metal', 'niquel'],
            '76': ['metal', 'aluminio'],
            '78': ['metal', 'plomo'],
            '79': ['metal', 'zinc'],
            '80': ['metal', 'estano'],
            '81': ['metal', 'otros'],
            '82': ['metal', 'herramientas'],
            '83': ['metal', 'manufacturas'],
            '84': ['maquinas', 'computo'],
            '85': ['electronica', 'electricidad'],
            '86': ['transporte', 'ferrocarril'],
            '87': ['transporte', 'automotriz'],
            '88': ['transporte', 'aereo'],
            '89': ['transporte', 'maritimo'],
            '90': ['instrumentos', 'medicion'],
            '91': ['instrumentos', 'relojes'],
            '92': ['instrumentos', 'musicales'],
            '93': ['armas', 'municiones'],
            '94': ['muebles', 'hogar'],
            '95': ['juguetes', 'deportes'],
            '96': ['manufacturas', 'miscelaneas'],
            '97': ['arte', 'antiguedades']
        }
        
        # Verificar coherencia con uso principal
        uso_principal = features.get('uso_principal', 'general')
        if chapter in chapter_usage_map:
            usos_validos = chapter_usage_map[chapter]
            if uso_principal in usos_validos:
                score += 0.3  # Boost por coherencia
            else:
                score -= 0.2  # Penalización por incoherencia
        
        # Verificar coherencia con material principal
        material = features.get('material_principal', 'no_especificado')
        if material != 'no_especificado':
            if (material == 'metal' and chapter in ['72', '73', '74', '75', '76', '78', '79', '80', '81', '82', '83']) or \
               (material == 'plastico' and chapter in ['39', '40']) or \
               (material == 'madera' and chapter in ['44', '45']) or \
               (material == 'vidrio' and chapter in ['70']) or \
               (material == 'ceramica' and chapter in ['69']) or \
               (material == 'textil' and chapter in ['50', '51', '52', '53', '54', '55', '56', '57', '58', '59', '60', '61', '62', '63', '64', '65', '66', '67']):
                score += 0.2  # Boost por coherencia de material
            else:
                score -= 0.1  # Penalización leve por incoherencia de material
        
        tipo = features.get('tipo_de_bien')
        expected = self._TYPE_EXPECTED_CHAPTERS.get(tipo)
        if expected:
            if chapter in expected:
                score += 0.35
            else:
                score -= 0.4
        agri_types = {'semilla', 'fertilizante', 'producto_agricola', 'implemento_riego', 'recipiente_jardin', 'herramienta_agricola'}
        if tipo in agri_types and chapter in {'72', '73', '84', '85', '61', '62'}:
            score -= 0.25
        
        return max(0.0, min(1.0, score))
    
    def _chapter_coherence_check(self, hs_code: str, features: Dict[str, Any], text: str = "") -> bool:
        """
        Verifica la coherencia entre el código HS y las características del producto.
        
        Devuelve False si hay incoherencias claras (ej: motor diésel clasificado como agua).
        """
        if not hs_code or len(hs_code) < 2:
            return True  # Si no hay código, no podemos validar
        
        chapter = hs_code[:2]
        uso_principal = features.get('uso_principal', 'general')
        tipo_bien = features.get('tipo_de_bien', 'producto_terminado')
        material = features.get('material_principal', 'no_especificado')
        text_lower = text.lower() if text else ""
        
        food_chapters = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23']
        machinery_chapters = ['84', '85', '90']
        mineral_chapters = ['25', '26']
        apparel_chapters = ['61', '62', '63', '64']
        paper_chapters = ['48', '49', '96']
        perfume_chapters = ['33']
        medical_chapters = ['30', '90']
        auto_parts_chapters = ['84', '85', '87']
        
        # Verificar incoherencias graves
        
        # 1. Alimentos con uso no alimentario
        if chapter in food_chapters:
            if uso_principal in ['construccion', 'ferreteria', 'herramienta', 'industrial', 'electricidad', 'automotriz', 'computo']:
                logging.warning(f"Incoherencia detectada: HS {hs_code} (alimentos) con uso {uso_principal}")
                return False
        
        # 2. Maquinaria/electrónica con tipo "materia prima" o material construcción
        if chapter in machinery_chapters:
            if tipo_bien in ['materia_prima', 'alimento_bebida', 'ropa_textil', 'papeleria', 'producto_medico'] \
               or material in ['arena', 'ladrillo', 'cemento', 'piedra']:
                logging.warning(f"Incoherencia detectada: HS {hs_code} (maquinaria) con materia prima o construcción")
                return False
        
        # 3. Minerales con producto terminado tecnológico
        if chapter in mineral_chapters:
            if tipo_bien == 'producto_terminado' and uso_principal in ['computo', 'electronica', 'electricidad']:
                logging.warning(f"Incoherencia detectada: HS {hs_code} (mineral) con producto terminado tecnológico")
                return False
        
        # 4. Capítulo 22 (bebidas) con uso industrial/automotriz (ej: motor diésel)
        if chapter == '22' and uso_principal in ['automotriz', 'industrial', 'maquinaria', 'ferreteria']:
            logging.warning(f"Incoherencia detectada: HS {hs_code} (bebidas) con uso automotriz/industrial")
            return False
        
        # 5. Capítulo 19 (panadería) con uso construcción/eléctrico (ej: panel solar)
        if chapter == '19' and uso_principal in ['construccion', 'electricidad', 'computo']:
            logging.warning(f"Incoherencia detectada: HS {hs_code} (panadería) con uso construcción/eléctrico")
            return False
        
        # 6. Capítulo 09 (café, té) con uso no alimentario (ej: zapatos)
        if chapter == '09' and uso_principal in ['textil', 'calzado', 'construccion']:
            logging.warning(f"Incoherencia detectada: HS {hs_code} (café) con uso no alimentario")
            return False
        
        # 7. Capítulo 44 (madera) con producto terminado metálico (ej: pala metálica)
        # Solo detectar si NO menciona madera como material principal
        if chapter == '44' and tipo_bien == 'producto_terminado' and material == 'metal' and 'madera' not in text_lower and 'mango' not in text_lower:
            logging.warning(f"Incoherencia detectada: HS {hs_code} (madera) con producto metálico")
            return False
        
        # 8. Capítulo 64 (calzado) pero el texto habla de café
        if chapter == '64' and ('cafe' in text_lower or 'café' in text_lower):
            logging.warning(f"Incoherencia detectada: HS {hs_code} (calzado) pero menciona café")
            return False

        # 9. Textiles y calzado fuera de capítulos textiles
        if tipo_bien in ['ropa_textil', 'calzado'] and chapter not in apparel_chapters:
            logging.warning(f"Incoherencia detectada: producto textil/calzado clasificado en capítulo {chapter}")
            return False

        # 10. Papelería/arte fuera de capítulos 48/49/96
        if tipo_bien == 'papeleria' and chapter not in paper_chapters:
            logging.warning(f"Incoherencia detectada: papelería clasificada en capítulo {chapter}")
            return False

        # 11. Perfumes/cosméticos fuera de capítulo 33
        if tipo_bien == 'perfume_cosmetico' and chapter not in perfume_chapters:
            logging.warning(f"Incoherencia detectada: perfumes/cosméticos clasificados en capítulo {chapter}")
            return False

        # 12. Productos médicos fuera de capítulos médicos
        if tipo_bien == 'producto_medico' and chapter not in (medical_chapters + ['63']):
            logging.warning(f"Incoherencia detectada: producto médico clasificado en capítulo {chapter}")
            return False

        # 13. Repuestos automotrices lejos de capítulos automotrices
        if tipo_bien == 'repuesto_automotriz' and chapter not in auto_parts_chapters:
            logging.warning(f"Incoherencia detectada: repuesto automotriz clasificado en capítulo {chapter}")
            return False
        
        if tipo_bien == 'semilla' and chapter not in ['12']:
            logging.warning(f"Incoherencia detectada: semilla clasificada en capítulo {chapter}")
            return False
        if tipo_bien == 'fertilizante' and chapter not in ['31']:
            logging.warning(f"Incoherencia detectada: fertilizante clasificado en capítulo {chapter}")
            return False
        if tipo_bien == 'producto_agricola' and chapter not in ['12', '31', '39', '69', '82']:
            logging.warning(f"Incoherencia detectada: producto agrícola clasificado en capítulo {chapter}")
            return False
        if tipo_bien == 'implemento_riego' and chapter not in ['39']:
            logging.warning(f"Incoherencia detectada: implemento de riego clasificado en capítulo {chapter}")
            return False
        if tipo_bien == 'recipiente_jardin' and chapter not in ['69']:
            logging.warning(f"Incoherencia detectada: recipiente de jardín clasificado en capítulo {chapter}")
            return False
        if tipo_bien == 'herramienta_agricola' and chapter not in ['82']:
            logging.warning(f"Incoherencia detectada: herramienta agrícola clasificada en capítulo {chapter}")
            return False
        if tipo_bien == 'higiene_personal' and chapter not in ['33', '96']:
            logging.warning(f"Incoherencia detectada: higiene personal clasificada en capítulo {chapter}")
            return False
        if tipo_bien == 'limpieza_hogar' and chapter not in ['34', '39']:
            logging.warning(f"Incoherencia detectada: producto de limpieza clasificado en capítulo {chapter}")
            return False
        if tipo_bien == 'producto_cocina_menaje' and chapter not in ['73', '76', '69', '70', '82']:
            logging.warning(f"Incoherencia detectada: menaje de cocina clasificado en capítulo {chapter}")
            return False
        if tipo_bien == 'hogar_organizador' and chapter not in ['39', '73']:
            logging.warning(f"Incoherencia detectada: organizador de hogar clasificado en capítulo {chapter}")
            return False
        if tipo_bien == 'accesorio_personal' and chapter not in ['42', '65', '66', '71']:
            logging.warning(f"Incoherencia detectada: accesorio personal clasificado en capítulo {chapter}")
            return False
        if tipo_bien == 'deporte_accesorio' and chapter not in ['95', '63']:
            logging.warning(f"Incoherencia detectada: accesorio deportivo clasificado en capítulo {chapter}")
            return False
        if tipo_bien == 'producto_bano' and chapter not in ['39', '57', '70']:
            logging.warning(f"Incoherencia detectada: artículo de baño clasificado en capítulo {chapter}")
            return False
        if tipo_bien == 'decoracion' and chapter not in ['69', '70', '44']:
            logging.warning(f"Incoherencia detectada: decoración clasificada en capítulo {chapter}")
            return False
        if tipo_bien == 'adhesivo_quimico' and chapter not in ['35', '32']:
            logging.warning(f"Incoherencia detectada: adhesivo clasificado en capítulo {chapter}")
            return False
        if tipo_bien == 'papeleria_avanzada' and chapter not in ['48', '96', '82']:
            logging.warning(f"Incoherencia detectada: papelería clasificada en capítulo {chapter}")
            return False
        if tipo_bien == 'mercearia' and chapter not in ['96', '73']:
            logging.warning(f"Incoherencia detectada: mercería clasificada en capítulo {chapter}")
            return False
        if tipo_bien == 'precision_optica' and chapter not in ['90']:
            logging.warning(f"Incoherencia detectada: instrumento de precisión clasificado en capítulo {chapter}")
            return False
        if tipo_bien == 'iluminacion' and chapter not in ['85', '94']:
            logging.warning(f"Incoherencia detectada: iluminación clasificada en capítulo {chapter}")
            return False
        if tipo_bien == 'mueble_hogar' and chapter not in ['94']:
            logging.warning(f"Incoherencia detectada: mueble clasificado en capítulo {chapter}")
            return False
        if tipo_bien == 'juguete' and chapter not in ['95']:
            logging.warning(f"Incoherencia detectada: juguete clasificado en capítulo {chapter}")
            return False
        if tipo_bien == 'envase_recipient' and chapter not in ['39', '70', '42']:
            logging.warning(f"Incoherencia detectada: envase clasificado en capítulo {chapter}")
            return False
        if tipo_bien == 'electrodomestico' and chapter not in ['84', '85']:
            logging.warning(f"Incoherencia detectada: electrodoméstico clasificado en capítulo {chapter}")
            return False
        if tipo_bien == 'maquinaria_industrial' and chapter not in ['84', '85', '90']:
            logging.warning(f"Incoherencia detectada: maquinaria industrial clasificada en capítulo {chapter}")
            return False
        if tipo_bien == 'material_construccion' and chapter not in ['25', '68', '69', '72']:
            logging.warning(f"Incoherencia detectada: material de construcción clasificado en capítulo {chapter}")
            return False
        if tipo_bien in ['bebida', 'bebida_listo_consumo'] and chapter not in ['22']:
            logging.warning(f"Incoherencia detectada: bebida clasificada en capítulo {chapter}")
            return False
        if tipo_bien == 'bebida_instantanea' and chapter not in ['21', '22']:
            logging.warning(f"Incoherencia detectada: bebida instantánea clasificada en capítulo {chapter}")
            return False
        if tipo_bien == 'condimento_salsa' and chapter not in ['21', '22']:
            logging.warning(f"Incoherencia detectada: condimento/salsa clasificado en capítulo {chapter}")
            return False
        if tipo_bien == 'producto_lacteo_miel' and chapter not in ['04']:
            logging.warning(f"Incoherencia detectada: producto lácteo/miel clasificado en capítulo {chapter}")
            return False
        
        return True
    
    def _is_suspect_code(self, national_code: str) -> bool:
        """Verifica si un código HS está en la lista de códigos sospechosos."""
        return national_code in self._SUSPECT_CODES
    
    def _validate_classification_consistency(self, features: Dict[str, Any], hs_code: str, title: str) -> Dict[str, Any]:
        """Valida la consistencia de la clasificación."""
        validation_score = 1.0
        flags = {}
        
        if not hs_code:
            validation_score = 0.0
            flags['no_hs_code'] = True
            return {'validation_score': validation_score, 'flags': flags}
        
        # Validación de coherencia de capítulo
        if len(hs_code) >= 2:
            chapter = hs_code[:2]
            uso_principal = features.get('uso_principal', 'general')
            
            # Mapeo básico de capítulos a usos
            chapter_usages = {
                '01': 'alimentacion', '02': 'alimentacion', '03': 'alimentacion',
                '25': 'construccion', '26': 'construccion', '27': 'energia',
                '84': 'computo', '85': 'electronica', '87': 'automotriz'
            }
            
            if chapter in chapter_usages:
                expected_usage = chapter_usages[chapter]
                if uso_principal != expected_usage and uso_principal != 'general':
                    validation_score -= 0.2
                    flags['coherencia_capitulo'] = False
                else:
                    flags['coherencia_capitulo'] = True
        
        # Validación de tipo de bien
        tipo_bien = features.get('tipo_de_bien', 'producto_terminado')
        if tipo_bien == 'producto_terminado' and any(word in title.lower() for word in ['parte', 'componente', 'repuesto']):
            validation_score -= 0.3
            flags['tipo_bien_inconsistente'] = True
        else:
            flags['tipo_bien_inconsistente'] = False
        
        validation_score = max(0.0, validation_score)
        flags['validation_score'] = validation_score
        
        return {'validation_score': validation_score, 'flags': flags}
    
    def _case_exists(self, case_id: int) -> bool:
        """Verifica si un caso existe en la base de datos."""
        try:
            with self.cc.get_session() as session:
                result = session.execute(
                    text("SELECT 1 FROM cases WHERE id = :case_id LIMIT 1"),
                    {"case_id": case_id}
                ).fetchone()
                return result is not None
        except Exception as e:
            logging.warning(f"Error verificando existencia de caso {case_id}: {str(e)}")
            return False
    
    def _save_candidate(self, case_id: int, national_code: str, hs6: str, title: str, confidence: float, trace: List[Dict], validation_result: Dict, features: Dict):
        """Guarda el candidato seleccionado."""
        try:
            # Verificar que el caso existe antes de guardar
            if not self._case_exists(case_id):
                logging.warning(f"Saltando persistencia de candidates para case_id={case_id} (no existe en BD)")
                return
            
            candidate_data = {
                'case_id': case_id,
                'hs_code': national_code,
                'hs6': hs6,
                'title': title,
                'confidence': confidence,
                'rank': 1,
                'rationale': json.dumps({
                    'trace': trace,
                    'validation_result': validation_result,
                    'features': features
                }),
                'legal_refs_json': json.dumps({
                    'method': 'rgi',
                    'trace': trace,
                    'validation_score': validation_result.get('validation_score', 0.0)
                })
            }
            
            self.candidate_repo.create(candidate_data)
            
        except Exception as e:
            logging.warning(f"Error guardando candidato: {str(e)}")
    
    def _record_metrics(self, case_id: int, confidence: float, response_time: float, validation_score: float, requires_review: bool = False):
        """Registra métricas de clasificación."""
        try:
            self.metrics_service.record_classification_metrics(
                case_id, confidence, response_time, validation_score, requires_review=requires_review
            )
            
            # Registrar caso sospechoso si requires_review
            if requires_review:
                self.metrics_service.update_kpi(
                    'classification_event',
                    confidence,
                    {
                        'case_id': case_id,
                        'requires_review': True,
                        'validation_score': validation_score,
                        'timestamp': datetime.now().isoformat()
                    }
                )
        except Exception as e:
            logging.warning(f"Error registrando métricas: {str(e)}")
    
    def _record_incremental_validation(self, case_id: int, duration: float, national_code: str,
                                       validation_result: Dict, method: str, confidence: float,
                                       is_suspect: bool, requires_review: bool):
        """Registra datos para validación incremental."""
        try:
            incremental_validation.record_classification(
                case_id=case_id,
                confidence=confidence,
                hs_code=national_code,
                validation_score=validation_result.get('validation_score'),
                validation_result=validation_result,
                method=method,
                is_suspect=is_suspect,
                requires_review=requires_review,
                duration_s=duration
            )
        except Exception as e:
            logging.warning(f"Error registrando validación incremental: {str(e)}")
    
    def _register_automatic_feedback(self, case_id: int, input_text: str, predicted_code: str,
                                     confidence: float, rationale: Dict[str, Any], requires_review: bool,
                                     validation_result: Dict[str, Any]):
        """Registra feedback automático para casos de baja confianza o sospechosos."""
        try:
            # Solo intentar registrar feedback si case_id es válido
            if case_id and case_id > 0:
                learning_integration.register_feedback(
                    case_id=case_id,
                    input_text=input_text,
                    predicted_hs=predicted_code or '',
                    confidence=confidence,
                    rationale=rationale,
                    original_result={
                        'national_code': predicted_code,
                        'confidence': confidence,
                        'validation_flags': validation_result or {},
                        'features': rationale.get('factores_clave', []),
                        'rationale': rationale
                    },
                    requires_review=requires_review,
                    correct_hs=None
                )
        except Exception as e:
            logging.warning(f"Error registrando feedback automático (case_id={case_id}): {str(e)}")
    
    def _build_detailed_rationale(self, features: Dict[str, Any], trace: List[Dict], chosen: Dict[str, Any], validation_result: Dict[str, Any], chapter_coherence: bool = True, is_suspect: bool = False, requires_review: bool = False) -> Dict[str, Any]:
        """Construye un rationale detallado para la clasificación."""
        return {
            'decision': f"Se seleccionó código {chosen.get('national_code', 'N/A')}",
            'factores_clave': self._extract_key_factors(features),
            'validations': self._format_validations(validation_result),
            'method': 'rgi',
            'confidence_factors': {
                'semantic_score': chosen.get('semantic_score', 0.0),
                'lexical_score': chosen.get('lexical_score', 0.0),
                'contextual_score': chosen.get('contextual_score', 0.0),
                'total_score': chosen.get('total_score', 0.0)
            },
            'chapter_coherence': 'OK' if chapter_coherence else 'FAIL',
            'suspect_code': is_suspect,
            'requires_review': requires_review or validation_result.get('validation_score', 1.0) < 0.7,
            'review_notes': chosen.get('review_notes', [])
        }
    
    def _extract_key_factors(self, features: Dict[str, Any]) -> List[str]:
        """Extrae factores clave para el rationale."""
        factors = []
        
        if features.get('tipo_de_bien'):
            factors.append(f"tipo_de_bien={features['tipo_de_bien']}")
        
        if features.get('uso_principal'):
            factors.append(f"uso_principal={features['uso_principal']}")
        
        if features.get('material_principal'):
            factors.append(f"material_principal={features['material_principal']}")
        
        return factors
    
    def _format_validations(self, validation_result: Dict[str, Any]) -> List[str]:
        """Formatea los resultados de validación."""
        validations = []
        flags = validation_result.get('flags', {})
        
        for flag, value in flags.items():
            if flag != 'validation_score':
                status = "OK" if value else "FAIL"
                validations.append(f"{flag}={status}")
        
        return validations
    
    def _get_top_candidates(self, options: List[Dict[str, Any]], text: str, features: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Obtiene los mejores candidatos para mostrar en topK."""
        top_candidates = []
        
        ordered = sorted(options, key=lambda opt: opt.get('total_score', opt.get('semantic_score', 0.0)), reverse=True)
        
        for i, option in enumerate(ordered[:5]):  # Top 5
            candidate = {
                'hs': option.get('national_code', ''),
                'title': option.get('title', ''),
                'score': option.get('total_score', option.get('semantic_score', 0.0)),
                'rank': i + 1
            }
            top_candidates.append(candidate)
        
        return top_candidates

    def _refresh_dynamic_adjustments(self) -> None:
        """
        Carga la configuración dinámica generada por el script de prueba masiva.
        Ajusta pesos y umbrales sin interrumpir el flujo en tiempo real.
        """
        report_path = Path("outputs/massive_test_50_report.json")
        if not report_path.exists():
            self._dynamic_adjustments = {}
            self._dynamic_config = self._base_dynamic_config()
            self._dynamic_report_mtime = None
            return
        
        try:
            mtime = report_path.stat().st_mtime
            if self._dynamic_report_mtime and mtime == self._dynamic_report_mtime:
                return
            
            data = json.loads(report_path.read_text(encoding='utf-8'))
            self._dynamic_adjustments = data or {}
            self._dynamic_report_mtime = mtime
            self._recompute_dynamic_config()
        except Exception as exc:
            logging.warning(f"No se pudo cargar reporte de test masivo: {exc}")
            self._dynamic_adjustments = {}
            self._dynamic_config = self._base_dynamic_config()
            self._dynamic_report_mtime = None

    def _base_dynamic_config(self) -> Dict[str, Any]:
        """Retorna la configuración base de pesos y umbrales."""
        return {
            'weights': {'semantic': 0.30, 'lexical': 0.25, 'rgi': 0.45},
            'min_semantic': 0.60,
            'max_suspect_conf': 0.65,
            'suspect_penalties': {},
            'suspect_min_semantic': 0.60,
            'review_low_conf': 0.38,
            'auto_clear_confidence': 0.58,
        }

    def _recompute_dynamic_config(self) -> None:
        """
        Ajusta pesos y penalizaciones en función del resumen del test masivo.
        Se aplican cambios suaves para evitar oscilaciones bruscas: pequeños ajustes
        sobre umbrales de sospechosos y reglas de revisión.
        """
        config = self._base_dynamic_config()
        data = self._dynamic_adjustments or {}
        summary = data.get('summary', data if isinstance(data, dict) else {})
        total = summary.get('total_products') or 0
        avg_confidence = summary.get('avg_confidence', 0.0) or 0.0
        suspicious_ratio = summary.get('suspicious_ratio', 0.0) or 0.0
        review_ratio = summary.get('review_ratio', 0.0) or 0.0
        top_hs_codes = summary.get('top_hs_codes', []) or []
        suspect_counts = summary.get('suspect_counts', {}) or {}

        # Si hay demasiados sospechosos generales, priorizar contexto/RGI.
        if suspicious_ratio > 0.6:
            config['weights'] = {'semantic': 0.25, 'lexical': 0.25, 'rgi': 0.50}
            config['min_semantic'] = 0.68
            config['max_suspect_conf'] = 0.55
        elif avg_confidence < 0.6 and suspicious_ratio <= 0.6:
            config['weights'] = {'semantic': 0.28, 'lexical': 0.32, 'rgi': 0.40}
            config['min_semantic'] = 0.58

        # Política de revisión dinámica: si estamos revisando demasiado, relajar un poco.
        if review_ratio > 0.6:
            config['max_suspect_conf'] = min(0.75, config['max_suspect_conf'] + 0.05)
            config['review_low_conf'] = min(0.45, config['review_low_conf'] + 0.05)
            config['auto_clear_confidence'] = max(0.58, config['auto_clear_confidence'] - 0.02)
        elif review_ratio and review_ratio < 0.35:
            config['max_suspect_conf'] = max(0.60, config['max_suspect_conf'] - 0.05)
            config['review_low_conf'] = max(0.35, config['review_low_conf'] - 0.03)
            config['auto_clear_confidence'] = min(0.65, config['auto_clear_confidence'] + 0.02)

        if total and top_hs_codes:
            top_entry = top_hs_codes[0]
            top_code = top_entry.get('hs')
            top_ratio = (top_entry.get('count', 0) / total) if total else 0.0
            if top_code in self._SUSPECT_CODES and top_ratio >= 0.20:
                config['suspect_penalties'][top_code] = min(0.25, 0.10 + top_ratio * 0.45)
                config['suspect_min_semantic'] = min(0.72, 0.62 + top_ratio * 0.15)

        if total:
            for suspect_code, count in suspect_counts.items():
                ratio = count / total
                if ratio >= 0.2:
                    current = config['suspect_penalties'].get(suspect_code, 0.0)
                    config['suspect_penalties'][suspect_code] = max(current, min(0.18, 0.05 + ratio * 0.35))

        self._dynamic_config = config

    def _evaluate_review_policy(
        self,
        chapter_coherence: bool,
        is_suspect: bool,
        final_confidence: float,
        validation_result: Dict[str, Any],
        keyword_hits: int,
        note_hits: int,
        review_notes: List[str]
    ) -> Tuple[bool, float, List[str]]:
        """Aplicar la política de revisión escalonada.

        Reglas resumidas:
        - Incoherencia de capítulo => revisión obligatoria (confianza contenida).
        - Códigos sospechosos con evidencia sólida pueden pasar sin revisión.
        - Casos no sospechosos con confianza ≥ umbral configurable se aceptan.
        - Confianzas muy bajas (< review_low_conf) forzan revisión.
        """
        reasons = list(dict.fromkeys(review_notes))
        validation_score = validation_result.get('validation_score', 1.0) or 0.0
        auto_clear = self._dynamic_config.get('auto_clear_confidence', 0.60)
        low_conf = self._dynamic_config.get('review_low_conf', 0.40)

        if 'chapter_incoherent' in reasons or not chapter_coherence:
            return True, max(0.0, min(final_confidence, 0.2)), reasons

        if final_confidence < low_conf:
            if 'low_confidence' not in reasons:
                reasons.append('low_confidence')
            return True, final_confidence, reasons

        relaxed_auto_clear = max(low_conf + 0.05, auto_clear - 0.07)

        if is_suspect:
            has_support = (keyword_hits >= 2) or (note_hits > 0) or (validation_score >= 0.8)
            if final_confidence >= 0.75 and has_support:
                reasons = [r for r in reasons if r not in ('suspect_code', 'suspect_low_semantic')]
                return False, final_confidence, reasons
            if final_confidence < 0.5 or validation_score < 0.7:
                if 'suspect_low_confidence' not in reasons:
                    reasons.append('suspect_low_confidence')
                return True, final_confidence, reasons
            if has_support and final_confidence >= 0.6:
                reasons = [r for r in reasons if r != 'suspect_code']
                return False, final_confidence, reasons
            if 'suspect_pending_review' not in reasons:
                reasons.append('suspect_pending_review')
            return True, final_confidence, reasons

        # No sospechoso: confianza suficiente + validación aceptable -> sin revisión.
        if chapter_coherence and final_confidence >= relaxed_auto_clear and validation_score >= 0.55:
            reasons = [r for r in reasons if r not in ('low_evidence', 'semantic_threshold_low', 'no_semantic_candidate')]
            return False, final_confidence, reasons

        if not is_suspect and chapter_coherence and final_confidence >= (auto_clear - 0.05) and validation_score >= 0.45:
            reasons = [r for r in reasons if r not in ('low_evidence', 'semantic_threshold_low', 'no_semantic_candidate')]
            return False, final_confidence, reasons

        if final_confidence >= auto_clear and validation_score >= 0.45:
            reasons = [r for r in reasons if r not in ('low_evidence', 'semantic_threshold_low', 'no_semantic_candidate')]
            return False, final_confidence, reasons

        if not is_suspect and chapter_coherence and final_confidence >= (low_conf + 0.08) and validation_score >= 0.4:
            reasons = [r for r in reasons if r not in ('low_evidence', 'semantic_threshold_low')]
            return False, final_confidence, reasons

        # En caso contrario, solo revisar si aún quedan motivos relevantes.
        blocking_reasons = [r for r in reasons if r not in ('low_evidence', 'semantic_threshold_low')]
        requires_review = len(blocking_reasons) > 0
        return requires_review, final_confidence, reasons