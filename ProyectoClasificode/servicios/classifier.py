from typing import Dict, Any, List
import json
import numpy as np
from rapidfuzz import fuzz
import unicodedata
import os

from .control_conexion import ControlConexion
from .modeloPln.embedding_service import EmbeddingService
from .modeloPln.nlp_service import NLPService
from .rules.rgi_engine import apply_all as rgi_apply_all
from .repos import CandidateRepository
from .learning_integration import learning_integration


class NationalClassifier:
    """
    Clasificador para bajar de HS6 a código nacional de 10 dígitos usando:
    - Vista v_current_tariff_items (vigencia)
    - attrs_json del caso para desambiguación
    - Similitud semántica con embeddings owner_type='tariff_item' como desempate
    - Reglas específicas para productos comunes
    """
    def __init__(self):
        self.cc = ControlConexion()
        self.embed = EmbeddingService()
        self.nlp = NLPService()
        self.candidate_repo = CandidateRepository()
        
        # Reglas específicas para productos comunes (mejora de precisión)
        self.specific_rules = {
            # Computadoras y electrónicos
            'computadora portatil': {'hs6': '847130', 'national_code': '8471300000', 'title': 'Máquinas automáticas para procesamiento de datos, portátiles'},
            'laptop': {'hs6': '847130', 'national_code': '8471300000', 'title': 'Máquinas automáticas para procesamiento de datos, portátiles'},
            'smartphone': {'hs6': '851712', 'national_code': '8517120000', 'title': 'Teléfonos inteligentes'},
            'tablet': {'hs6': '847130', 'national_code': '8471300000', 'title': 'Máquinas automáticas para procesamiento de datos, portátiles'},
            
            # Audio y parlantes
            'parlante': {'hs6': '851822', 'national_code': '8518220000', 'title': 'Altavoces múltiples, montados en un chasis común'},
            'altavoz': {'hs6': '851822', 'national_code': '8518220000', 'title': 'Altavoces múltiples, montados en un chasis común'},
            'speaker': {'hs6': '851822', 'national_code': '8518220000', 'title': 'Altavoces múltiples, montados en un chasis común'},
            'parlante bluetooth': {'hs6': '851822', 'national_code': '8518220000', 'title': 'Altavoces múltiples, montados en un chasis común'},
            'altavoz bluetooth': {'hs6': '851822', 'national_code': '8518220000', 'title': 'Altavoces múltiples, montados en un chasis común'},
            'parlante portatil': {'hs6': '851822', 'national_code': '8518220000', 'title': 'Altavoces múltiples, montados en un chasis común'},
            'altavoces escritorio': {'hs6': '851822', 'national_code': '8518220000', 'title': 'Altavoces múltiples, montados en un chasis común'},
            'subwoofer': {'hs6': '851822', 'national_code': '8518220000', 'title': 'Altavoces múltiples, montados en un chasis común'},
            'microfono': {'hs6': '851830', 'national_code': '8518300000', 'title': 'Micrófonos y sus soportes'},
            'microfono profesional': {'hs6': '851830', 'national_code': '8518300000', 'title': 'Micrófonos y sus soportes'},
            
            # Periféricos de computadora
            'mouse gaming': {'hs6': '847160', 'national_code': '8471600000', 'title': 'Dispositivos de entrada para máquinas automáticas de procesamiento de datos'},
            'mouse optico': {'hs6': '847160', 'national_code': '8471600000', 'title': 'Dispositivos de entrada para máquinas automáticas de procesamiento de datos'},
            'raton gaming': {'hs6': '847160', 'national_code': '8471600000', 'title': 'Dispositivos de entrada para máquinas automáticas de procesamiento de datos'},
            'teclado gaming': {'hs6': '847160', 'national_code': '8471600000', 'title': 'Dispositivos de entrada para máquinas automáticas de procesamiento de datos'},
            'auriculares gaming': {'hs6': '851830', 'national_code': '8518300000', 'title': 'Auriculares y micrófonos'},
            'auriculares bluetooth': {'hs6': '851830', 'national_code': '8518300000', 'title': 'Auriculares y micrófonos'},
            'monitor gaming': {'hs6': '852872', 'national_code': '8528720000', 'title': 'Monitores de visualización'},
            
            # Textiles y ropa
            'camiseta algodon': {'hs6': '610910', 'national_code': '6109100000', 'title': 'Camisetas de algodón'},
            'camiseta': {'hs6': '610910', 'national_code': '6109100000', 'title': 'Camisetas de algodón'},
            'pantalon jeans': {'hs6': '620342', 'national_code': '6203420000', 'title': 'Pantalones de algodón'},
            'zapatos deportivos': {'hs6': '640419', 'national_code': '6404190000', 'title': 'Calzado deportivo'},
            'tenis': {'hs6': '640419', 'national_code': '6404190000', 'title': 'Calzado deportivo'},
            
            # Animales y alimentos
            'ternero vivo': {'hs6': '010290', 'national_code': '0102900000', 'title': 'Animales vivos de la especie bovina'},
            'cafe grano': {'hs6': '090111', 'national_code': '0901110000', 'title': 'Café sin tostar, sin descafeinar'},
            'cafe tostado': {'hs6': '090121', 'national_code': '0901210000', 'title': 'Café tostado, sin descafeinar'},
            'chocolate': {'hs6': '180632', 'national_code': '1806320000', 'title': 'Chocolate y preparaciones alimenticias'},
            
            # Vehículos
            'automovil': {'hs6': '870321', 'national_code': '8703210000', 'title': 'Automóviles de turismo'},
            'motocicleta': {'hs6': '871120', 'national_code': '8711200000', 'title': 'Motocicletas'},
            'bicicleta': {'hs6': '871200', 'national_code': '8712000000', 'title': 'Bicicletas'},
            
            # Electrodomésticos
            'refrigerador': {'hs6': '841810', 'national_code': '8418100000', 'title': 'Refrigeradores y congeladores combinados'},
            'lavadora': {'hs6': '845011', 'national_code': '8450110000', 'title': 'Máquinas lavadoras de ropa'},
            'microondas': {'hs6': '851650', 'national_code': '8516500000', 'title': 'Hornos de microondas'},
            'licuadora': {'hs6': '850940', 'national_code': '8509400000', 'title': 'Licuadoras y mezcladoras'},
            
            # Herramientas
            'taladro': {'hs6': '820540', 'national_code': '8205400000', 'title': 'Taladros y destornilladores'},
            'martillo': {'hs6': '820520', 'national_code': '8205200000', 'title': 'Martillos y mazas'},
            'destornillador': {'hs6': '820540', 'national_code': '8205400000', 'title': 'Destornilladores y herramientas similares'},
            'sierra': {'hs6': '820210', 'national_code': '8202100000', 'title': 'Sierras de mano'},
            
            # Juguetes
            'juguete': {'hs6': '950300', 'national_code': '9503000000', 'title': 'Juguetes'},
            'muñeca': {'hs6': '950210', 'national_code': '9502100000', 'title': 'Muñecas'},
            'pelota': {'hs6': '950662', 'national_code': '9506620000', 'title': 'Pelotas de fútbol'},
            
            # Productos médicos
            'termometro': {'hs6': '902519', 'national_code': '9025190000', 'title': 'Termómetros'},
            'mascarilla': {'hs6': '630790', 'national_code': '6307900000', 'title': 'Artículos de confección'},
            'vendaje': {'hs6': '300510', 'national_code': '3005100000', 'title': 'Vendas, gasas y apósitos'},
            'jeringa': {'hs6': '901831', 'national_code': '9018310000', 'title': 'Jeringas'},
            
            # Materiales de construcción
            'cemento': {'hs6': '252310', 'national_code': '2523100000', 'title': 'Cementos hidráulicos'},
            'ladrillo': {'hs6': '690410', 'national_code': '6904100000', 'title': 'Ladrillos de construcción'},
            'pintura': {'hs6': '320890', 'national_code': '3208900000', 'title': 'Pinturas y barnices'},
            'madera pino': {'hs6': '440710', 'national_code': '4407100000', 'title': 'Madera de pino aserrada'},
            'vidrio templado': {'hs6': '700719', 'national_code': '7007190000', 'title': 'Vidrio templado de seguridad'},
            'arena construccion': {'hs6': '250510', 'national_code': '2505100000', 'title': 'Arena de construcción'},
            'arena rio': {'hs6': '250510', 'national_code': '2505100000', 'title': 'Arena de río'},
            'grava': {'hs6': '251710', 'national_code': '2517100000', 'title': 'Grava y piedra triturada'},
            
            # Productos químicos y limpieza
            'detergente': {'hs6': '340220', 'national_code': '3402200000', 'title': 'Detergentes líquidos'},
            'jabon tocador': {'hs6': '340111', 'national_code': '3401110000', 'title': 'Jabón de tocador'},
            'shampoo': {'hs6': '330510', 'national_code': '3305100000', 'title': 'Shampoo para el cabello'},
            'crema hidratante': {'hs6': '330499', 'national_code': '3304990000', 'title': 'Cremas hidratantes'},
            'pasta dental': {'hs6': '330610', 'national_code': '3306100000', 'title': 'Pasta dental'},
            
            # Alimentos específicos
            'aceite oliva': {'hs6': '150910', 'national_code': '1509100000', 'title': 'Aceite de oliva virgen extra'},
            'miel abeja': {'hs6': '040900', 'national_code': '0409000000', 'title': 'Miel de abeja natural'},
            'chocolate negro': {'hs6': '180632', 'national_code': '1806320000', 'title': 'Chocolate negro'},
            'atun enlatado': {'hs6': '160414', 'national_code': '1604140000', 'title': 'Atún enlatado'},
            'atun aceite': {'hs6': '160414', 'national_code': '1604140000', 'title': 'Atún en aceite'},
            'leche polvo': {'hs6': '040210', 'national_code': '0402100000', 'title': 'Leche en polvo'},
            'leche entera': {'hs6': '040110', 'national_code': '0401100000', 'title': 'Leche entera'},
            
            # Textiles específicos
            'chaqueta cuero': {'hs6': '620342', 'national_code': '6203420000', 'title': 'Chaquetas de cuero'},
            'vestido verano': {'hs6': '620442', 'national_code': '6204420000', 'title': 'Vestidos de verano'},
            
            # Vehículos y accesorios
            'neumatico': {'hs6': '401110', 'national_code': '4011100000', 'title': 'Neumáticos para automóviles'},
            'neumatico automovil': {'hs6': '401110', 'national_code': '4011100000', 'title': 'Neumáticos para automóvil'},
            'neumatico radial': {'hs6': '401110', 'national_code': '4011100000', 'title': 'Neumáticos radiales para automóvil'},
            'bateria automovil': {'hs6': '850720', 'national_code': '8507200000', 'title': 'Baterías de plomo-ácido para automóviles'},
            'bateria plomo acido': {'hs6': '850720', 'national_code': '8507200000', 'title': 'Baterías de plomo-ácido'},
            'faro led': {'hs6': '851220', 'national_code': '8512200000', 'title': 'Faros LED para automóviles'},
            
            # Electrodomésticos específicos
            'plancha vapor': {'hs6': '851640', 'national_code': '8516400000', 'title': 'Planchas de vapor'},
            'ventilador electrico': {'hs6': '841451', 'national_code': '8414510000', 'title': 'Ventiladores eléctricos'},
            'ventilador pedestal': {'hs6': '841451', 'national_code': '8414510000', 'title': 'Ventiladores de pedestal'},
            'botella pet': {'hs6': '392330', 'national_code': '3923300000', 'title': 'Botellas de PET'},
            'envase pet': {'hs6': '392330', 'national_code': '3923300000', 'title': 'Envases de PET'},
            
            # Herramientas específicas
            'nivel burbuja': {'hs6': '901580', 'national_code': '9015800000', 'title': 'Niveles de burbuja'},
            
            # Juguetes específicos
            'puzzle': {'hs6': '950300', 'national_code': '9503000000', 'title': 'Puzzles y rompecabezas'},
            
            # Productos médicos específicos
            'oximetro': {'hs6': '901819', 'national_code': '9018190000', 'title': 'Oxímetros de pulso'},
            
            # Nuevas reglas específicas para productos más detallados
            'camisa algodon': {'hs6': '610510', 'national_code': '6105100000', 'title': 'Camisas de algodón para hombre'},
            'reloj digital': {'hs6': '910211', 'national_code': '9102110000', 'title': 'Relojes digitales de pulsera'},
            'televisor led': {'hs6': '852872', 'national_code': '8528720000', 'title': 'Televisores LED'},
            'aspiradora': {'hs6': '850940', 'national_code': '8509400000', 'title': 'Aspiradoras eléctricas'},
            'cafetera electrica': {'hs6': '851671', 'national_code': '8516710000', 'title': 'Cafeteras eléctricas'},
            'impresora laser': {'hs6': '844332', 'national_code': '8443320000', 'title': 'Impresoras láser'},
            'telefono movil': {'hs6': '851712', 'national_code': '8517120000', 'title': 'Teléfonos móviles inteligentes'},
            'silla oficina': {'hs6': '940130', 'national_code': '9401300000', 'title': 'Sillas de oficina'},
            'escritorio madera': {'hs6': '940360', 'national_code': '9403600000', 'title': 'Escritorios de madera'},
            'sofa tres puestos': {'hs6': '940140', 'national_code': '9401400000', 'title': 'Sofás de tres puestos'},
            'colchon ortopedico': {'hs6': '940421', 'national_code': '9404210000', 'title': 'Colchones ortopédicos'},
            'lampara mesa led': {'hs6': '851310', 'national_code': '8513100000', 'title': 'Lámparas de mesa LED'},
            'bombillo led': {'hs6': '853950', 'national_code': '8539500000', 'title': 'Bombillos LED'},
            'cable electrico': {'hs6': '854442', 'national_code': '8544420000', 'title': 'Cables eléctricos'},
            'tuberia pvc': {'hs6': '391723', 'national_code': '3917230000', 'title': 'Tuberías de PVC'},
            'baldosa ceramica': {'hs6': '690890', 'national_code': '6908900000', 'title': 'Baldosas cerámicas'},
            'varilla corrugada': {'hs6': '721420', 'national_code': '7214200000', 'title': 'Varillas corrugadas'},
            'tornillos acero': {'hs6': '731814', 'national_code': '7318140000', 'title': 'Tornillos de acero'},
            'alambre cobre': {'hs6': '854411', 'national_code': '8544110000', 'title': 'Alambre de cobre'},
            'aceite lubricante': {'hs6': '271019', 'national_code': '2710190000', 'title': 'Aceites lubricantes'},
            'anticongelante': {'hs6': '382000', 'national_code': '3820000000', 'title': 'Anticongelantes'},
            'desinfectante': {'hs6': '380894', 'national_code': '3808940000', 'title': 'Desinfectantes'},
            'perfume spray': {'hs6': '330300', 'national_code': '3303000000', 'title': 'Perfumes en spray'},
            'galletas chocolate': {'hs6': '190590', 'national_code': '1905900000', 'title': 'Galletas con chocolate'},
            'jugo naranja': {'hs6': '200912', 'national_code': '2009120000', 'title': 'Jugo de naranja'},
            'leche entera': {'hs6': '040110', 'national_code': '0401100000', 'title': 'Leche entera'},
            'harina trigo': {'hs6': '110100', 'national_code': '1101000000', 'title': 'Harina de trigo'},
            'arroz blanco': {'hs6': '100630', 'national_code': '1006300000', 'title': 'Arroz blanco pulido'},
            'pescado congelado': {'hs6': '030499', 'national_code': '0304990000', 'title': 'Pescado congelado'},
            'pollo congelado': {'hs6': '020714', 'national_code': '0207140000', 'title': 'Pollo congelado'},
            'manzanas frescas': {'hs6': '080810', 'national_code': '0808100000', 'title': 'Manzanas frescas'},
            'flores frescas': {'hs6': '060311', 'national_code': '0603110000', 'title': 'Flores frescas cortadas'},
            'fertilizante npk': {'hs6': '310590', 'national_code': '3105900000', 'title': 'Fertilizantes NPK'},
            'semillas maiz': {'hs6': '100590', 'national_code': '1005900000', 'title': 'Semillas de maíz'},
            
            # Reglas específicas para productos técnicos e industriales
            'automovil hibrido': {'hs6': '870390', 'national_code': '8703900000', 'title': 'Automóviles híbridos'},
            'tractor agricola': {'hs6': '870190', 'national_code': '8701900000', 'title': 'Tractores agrícolas'},
            'excavadora hidraulica': {'hs6': '842952', 'national_code': '8429520000', 'title': 'Excavadoras hidráulicas'},
            'cosechadora granos': {'hs6': '843351', 'national_code': '8433510000', 'title': 'Cosechadoras de granos'},
            'motocicleta electrica': {'hs6': '871190', 'national_code': '8711900000', 'title': 'Motocicletas eléctricas'},
            'patineta electrica': {'hs6': '871190', 'national_code': '8711900000', 'title': 'Patinetas eléctricas'},
            'casco seguridad': {'hs6': '650610', 'national_code': '6506100000', 'title': 'Cascos de seguridad'},
            'chaleco reflectivo': {'hs6': '621143', 'national_code': '6211430000', 'title': 'Chalecos reflectivos'},
            'guantes nitrilo': {'hs6': '401519', 'national_code': '4015190000', 'title': 'Guantes de nitrilo'},
            'gafas proteccion': {'hs6': '900490', 'national_code': '9004900000', 'title': 'Gafas de protección'},
            'neumatico automovil': {'hs6': '401110', 'national_code': '4011100000', 'title': 'Neumáticos para automóvil'},
            'pastillas freno': {'hs6': '870830', 'national_code': '8708300000', 'title': 'Pastillas de freno'},
            'filtro aceite': {'hs6': '842123', 'national_code': '8421230000', 'title': 'Filtros de aceite'},
            'amortiguador': {'hs6': '870899', 'national_code': '8708990000', 'title': 'Amortiguadores'},
            'parachoques': {'hs6': '870829', 'national_code': '8708290000', 'title': 'Parachoques'},
            'retrovisor': {'hs6': '870899', 'national_code': '8708990000', 'title': 'Retrovisores'},
            'limpiaparabrisas': {'hs6': '870899', 'national_code': '8708990000', 'title': 'Limpiaparabrisas'},
            'radiador aluminio': {'hs6': '870891', 'national_code': '8708910000', 'title': 'Radiadores de aluminio'},
            'aceite hidraulico': {'hs6': '271019', 'national_code': '2710190000', 'title': 'Aceite hidráulico'},
            'grasa lubricante': {'hs6': '271019', 'national_code': '2710190000', 'title': 'Grasa lubricante'},
            'adhesivo epoxico': {'hs6': '350690', 'national_code': '3506900000', 'title': 'Adhesivo epóxico'},
            'sellante silicona': {'hs6': '321410', 'national_code': '3214100000', 'title': 'Sellante de silicona'},
            'tuberia pvc': {'hs6': '391732', 'national_code': '3917320000', 'title': 'Tubería de PVC'},
            'bolsa plastica': {'hs6': '392321', 'national_code': '3923210000', 'title': 'Bolsa plástica'},
            'envase pet': {'hs6': '392330', 'national_code': '3923300000', 'title': 'Envase PET'},
            'etiqueta autoadhesiva': {'hs6': '482110', 'national_code': '4821100000', 'title': 'Etiqueta autoadhesiva'},
            'caja carton': {'hs6': '481910', 'national_code': '4819100000', 'title': 'Caja de cartón'},
            'paleta madera': {'hs6': '441520', 'national_code': '4415200000', 'title': 'Paleta de madera'},
            'soldadora inverter': {'hs6': '851531', 'national_code': '8515310000', 'title': 'Soldadora inverter'},
            'compresor aire': {'hs6': '841430', 'national_code': '8414300000', 'title': 'Compresor de aire'},
            'bomba centrifuga': {'hs6': '841370', 'national_code': '8413700000', 'title': 'Bomba centrífuga'},
            'generador electrico': {'hs6': '850220', 'national_code': '8502200000', 'title': 'Generador eléctrico'},
            'motor electrico': {'hs6': '850153', 'national_code': '8501530000', 'title': 'Motor eléctrico'},
            'transformador electrico': {'hs6': '850431', 'national_code': '8504310000', 'title': 'Transformador eléctrico'},
            'panel solar': {'hs6': '854140', 'national_code': '8541400000', 'title': 'Panel solar fotovoltaico'},
            'inversor corriente': {'hs6': '850440', 'national_code': '8504400000', 'title': 'Inversor de corriente'},
            'cable fibra optica': {'hs6': '854470', 'national_code': '8544700000', 'title': 'Cable de fibra óptica'},
            'router wifi': {'hs6': '851762', 'national_code': '8517620000', 'title': 'Router WiFi'},
            'camara seguridad': {'hs6': '852580', 'national_code': '8525800000', 'title': 'Cámara de seguridad'},
            'sensor movimiento': {'hs6': '853110', 'national_code': '8531100000', 'title': 'Sensor de movimiento'},
            'placa circuito': {'hs6': '853400', 'national_code': '8534000000', 'title': 'Placa de circuito impreso'},
            'microcontrolador': {'hs6': '854231', 'national_code': '8542310000', 'title': 'Microcontrolador'},
            'modulo gps': {'hs6': '852691', 'national_code': '8526910000', 'title': 'Módulo GPS'},
            'resistor ceramico': {'hs6': '853321', 'national_code': '8533210000', 'title': 'Resistor cerámico'},
            'condensador electrolitico': {'hs6': '853222', 'national_code': '8532220000', 'title': 'Condensador electrolítico'},
            'fuente poder': {'hs6': '850440', 'national_code': '8504400000', 'title': 'Fuente de poder'},
            'bombilla halogena': {'hs6': '853921', 'national_code': '8539210000', 'title': 'Bombilla halógena'},
            'llanta motocicleta': {'hs6': '401140', 'national_code': '4011400000', 'title': 'Llanta de motocicleta'},
            
            # Productos adicionales para mejor precisión
            'smartphone samsung': {'hs6': '851712', 'national_code': '8517120000', 'title': 'Teléfonos inteligentes'},
            'iphone': {'hs6': '851712', 'national_code': '8517120000', 'title': 'Teléfonos inteligentes'},
            'tablet ipad': {'hs6': '847130', 'national_code': '8471300000', 'title': 'Máquinas automáticas para procesamiento de datos, portátiles'},
            'laptop dell': {'hs6': '847130', 'national_code': '8471300000', 'title': 'Máquinas automáticas para procesamiento de datos, portátiles'},
            'laptop hp': {'hs6': '847130', 'national_code': '8471300000', 'title': 'Máquinas automáticas para procesamiento de datos, portátiles'},
            'laptop lenovo': {'hs6': '847130', 'national_code': '8471300000', 'title': 'Máquinas automáticas para procesamiento de datos, portátiles'},
            'laptop asus': {'hs6': '847130', 'national_code': '8471300000', 'title': 'Máquinas automáticas para procesamiento de datos, portátiles'},
            'laptop acer': {'hs6': '847130', 'national_code': '8471300000', 'title': 'Máquinas automáticas para procesamiento de datos, portátiles'},
            'laptop macbook': {'hs6': '847130', 'national_code': '8471300000', 'title': 'Máquinas automáticas para procesamiento de datos, portátiles'},
            'monitor samsung': {'hs6': '852872', 'national_code': '8528720000', 'title': 'Monitores de visualización'},
            'monitor lg': {'hs6': '852872', 'national_code': '8528720000', 'title': 'Monitores de visualización'},
            'monitor dell': {'hs6': '852872', 'national_code': '8528720000', 'title': 'Monitores de visualización'},
            'monitor hp': {'hs6': '852872', 'national_code': '8528720000', 'title': 'Monitores de visualización'},
            'auriculares sony': {'hs6': '851830', 'national_code': '8518300000', 'title': 'Auriculares y micrófonos'},
            'auriculares bose': {'hs6': '851830', 'national_code': '8518300000', 'title': 'Auriculares y micrófonos'},
            'auriculares sennheiser': {'hs6': '851830', 'national_code': '8518300000', 'title': 'Auriculares y micrófonos'},
            'auriculares jbl': {'hs6': '851830', 'national_code': '8518300000', 'title': 'Auriculares y micrófonos'},
            'parlante jbl': {'hs6': '851822', 'national_code': '8518220000', 'title': 'Altavoces múltiples, montados en un chasis común'},
            'parlante bose': {'hs6': '851822', 'national_code': '8518220000', 'title': 'Altavoces múltiples, montados en un chasis común'},
            'parlante sony': {'hs6': '851822', 'national_code': '8518220000', 'title': 'Altavoces múltiples, montados en un chasis común'},
            'parlante logitech': {'hs6': '851822', 'national_code': '8518220000', 'title': 'Altavoces múltiples, montados en un chasis común'},
            'mouse logitech': {'hs6': '847160', 'national_code': '8471600000', 'title': 'Dispositivos de entrada para máquinas automáticas de procesamiento de datos'},
            'mouse razer': {'hs6': '847160', 'national_code': '8471600000', 'title': 'Dispositivos de entrada para máquinas automáticas de procesamiento de datos'},
            'mouse corsair': {'hs6': '847160', 'national_code': '8471600000', 'title': 'Dispositivos de entrada para máquinas automáticas de procesamiento de datos'},
            'teclado logitech': {'hs6': '847160', 'national_code': '8471600000', 'title': 'Dispositivos de entrada para máquinas automáticas de procesamiento de datos'},
            'teclado razer': {'hs6': '847160', 'national_code': '8471600000', 'title': 'Dispositivos de entrada para máquinas automáticas de procesamiento de datos'},
            'teclado corsair': {'hs6': '847160', 'national_code': '8471600000', 'title': 'Dispositivos de entrada para máquinas automáticas de procesamiento de datos'},
            'café colombia': {'hs6': '090111', 'national_code': '0901110000', 'title': 'Café sin tostar, sin descafeinar'},
            'café brasil': {'hs6': '090111', 'national_code': '0901110000', 'title': 'Café sin tostar, sin descafeinar'},
            'café etiopia': {'hs6': '090111', 'national_code': '0901110000', 'title': 'Café sin tostar, sin descafeinar'},
            'chocolate hershey': {'hs6': '180632', 'national_code': '1806320000', 'title': 'Chocolate y preparaciones alimenticias'},
            'chocolate nestle': {'hs6': '180632', 'national_code': '1806320000', 'title': 'Chocolate y preparaciones alimenticias'},
            'chocolate ferrero': {'hs6': '180632', 'national_code': '1806320000', 'title': 'Chocolate y preparaciones alimenticias'},
            
            # Reglas adicionales para mejor cobertura
            'café': {'hs6': '090111', 'national_code': '0901110000', 'title': 'Café sin tostar, sin descafeinar'},
            'cafe': {'hs6': '090111', 'national_code': '0901110000', 'title': 'Café sin tostar, sin descafeinar'},
            'coffee': {'hs6': '090111', 'national_code': '0901110000', 'title': 'Café sin tostar, sin descafeinar'},
            'café tostado': {'hs6': '090121', 'national_code': '0901210000', 'title': 'Café tostado, sin descafeinar'},
            'cafe tostado': {'hs6': '090121', 'national_code': '0901210000', 'title': 'Café tostado, sin descafeinar'},
            'café molido': {'hs6': '090121', 'national_code': '0901210000', 'title': 'Café tostado, sin descafeinar'},
            'cafe molido': {'hs6': '090121', 'national_code': '0901210000', 'title': 'Café tostado, sin descafeinar'},
            
            # Textiles adicionales
            'pantalón': {'hs6': '620342', 'national_code': '6203420000', 'title': 'Pantalones de algodón'},
            'pantalon': {'hs6': '620342', 'national_code': '6203420000', 'title': 'Pantalones de algodón'},
            'jeans': {'hs6': '620342', 'national_code': '6203420000', 'title': 'Pantalones de algodón'},
            'vaquero': {'hs6': '620342', 'national_code': '6203420000', 'title': 'Pantalones de algodón'},
            'zapato': {'hs6': '640419', 'national_code': '6404190000', 'title': 'Calzado deportivo'},
            'zapatos': {'hs6': '640419', 'national_code': '6404190000', 'title': 'Calzado deportivo'},
            'zapatilla': {'hs6': '640419', 'national_code': '6404190000', 'title': 'Calzado deportivo'},
            'zapatillas': {'hs6': '640419', 'national_code': '6404190000', 'title': 'Calzado deportivo'},
            'tenis': {'hs6': '640419', 'national_code': '6404190000', 'title': 'Calzado deportivo'},
            'sneakers': {'hs6': '640419', 'national_code': '6404190000', 'title': 'Calzado deportivo'},
            
            # Electrónicos adicionales
            'televisor': {'hs6': '852872', 'national_code': '8528720000', 'title': 'Monitores de visualización'},
            'tv': {'hs6': '852872', 'national_code': '8528720000', 'title': 'Monitores de visualización'},
            'television': {'hs6': '852872', 'national_code': '8528720000', 'title': 'Monitores de visualización'},
            'radio': {'hs6': '852712', 'national_code': '8527120000', 'title': 'Receptores de radio'},
            'cámara': {'hs6': '852580', 'national_code': '8525800000', 'title': 'Cámaras de televisión'},
            'camara': {'hs6': '852580', 'national_code': '8525800000', 'title': 'Cámaras de televisión'},
            'camera': {'hs6': '852580', 'national_code': '8525800000', 'title': 'Cámaras de televisión'},
            
            # Vehículos adicionales
            'carro': {'hs6': '870321', 'national_code': '8703210000', 'title': 'Automóviles de turismo'},
            'auto': {'hs6': '870321', 'national_code': '8703210000', 'title': 'Automóviles de turismo'},
            'coche': {'hs6': '870321', 'national_code': '8703210000', 'title': 'Automóviles de turismo'},
            'vehículo': {'hs6': '870321', 'national_code': '8703210000', 'title': 'Automóviles de turismo'},
            'vehiculo': {'hs6': '870321', 'national_code': '8703210000', 'title': 'Automóviles de turismo'},
            'moto': {'hs6': '871120', 'national_code': '8711200000', 'title': 'Motocicletas'},
            'motocicleta': {'hs6': '871120', 'national_code': '8711200000', 'title': 'Motocicletas'},
            'bici': {'hs6': '871200', 'national_code': '8712000000', 'title': 'Bicicletas'},
            'bicicleta': {'hs6': '871200', 'national_code': '8712000000', 'title': 'Bicicletas'},
            
            # Alimentos adicionales
            'arroz': {'hs6': '100630', 'national_code': '1006300000', 'title': 'Arroz'},
            'azúcar': {'hs6': '170114', 'national_code': '1701140000', 'title': 'Azúcar de caña'},
            'azucar': {'hs6': '170114', 'national_code': '1701140000', 'title': 'Azúcar de caña'},
            'sugar': {'hs6': '170114', 'national_code': '1701140000', 'title': 'Azúcar de caña'},
            'aceite': {'hs6': '150910', 'national_code': '1509100000', 'title': 'Aceite de oliva'},
            'aceite oliva': {'hs6': '150910', 'national_code': '1509100000', 'title': 'Aceite de oliva'},
            'aceite girasol': {'hs6': '151211', 'national_code': '1512110000', 'title': 'Aceite de girasol'},
            'leche': {'hs6': '040110', 'national_code': '0401100000', 'title': 'Leche'},
            'milk': {'hs6': '040110', 'national_code': '0401100000', 'title': 'Leche'},
            'pan': {'hs6': '1905', 'national_code': '1905000000', 'title': 'Pan'},
            'bread': {'hs6': '1905', 'national_code': '1905000000', 'title': 'Pan'},
            
            # Juguetes adicionales
            'juguete': {'hs6': '950300', 'national_code': '9503000000', 'title': 'Juguetes'},
            'toy': {'hs6': '950300', 'national_code': '9503000000', 'title': 'Juguetes'},
            'muñeca': {'hs6': '950210', 'national_code': '9502100000', 'title': 'Muñecas'},
            'muneca': {'hs6': '950210', 'national_code': '9502100000', 'title': 'Muñecas'},
            'doll': {'hs6': '950210', 'national_code': '9502100000', 'title': 'Muñecas'},
            'pelota': {'hs6': '950662', 'national_code': '9506620000', 'title': 'Pelotas de fútbol'},
            'ball': {'hs6': '950662', 'national_code': '9506620000', 'title': 'Pelotas de fútbol'},
            'balón': {'hs6': '950662', 'national_code': '9506620000', 'title': 'Pelotas de fútbol'},
            'balon': {'hs6': '950662', 'national_code': '9506620000', 'title': 'Pelotas de fútbol'},
            
            # Herramientas adicionales
            'herramienta': {'hs6': '820540', 'national_code': '8205400000', 'title': 'Herramientas'},
            'tool': {'hs6': '820540', 'national_code': '8205400000', 'title': 'Herramientas'},
            'llave': {'hs6': '820420', 'national_code': '8204200000', 'title': 'Llaves'},
            'wrench': {'hs6': '820420', 'national_code': '8204200000', 'title': 'Llaves'},
            'cuchillo': {'hs6': '821192', 'national_code': '8211920000', 'title': 'Cuchillos'},
            'knife': {'hs6': '821192', 'national_code': '8211920000', 'title': 'Cuchillos'},
            
            # Muebles
            'mesa': {'hs6': '940360', 'national_code': '9403600000', 'title': 'Mesas'},
            'table': {'hs6': '940360', 'national_code': '9403600000', 'title': 'Mesas'},
            'silla': {'hs6': '940130', 'national_code': '9401300000', 'title': 'Sillas'},
            'chair': {'hs6': '940130', 'national_code': '9401300000', 'title': 'Sillas'},
            'cama': {'hs6': '940360', 'national_code': '9403600000', 'title': 'Camas'},
            'bed': {'hs6': '940360', 'national_code': '9403600000', 'title': 'Camas'},
            'armario': {'hs6': '940360', 'national_code': '9403600000', 'title': 'Armarios'},
            'wardrobe': {'hs6': '940360', 'national_code': '9403600000', 'title': 'Armarios'},
        }

    def _fetch_tariff_options(self, hs6: str) -> List[Dict[str, Any]]:
        """Obtiene posibles aperturas nacionales vigentes para un HS6."""
        query = (
            "SELECT * FROM v_current_tariff_items "
            "WHERE substring(national_code, 1, 6) = :hs6"
        )
        df = self.cc.ejecutar_consulta_sql(query, {"hs6": hs6})
        if df.empty:
            return []
        return df.to_dict('records')

    def _select_by_semantics(self, text: str, options: List[Dict[str, Any]], features: Dict[str, Any] = None) -> Dict[str, Any]:
        """Selecciona la opción más semánticamente similar usando palabras clave mejoradas y features."""
        if not options:
            return {}
        
        if features is None:
            features = {}
        
        # Primero intentar selección por palabras clave mejorada
        text_lower = text.lower()
        best_match = None
        best_score = 0
        
        # Mapeo de palabras clave a categorías específicas
        category_keywords = {
            'textiles': ['camiseta', 'camisa', 'prenda', 'ropa', 'vestido', 'textil', 'algodón', 'gorra', 'sombrero', 'pantalón', 'falda'],
            'computadoras': ['computadora', 'portátil', 'laptop', 'ordenador', 'equipo', 'pc', 'notebook'],
            'alimentos': ['café', 'grano', 'semilla', 'tostado', 'alimento', 'comida', 'bebida'],
            'vehiculos': ['automóvil', 'carro', 'vehículo', 'coche', 'moto', 'bicicleta'],
            'electrodomesticos': ['refrigerador', 'nevera', 'frigorífico', 'lavadora', 'microondas', 'aire acondicionado'],
            'herramientas': ['taladro', 'martillo', 'destornillador', 'herramienta', 'sierra'],
            'animales': ['ternero', 'vivo', 'animal', 'ganado', 'bovino', 'vaca', 'toro']
        }
        
        # Pre-calcular embedding del texto del caso
        try:
            qvec = np.array(self.embed.generate_embedding(text))
        except Exception:
            qvec = None

        # Inferir dominio del texto para sesgos controlados
        domain = self._infer_domain(text_lower)
        
        # Detectar tipo de producto más sofisticado
        product_type = self._detect_product_type(text_lower, features)
        
        # Ajustar pesos dinámicamente según tipo de producto
        weight_config = self._get_dynamic_weights(product_type, domain)

        # Pre-cargar embeddings existentes para las opciones (owner_type=tariff_item)
        option_ids = [int(o.get('id')) for o in options if o.get('id') is not None]
        emb_map: Dict[int, np.ndarray] = {}
        if option_ids:
            try:
                in_clause = '(' + ','.join([str(i) for i in option_ids]) + ')'
                q = (
                    "SELECT owner_id, vector FROM embeddings "
                    "WHERE owner_type = 'tariff_item' AND owner_id IN " + in_clause
                )
                df_emb = self.cc.ejecutar_consulta_sql(q)
                for _, row in df_emb.iterrows():
                    vec_str = row['vector']
                    try:
                        emb_map[int(row['owner_id'])] = np.array(json.loads(vec_str))
                    except Exception:
                        s = str(vec_str).strip().strip('[]{}')
                        parts = [p for p in s.replace('{','').replace('}','').split(',') if p.strip()]
                        emb_map[int(row['owner_id'])] = np.array([float(p) for p in parts]) if parts else None
            except Exception:
                emb_map = {}

        # Recorrer opciones y calcular puntajes combinados
        scores: List[Dict[str, Any]] = []
        for opt in options:
            title = str(opt.get('title', '')).lower()
            keywords = str(opt.get('keywords', '')).lower()
            description = str(opt.get('description', '')).lower()
            item_text = f"{title} {keywords} {description}".strip()

            # 1) Puntaje léxico con RapidFuzz mejorado (0..100)
            lex_score = max(
                fuzz.token_set_ratio(text_lower, item_text),
                fuzz.partial_ratio(text_lower, item_text),
                fuzz.ratio(text_lower, item_text)
            )
            lex_norm = lex_score / 100.0

            # 2) Bonus por categorías específicas
            cat_bonus = 0.0
            for _, keywords_list in category_keywords.items():
                text_has_category = any(word in text_lower for word in keywords_list)
                item_has_category = any(word in item_text for word in keywords_list)
                if text_has_category and item_has_category:
                    cat_bonus += 0.1  # bonus pequeño acumulable

            # 3) Puntaje semántico si hay embeddings para el item
            sem_norm = 0.0
            if qvec is not None:
                v = emb_map.get(int(opt.get('id', -1)))
                if v is not None and v.size > 0:
                    denom = (np.linalg.norm(qvec) * np.linalg.norm(v))
                    if denom:
                        sim = float(np.dot(qvec, v) / denom)  # -1..1
                        sem_norm = (sim + 1.0) / 2.0          # 0..1

            # 4) Penalización por palabras claramente ajenas (evitar minerales para ropa, etc.)
            negative_words = ['mineral', 'minerales', 'manganeso', 'mena', 'concentrado', 'turba', 'colorante industrial']
            neg_penalty = 0.0
            if any(w in item_text for w in negative_words) and not any(w in text_lower for w in negative_words):
                neg_penalty = 0.25  # resta al score final
            
            # 4b) PENALIZACIONES POR FEATURES
            # --- MEJORA CLASIFICACIÓN HS CONTEXTUAL ---
            feature_penalty = 0.0
            feature_bonus = 0.0
            why_details = []
            
            # Aplicar penalizaciones y bonificaciones usando banderas contextuales
            tipo_bien = features.get('tipo_de_bien', '')
            uso_principal = features.get('uso_principal', '')
            nivel_proc = features.get('nivel_procesamiento', '')
            
            # Penalizar "partes y accesorios" si tipo_de_bien es "producto_terminado"
            if tipo_bien == 'producto_terminado' and ('partes' in item_text or 'accesorios' in item_text or 'parte' in item_text):
                feature_penalty += 0.5  # Penalización muy fuerte
                why_details.append("Descarte: es producto terminado pero subpartida es 'partes y accesorios'")
            
            # Bonificar "completo" si tipo_de_bien es "producto_terminado"
            if tipo_bien == 'producto_terminado' and ('completo' in item_text or 'equipo' in item_text or 'dispositivo' in item_text):
                feature_bonus += 0.3
                why_details.append("Coincide: producto terminado con subpartida de equipo completo")
            
            # Penalizar "producto terminado" si tipo_de_bien es "accesorio_repuesto"
            if tipo_bien == 'accesorio_repuesto' and ('completo' in item_text or 'equipo' in item_text):
                feature_penalty += 0.4
                why_details.append("Descarte: es accesorio pero subpartida es equipo completo")
            
            # Priorizar materia_prima en capítulos correctos
            if tipo_bien == 'materia_prima':
                chapter = ''.join([c for c in str(opt.get('national_code') or opt.get('hs6', '') or '') if c.isdigit()])[:2]
                if chapter and 1 <= int(chapter) <= 27:
                    feature_bonus += 0.3
                    why_details.append(f"Coincide: materia prima en capítulo {chapter} (materiales básicos)")
                elif chapter:
                    feature_penalty += 0.3
                    why_details.append(f"Descarte: materia prima en capítulo {chapter} incorrecto")
            
            # Priorizar según uso_principal
            chapter = ''.join([c for c in str(opt.get('national_code') or opt.get('hs6', '') or '') if c.isdigit()])[:2]
            
            if uso_principal == 'computo':
                if chapter in ['84', '85']:
                    feature_bonus += 0.35
                    why_details.append("Coincide: uso computo en capítulos 84/85 (máquinas)")
                    # Boost específico para laptops
                    if '8471' in str(opt.get('national_code') or ''):
                        feature_bonus += 0.4
                        why_details.append("Boost: laptop (8471) - Máquinas automáticas para procesamiento de datos")
                else:
                    feature_penalty += 0.3
                    why_details.append(f"Descarte: uso computo fuera de capítulos 84/85 (está en {chapter})")
            
            elif uso_principal == 'construccion':
                if chapter in ['25', '68', '69']:
                    feature_bonus += 0.3
                    why_details.append("Coincide: uso construcción en capítulos 25/68/69 (materiales construcción)")
                else:
                    feature_penalty += 0.25
                    why_details.append(f"Descarte: uso construcción fuera de capítulos 25/68/69 (está en {chapter})")
            
            elif uso_principal == 'alimentario':
                if chapter in ['09', '16', '17', '18', '19', '20']:
                    feature_bonus += 0.3
                    why_details.append("Coincide: uso alimentario en capítulos correctos")
                    # Boost para café sin tostar
                    if '0901' in str(opt.get('national_code') or ''):
                        feature_bonus += 0.4
                        why_details.append("Boost: café sin tostar (0901)")
                else:
                    feature_penalty += 0.2
                    why_details.append(f"Descarte: uso alimentario fuera de capítulos correctos (está en {chapter})")
            
            elif uso_principal == 'vestimenta':
                if chapter in ['61', '62', '63', '64']:
                    feature_bonus += 0.25
                    why_details.append("Coincide: uso vestimenta en capítulos 61-64 (textiles y calzado)")
            
            elif uso_principal == 'agropecuario':
                if chapter in ['01', '02', '03', '04', '05']:
                    feature_bonus += 0.35
                    why_details.append("Coincide: uso agropecuario en capítulos 01-05 (animales vivos)")
                else:
                    feature_penalty += 0.3
                    why_details.append(f"Descarte: uso agropecuario fuera de capítulos 01-05 (está en {chapter})")
            
            elif uso_principal == 'medico':
                if chapter in ['30', '38', '90']:
                    feature_bonus += 0.25
                    why_details.append("Coincide: uso médico en capítulos 30/38/90")
            
            # Bonificar uso médico (legacy)
            if features.get('uso_medico') and ('medico' in item_text or 'médico' in item_text or 'quirurgico' in item_text or 'quirúrgico' in item_text or 'hospital' in item_text):
                feature_bonus += 0.2
                why_details.append("Bonificado: uso médico detectado coincide con subpartida")
            
            # Bonificar animal vivo (legacy)
            if features.get('uso_animal_vivo') and ('vivo' in item_text or 'animal' in item_text or 'bovino' in item_text):
                feature_bonus += 0.2
                why_details.append("Bonificado: animal vivo detectado coincide con subpartida")
            
            # Bonificar inalámbrico (legacy)
            if features.get('inalambrico') and ('inalambrico' in item_text or 'inalámbrico' in item_text or 'wireless' in item_text):
                feature_bonus += 0.15
                why_details.append("Bonificado: característica inalámbrica coincide")
            # --- FIN MEJORA CLASIFICACIÓN HS CONTEXTUAL ---

            # 5) Señal full-text (ts_rank) sobre tariff_items sin cambiar la BD (on-the-fly)
            ft_norm = 0.0
            try:
                oid = int(opt.get('id', -1))
                if oid != -1:
                    q = (
                        "SELECT id, ts_rank_cd("
                        "to_tsvector('spanish', coalesce(title,'')||' '||coalesce(keywords,'')||' '||coalesce(notes,'')),"
                        "plainto_tsquery('spanish', :q)) AS r FROM tariff_items WHERE id = :oid"
                    )
                    df_rank = self.cc.ejecutar_consulta_sql(q, {"q": text, "oid": oid})
                    if not df_rank.empty:
                        r = float(df_rank.iloc[0]['r'] or 0.0)
                        # Normalización tosca: ts_rank suele ~[0..1]
                        ft_norm = max(0.0, min(1.0, r))
            except Exception:
                ft_norm = 0.0

            # 6) Score combinado con pesos dinámicos basados en tipo de producto
            w_sem = weight_config.get('semantic', 0.40)
            w_lex = weight_config.get('lexical', 0.35)
            w_cat = weight_config.get('category', 0.20)
            w_ft = weight_config.get('fulltext', 0.10)
            
            base_score = (w_sem * sem_norm + w_lex * lex_norm + w_cat * max(0.0, min(1.0, cat_bonus)) + w_ft * ft_norm)
            # Aplicar penalizaciones y bonificaciones de features
            score = base_score - neg_penalty - feature_penalty + feature_bonus
            
            # Guardar detalles del "por qué" en la opción para auditoría
            if why_details:
                opt['_why'] = why_details

            # 6) Sesgo por dominio usando prefijos de capítulos de national_code/hs6
            code_digits = ''.join([c for c in str(opt.get('national_code') or '') if c.isdigit()])
            if len(code_digits) < 2:
                code_digits = ''.join([c for c in str(opt.get('hs6') or '') if c.isdigit()])
            ch = code_digits[:2] if len(code_digits) >= 2 else ''
            boost = float(os.getenv('CLS_W_DOMAIN_BOOST', '0.1'))
            boost_e = float(os.getenv('CLS_W_DOMAIN_BOOST_E', '0.08'))
            boost_m = float(os.getenv('CLS_W_DOMAIN_BOOST_M', '0.06'))
            boost_min = float(os.getenv('CLS_W_DOMAIN_BOOST_MIN', '0.08'))
            if domain == 'textiles' and ch in ('61', '62'):
                score += boost
            elif domain == 'vehiculos' and ch == '87':
                score += boost
            elif domain == 'electronicos' and ch in ('84','85'):
                score += boost_e
            elif domain == 'medico' and ch in ('30','90'):
                score += boost_m
            elif domain == 'minerales' and ch in ('25','26','27'):
                score += boost_min
            elif domain == 'herramientas' and ch == '82':
                score += boost
            elif domain == 'calzado' and ch == '64':
                score += boost

            opt_scored = dict(opt)
            opt_scored['_score'] = float(score)
            scores.append(opt_scored)
            if score > best_score:
                best_score = score
                best_match = opt
        
        # Si encontramos una buena coincidencia por palabras clave, usarla
        if best_match and best_score > 10:
            # Attach ranked list for later (top-3)
            scores_sorted = sorted(scores, key=lambda o: o.get('_score', 0.0), reverse=True)
            self._last_ranked_options = scores_sorted[:3]
            return best_match
        
        # Si no, intentar con embeddings/lexical como respaldo adicional (fallback antiguo)
        try:
            # Construir embedding del texto del caso
            qvec = self.embed.generate_embedding(text)
            # Derivar hs6 desde las opciones (todas comparten mismo hs6)
            hs6 = None
            for opt in options:
                nc = str(opt.get('national_code') or '')
                digits = ''.join([c for c in nc if c.isdigit()])
                if len(digits) >= 6:
                    hs6 = digits[:6]
                    break
            if not hs6:
                return options[0]

            # Consultar embeddings de hs_items para ese HS6
            q = (
                "SELECT ev.owner_id, ev.vector "
                "FROM embeddings ev JOIN hs_items hi ON hi.id = ev.owner_id "
                "WHERE ev.owner_type = 'hs_item' AND replace(hi.hs_code, '.', '') LIKE :hs6pref"
            )
            df = self.cc.ejecutar_consulta_sql(q, {"hs6pref": f"{hs6}%"})
            if df.empty:
                return options[0]

            # Convertir a vectores numpy
            best = None
            best_sim = -1e9
            # qvec puede venir como np.ndarray shape (1,dim) según servicio
            q = qvec[0] if hasattr(qvec, 'shape') and len(qvec.shape) == 2 else qvec
            for _, row in df.iterrows():
                vec_str = row['vector']
                # vector se almacena como '[]' json o formato vector pgvector en nuestro código guardamos como ::vector desde json
                try:
                    # Intentar JSON primero
                    v = np.array(json.loads(vec_str))
                except Exception:
                    # Fallback: parseo simple de '{...}' o formato pgvector no json
                    s = str(vec_str).strip().strip('[]{}')
                    parts = [p for p in s.replace('{','').replace('}','').split(',') if p.strip()]
                    v = np.array([float(p) for p in parts]) if parts else None
                if v is None or v.size == 0:
                    continue
                # similitud coseno
                denom = (np.linalg.norm(q) * np.linalg.norm(v))
                sim = float(np.dot(q, v) / denom) if denom else -1e9
                if sim > best_sim:
                    best_sim = sim
                    best = int(row['owner_id'])

            if best is not None:
                for opt in options:
                    if int(opt.get('id', -1)) == best:
                        return opt
            
            # Si los embeddings fallan, usar la primera opción
            scores_sorted = sorted(scores, key=lambda o: o.get('_score', 0.0), reverse=True)
            self._last_ranked_options = scores_sorted[:3]
            return options[0]
            
        except Exception:
            # Si todo falla, usar la primera opción
            scores_sorted = sorted(scores, key=lambda o: o.get('_score', 0.0), reverse=True)
            self._last_ranked_options = scores_sorted[:3] if scores_sorted else []
            return options[0]

    def _try_specific_rules(self, text: str) -> Dict[str, Any]:
        """Intentar aplicar reglas específicas para productos comunes con coincidencias mejoradas"""
        def _norm(s: str) -> str:
            s = s.lower()
            s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
            for ch in [',', '.', ';', ':', '(', ')', '[', ']', '{', '}', '/', '\\', '-', '_', '%']:
                s = s.replace(ch, ' ')
            s = ' '.join(s.split())
            return s

        text_norm = _norm(text)
        
        # Aplicar preprocesamiento avanzado
        text_processed = self._preprocess_text(text)
        text_processed_norm = _norm(text_processed)
        
        # 1. Buscar coincidencias exactas de patrones existentes (normalizados)
        # MEJORA: Solo aplicar si hay coincidencia exacta o muy específica
        for pattern, rule in self.specific_rules.items():
            pattern_norm = _norm(pattern)
            # Solo aplicar si el patrón está completo en el texto, no como subcadena
            if pattern_norm == text_norm or pattern_norm == text_processed_norm:
                return rule
            # O si el patrón es una palabra completa dentro del texto
            elif pattern_norm in text_norm.split() or pattern_norm in text_processed_norm.split():
                return rule
        
        # 2. Coincidencias parciales mejoradas por categorías
        
        # Audio y parlantes (mejorado)
        audio_words = ['parlante', 'altavoz', 'speaker', 'sonido', 'audio', 'bocina', 'corneta']
        if any(word in text_norm or word in text_processed_norm for word in audio_words):
            if any(word in text_norm or word in text_processed_norm for word in ['bluetooth', 'inalámbrico', 'wireless', 'inalambrico']):
                return self.specific_rules.get('parlante bluetooth')
            elif any(word in text_norm or word in text_processed_norm for word in ['portátil', 'portatil', 'portable', 'movil', 'móvil']):
                return self.specific_rules.get('parlante portatil')
            elif any(word in text_norm or word in text_processed_norm for word in ['escritorio', 'desktop', 'subwoofer', 'woofer']):
                return self.specific_rules.get('altavoces escritorio')
            else:
                return self.specific_rules.get('parlante')
        
        # Micrófonos (mejorado)
        mic_words = ['microfono', 'micrófono', 'microphone', 'mic', 'micro']
        if any(word in text_norm or word in text_processed_norm for word in mic_words):
            if any(word in text_norm or word in text_processed_norm for word in ['profesional', 'streaming', 'grabación', 'grabacion', 'podcast']):
                return self.specific_rules.get('microfono profesional')
            else:
                return self.specific_rules.get('microfono')
        
        # Periféricos de computadora (mejorado)
        mouse_words = ['mouse', 'raton', 'ratón', 'gaming', 'optico', 'óptico', 'dpi', 'inalámbrico', 'inalambrico']
        if any(word in text_norm or word in text_processed_norm for word in mouse_words):
            if any(word in text_norm or word in text_processed_norm for word in ['mouse', 'raton', 'ratón']):
                if any(word in text_norm or word in text_processed_norm for word in ['gaming', 'gamer', 'rgb']):
                    return self.specific_rules.get('mouse gaming')
                else:
                    return self.specific_rules.get('mouse optico')
        
        if any(word in text_norm for word in ['teclado', 'keyboard', 'gaming']):
            if 'teclado' in text_norm or 'keyboard' in text_norm:
                return self.specific_rules.get('teclado gaming')
        
        if any(word in text_norm for word in ['auriculares', 'headphones', 'gaming', 'bluetooth']):
            if 'auriculares' in text_norm or 'headphones' in text_norm:
                if any(word in text_norm for word in ['bluetooth', 'inalámbrico']):
                    return self.specific_rules.get('auriculares bluetooth')
                else:
                    return self.specific_rules.get('auriculares gaming')
        
        if any(word in text_norm for word in ['monitor', 'pantalla', 'gaming']):
            if 'monitor' in text_norm or 'pantalla' in text_norm:
                return self.specific_rules.get('monitor gaming')
        
        # Textiles y ropa (mejorado)
        camiseta_words = ['camiseta', 'playera', 'remera', 'tshirt', 't shirt', 't-shirt', 'polo', 'camisa']
        if any(word in text_norm or word in text_processed_norm for word in camiseta_words):
            if any(word in text_norm or word in text_processed_norm for word in ['algodon', 'algodón', 'cotton', '100', 'cien']):
                return self.specific_rules.get('camiseta algodon')
            else:
                return self.specific_rules.get('camiseta')
        
        # Pantalones (mejorado)
        pantalon_words = ['pantalon', 'pantalón', 'jeans', 'vaquero', 'pantalones']
        if any(word in text_norm or word in text_processed_norm for word in pantalon_words):
            return self.specific_rules.get('pantalon jeans')
        
        # Chaquetas (mejorado)
        chaqueta_words = ['chaqueta', 'cazadora', 'abrigo', 'jacket', 'coat']
        if any(word in text_norm or word in text_processed_norm for word in chaqueta_words):
            if any(word in text_norm or word in text_processed_norm for word in ['cuero', 'leather', 'motociclista', 'moto']):
                return self.specific_rules.get('chaqueta cuero')
            else:
                return self.specific_rules.get('chaqueta')
        
        # Zapatos (mejorado)
        zapato_words = ['zapato', 'zapatos', 'zapatilla', 'zapatillas', 'tenis', 'sneakers', 'calzado']
        if any(word in text_norm or word in text_processed_norm for word in zapato_words):
            return self.specific_rules.get('zapato')
        
        # Vehículos (mejorado)
        vehiculo_words = ['carro', 'auto', 'coche', 'vehiculo', 'vehículo', 'automovil', 'automóvil']
        if any(word in text_norm or word in text_processed_norm for word in vehiculo_words):
            return self.specific_rules.get('automovil')
        
        # Motocicletas (mejorado)
        moto_words = ['moto', 'motocicleta', 'motorcycle', 'scooter']
        if any(word in text_norm or word in text_processed_norm for word in moto_words):
            return self.specific_rules.get('motocicleta')
        
        # Bicicletas (mejorado)
        bici_words = ['bici', 'bicicleta', 'bicycle', 'bike']
        if any(word in text_norm or word in text_processed_norm for word in bici_words):
            return self.specific_rules.get('bicicleta')
        
        # Alimentos básicos (mejorado)
        cafe_words = ['cafe', 'café', 'coffee']
        if any(word in text_norm or word in text_processed_norm for word in cafe_words):
            if any(word in text_norm or word in text_processed_norm for word in ['tostado', 'molido', 'tostado']):
                return self.specific_rules.get('cafe tostado')
            else:
                return self.specific_rules.get('cafe')
        
        # Chocolate (mejorado)
        chocolate_words = ['chocolate', 'cacao', 'cocoa']
        if any(word in text_norm or word in text_processed_norm for word in chocolate_words):
            return self.specific_rules.get('chocolate')
        
        # Juguetes (mejorado)
        juguete_words = ['juguete', 'toy', 'juego', 'game']
        if any(word in text_norm or word in text_processed_norm for word in juguete_words):
            return self.specific_rules.get('juguete')
        
        # Herramientas (mejorado)
        herramienta_words = ['herramienta', 'tool', 'taladro', 'martillo', 'destornillador', 'llave', 'cuchillo']
        if any(word in text_norm or word in text_processed_norm for word in herramienta_words):
            return self.specific_rules.get('herramienta')
        
        # Muebles (mejorado)
        mueble_words = ['mesa', 'table', 'silla', 'chair', 'cama', 'bed', 'armario', 'wardrobe']
        if any(word in text_norm or word in text_processed_norm for word in mueble_words):
            return self.specific_rules.get('mesa')
        
        if any(word in text_norm for word in ['vestido']):
            if any(word in text_norm for word in ['verano', 'summer', 'poliéster', 'poliester']):
                return self.specific_rules.get('vestido verano')
            else:
                return self.specific_rules.get('vestido')
        
        if any(word in text_norm for word in ['zapatos', 'zapatilla', 'tenis', 'deportivo']):
            if any(word in text_norm for word in ['deportivo', 'sport', 'running', 'atlético']):
                return self.specific_rules.get('zapatos deportivos')
            else:
                return self.specific_rules.get('tenis')
        
        # Computadoras
        if any(word in text_norm for word in ['computadora', 'laptop', 'notebook', 'portátil', 'portatil']):
            return self.specific_rules.get('computadora portatil')
        
        if any(word in text_norm for word in ['smartphone', 'celular', 'móvil', 'movil', 'telefono']):
            return self.specific_rules.get('smartphone')
        
        if any(word in text_norm for word in ['tablet', 'tableta', 'ipad']):
            return self.specific_rules.get('tablet')
        
        # Animales
        if any(word in text_norm for word in ['ternero', 'vivo', 'animal', 'ganado', 'bovino']):
            if 'vivo' in text_norm:
                return self.specific_rules.get('ternero vivo')
        
        # Alimentos
        if any(word in text_norm for word in ['cafe', 'café', 'grano']):
            if any(word in text_norm for word in ['tostado', 'molido']):
                return self.specific_rules.get('cafe tostado')
            else:
                return self.specific_rules.get('cafe grano')
        
        if any(word in text_norm for word in ['chocolate', 'cacao']):
            if any(word in text_norm for word in ['negro', 'dark', '70%']):
                return self.specific_rules.get('chocolate negro')
            else:
                return self.specific_rules.get('chocolate')
        
        if any(word in text_norm for word in ['aceite', 'oliva']):
            if any(word in text_norm for word in ['oliva', 'olive', 'virgen']):
                return self.specific_rules.get('aceite oliva')
        
        if any(word in text_norm for word in ['miel']):
            if any(word in text_norm for word in ['abeja', 'bee', 'natural']):
                return self.specific_rules.get('miel abeja')
        
        # Vehículos (MEJORADO - más específico)
        if any(word in text_norm for word in ['automovil', 'automóvil', 'carro', 'vehiculo']):
            if any(word in text_norm for word in ['turismo', 'pasajeros', 'sedan', 'hatchback']):
                return self.specific_rules.get('automovil')
        
        if any(word in text_norm for word in ['motocicleta', 'moto', 'motociclo']):
            if any(word in text_norm for word in ['motor', 'cilindrada', 'cc']):
                return self.specific_rules.get('motocicleta')
        
        if any(word in text_norm for word in ['bicicleta', 'bici', 'ciclo']):
            if any(word in text_norm for word in ['pedales', 'ruedas', 'manubrio']):
                return self.specific_rules.get('bicicleta')
        
        if any(word in text_norm for word in ['neumatico', 'neumático', 'llanta']):
            if any(word in text_norm for word in ['radial', 'automovil', 'automóvil', 'medida', 'pulgadas']):
                return self.specific_rules.get('neumatico radial')
        
        if any(word in text_norm for word in ['bateria', 'batería']):
            if any(word in text_norm for word in ['automovil', 'automóvil', 'plomo', 'acido', 'ácido', '12v']):
                return self.specific_rules.get('bateria automovil')
        
        if any(word in text_norm for word in ['faro', 'luz', 'led']):
            if any(word in text_norm for word in ['automovil', 'carro', 'vehiculo']):
                return self.specific_rules.get('faro led')
        
        # Electrodomésticos (MEJORADO - más específico)
        if any(word in text_norm for word in ['refrigerador', 'nevera', 'frigorífico']):
            if any(word in text_norm for word in ['domestico', 'doméstico', 'litros', 'consumo']):
                return self.specific_rules.get('refrigerador')
        
        if any(word in text_norm for word in ['lavadora', 'lavarropas']):
            if any(word in text_norm for word in ['automatica', 'automática', 'kg', 'carga']):
                return self.specific_rules.get('lavadora')
        
        if any(word in text_norm for word in ['microondas', 'horno']):
            if any(word in text_norm for word in ['litros', 'w', 'watts', 'potencia']):
                return self.specific_rules.get('microondas')
        
        if any(word in text_norm for word in ['licuadora', 'batidora']):
            if any(word in text_norm for word in ['electric', 'eléctrica', 'potencia']):
                return self.specific_rules.get('licuadora')
        
        if any(word in text_norm for word in ['ventilador']):
            if any(word in text_norm for word in ['electrico', 'eléctrico', 'pedestal', 'velocidades']):
                return self.specific_rules.get('ventilador electrico')
        
        if any(word in text_norm for word in ['plancha']):
            if any(word in text_norm for word in ['vapor', 'steam']):
                return self.specific_rules.get('plancha vapor')
        
        # Productos plásticos (MEJORADO - más específico)
        if any(word in text_norm for word in ['botella']):
            if any(word in text_norm for word in ['pet', 'plastica', 'plástica', 'transparente']):
                return self.specific_rules.get('botella pet')
        
        if any(word in text_norm for word in ['envase']):
            if any(word in text_norm for word in ['pet', 'plastico', 'plástico']):
                return self.specific_rules.get('envase pet')
        
        # Herramientas
        if any(word in text_norm for word in ['taladro', 'perforar']):
            return self.specific_rules.get('taladro')
        
        if any(word in text_norm for word in ['martillo', 'golpear']):
            return self.specific_rules.get('martillo')
        
        if any(word in text_norm for word in ['destornillador', 'atornillar']):
            return self.specific_rules.get('destornillador')
        
        if any(word in text_norm for word in ['sierra', 'cortar']):
            return self.specific_rules.get('sierra')
        
        if any(word in text_norm for word in ['nivel']):
            if any(word in text_norm for word in ['burbuja', 'bubble']):
                return self.specific_rules.get('nivel burbuja')
        
        # Juguetes
        if any(word in text_norm for word in ['juguete', 'toy']):
            return self.specific_rules.get('juguete')
        
        if any(word in text_norm for word in ['muñeca', 'doll']):
            return self.specific_rules.get('muñeca')
        
        if any(word in text_norm for word in ['pelota', 'balón', 'ball']):
            return self.specific_rules.get('pelota')
        
        if any(word in text_norm for word in ['puzzle', 'rompecabezas']):
            return self.specific_rules.get('puzzle')
        
        # Productos médicos
        if any(word in text_norm for word in ['termometro', 'termómetro', 'temperatura']):
            return self.specific_rules.get('termometro')
        
        if any(word in text_norm for word in ['mascarilla', 'máscara', 'protección']):
            return self.specific_rules.get('mascarilla')
        
        if any(word in text_norm for word in ['vendaje', 'venda', 'curación']):
            return self.specific_rules.get('vendaje')
        
        if any(word in text_norm for word in ['jeringa', 'inyección']):
            return self.specific_rules.get('jeringa')
        
        if any(word in text_norm for word in ['oximetro', 'oxímetro', 'pulso']):
            return self.specific_rules.get('oximetro')
        
        # Materiales de construcción (MEJORADO - más específico)
        if any(word in text_norm for word in ['arena']):
            if any(word in text_norm for word in ['construccion', 'construcción', 'rio', 'río', 'lavada']):
                return self.specific_rules.get('arena construccion')
        
        if any(word in text_norm for word in ['cemento']):
            if any(word in text_norm for word in ['portland', 'gris', 'hidraulico', 'hidráulico']):
                return self.specific_rules.get('cemento')
        
        if any(word in text_norm for word in ['ladrillo']):
            if any(word in text_norm for word in ['ceramico', 'cerámico', 'construccion', 'construcción']):
                return self.specific_rules.get('ladrillo')
        
        if any(word in text_norm for word in ['pintura']):
            if any(word in text_norm for word in ['acrilica', 'acrílica', 'blanca', 'interiores', 'exteriores']):
                return self.specific_rules.get('pintura')
        
        if any(word in text_norm for word in ['madera']):
            if any(word in text_norm for word in ['pino', 'pine', 'aserrada']):
                return self.specific_rules.get('madera pino')
        
        if any(word in text_norm for word in ['vidrio']):
            if any(word in text_norm for word in ['templado', 'tempered', 'seguridad']):
                return self.specific_rules.get('vidrio templado')
        
        # Productos químicos y limpieza
        if any(word in text_norm for word in ['detergente']):
            return self.specific_rules.get('detergente')
        
        if any(word in text_norm for word in ['jabon', 'jabón']):
            if any(word in text_norm for word in ['tocador', 'bath', 'barra']):
                return self.specific_rules.get('jabon tocador')
        
        if any(word in text_norm for word in ['shampoo', 'champú']):
            return self.specific_rules.get('shampoo')
        
        if any(word in text_norm for word in ['crema']):
            if any(word in text_norm for word in ['hidratante', 'moisturizer', 'cara']):
                return self.specific_rules.get('crema hidratante')
        
        if any(word in text_norm for word in ['pasta']):
            if any(word in text_norm for word in ['dental', 'toothpaste', 'flúor']):
                return self.specific_rules.get('pasta dental')
        
        # Nuevas reglas específicas para productos más detallados
        if any(word in text_norm for word in ['camisa']):
            if any(word in text_norm for word in ['algodon', 'algodón', 'hombre']):
                return self.specific_rules.get('camisa algodon')
        
        if any(word in text_norm for word in ['reloj']):
            if any(word in text_norm for word in ['digital', 'pulsera', 'pantalla']):
                return self.specific_rules.get('reloj digital')
        
        if any(word in text_norm for word in ['televisor']):
            if any(word in text_norm for word in ['led', '4k', 'hdmi']):
                return self.specific_rules.get('televisor led')
        
        if any(word in text_norm for word in ['aspiradora']):
            return self.specific_rules.get('aspiradora')
        
        if any(word in text_norm for word in ['cafetera']):
            if any(word in text_norm for word in ['electrica', 'eléctrica', 'goteo']):
                return self.specific_rules.get('cafetera electrica')
        
        if any(word in text_norm for word in ['impresora']):
            if any(word in text_norm for word in ['laser', 'láser', 'multifuncional']):
                return self.specific_rules.get('impresora laser')
        
        if any(word in text_norm for word in ['telefono', 'teléfono']):
            if any(word in text_norm for word in ['movil', 'móvil', 'inteligente', 'smartphone']):
                return self.specific_rules.get('telefono movil')
        
        if any(word in text_norm for word in ['silla']):
            if any(word in text_norm for word in ['oficina', 'ergonomica', 'ergonómica']):
                return self.specific_rules.get('silla oficina')
        
        if any(word in text_norm for word in ['escritorio']):
            if any(word in text_norm for word in ['madera', 'mdf', 'melaminico']):
                return self.specific_rules.get('escritorio madera')
        
        if any(word in text_norm for word in ['sofa', 'sofá']):
            if any(word in text_norm for word in ['tres', 'puestos', 'tapizado']):
                return self.specific_rules.get('sofa tres puestos')
        
        if any(word in text_norm for word in ['colchon', 'colchón']):
            if any(word in text_norm for word in ['ortopedico', 'ortopédico', 'resortes']):
                return self.specific_rules.get('colchon ortopedico')
        
        if any(word in text_norm for word in ['lampara', 'lámpara']):
            if any(word in text_norm for word in ['mesa', 'led', 'flexible']):
                return self.specific_rules.get('lampara mesa led')
        
        if any(word in text_norm for word in ['bombillo']):
            if any(word in text_norm for word in ['led', 'e27', 'luz']):
                return self.specific_rules.get('bombillo led')
        
        if any(word in text_norm for word in ['cable']):
            if any(word in text_norm for word in ['electrico', 'eléctrico', 'cobre']):
                return self.specific_rules.get('cable electrico')
        
        if any(word in text_norm for word in ['tuberia', 'tubería']):
            if any(word in text_norm for word in ['pvc', 'agua', 'potable']):
                return self.specific_rules.get('tuberia pvc')
        
        if any(word in text_norm for word in ['baldosa']):
            if any(word in text_norm for word in ['ceramica', 'cerámica', 'piso']):
                return self.specific_rules.get('baldosa ceramica')
        
        if any(word in text_norm for word in ['varilla']):
            if any(word in text_norm for word in ['corrugada', 'acero', 'carbono']):
                return self.specific_rules.get('varilla corrugada')
        
        if any(word in text_norm for word in ['tornillos']):
            if any(word in text_norm for word in ['acero', 'inoxidable', 'phillips']):
                return self.specific_rules.get('tornillos acero')
        
        if any(word in text_norm for word in ['alambre']):
            if any(word in text_norm for word in ['cobre', 'esmaltado', 'bobinado']):
                return self.specific_rules.get('alambre cobre')
        
        if any(word in text_norm for word in ['aceite']):
            if any(word in text_norm for word in ['lubricante', 'sintetico', 'sintético', 'motor']):
                return self.specific_rules.get('aceite lubricante')
        
        if any(word in text_norm for word in ['anticongelante']):
            return self.specific_rules.get('anticongelante')
        
        if any(word in text_norm for word in ['desinfectante']):
            return self.specific_rules.get('desinfectante')
        
        if any(word in text_norm for word in ['perfume']):
            if any(word in text_norm for word in ['spray', 'ml', 'florales']):
                return self.specific_rules.get('perfume spray')
        
        if any(word in text_norm for word in ['galletas']):
            if any(word in text_norm for word in ['chocolate', 'rellenas', 'dulces']):
                return self.specific_rules.get('galletas chocolate')
        
        if any(word in text_norm for word in ['jugo']):
            if any(word in text_norm for word in ['naranja', 'natural', 'pasteurizado']):
                return self.specific_rules.get('jugo naranja')
        
        if any(word in text_norm for word in ['leche']):
            if any(word in text_norm for word in ['entera', 'uht', 'fortificada']):
                return self.specific_rules.get('leche entera')
        
        if any(word in text_norm for word in ['harina']):
            if any(word in text_norm for word in ['trigo', 'panificacion', 'panificación']):
                return self.specific_rules.get('harina trigo')
        
        if any(word in text_norm for word in ['arroz']):
            if any(word in text_norm for word in ['blanco', 'pulido', 'grano largo']):
                return self.specific_rules.get('arroz blanco')
        
        if any(word in text_norm for word in ['pescado']):
            if any(word in text_norm for word in ['congelado', 'filete', 'vacío']):
                return self.specific_rules.get('pescado congelado')
        
        if any(word in text_norm for word in ['pollo']):
            if any(word in text_norm for word in ['congelado', 'entero', 'vísceras']):
                return self.specific_rules.get('pollo congelado')
        
        if any(word in text_norm for word in ['manzanas']):
            if any(word in text_norm for word in ['frescas', 'rojas', 'calibre']):
                return self.specific_rules.get('manzanas frescas')
        
        if any(word in text_norm for word in ['flores']):
            if any(word in text_norm for word in ['frescas', 'cortadas', 'rosa']):
                return self.specific_rules.get('flores frescas')
        
        if any(word in text_norm for word in ['fertilizante']):
            if any(word in text_norm for word in ['npk', 'granulado', '15-15-15']):
                return self.specific_rules.get('fertilizante npk')
        
        if any(word in text_norm for word in ['semillas']):
            if any(word in text_norm for word in ['maiz', 'maíz', 'hibrido', 'híbrido']):
                return self.specific_rules.get('semillas maiz')
        
        # Reglas específicas para productos técnicos e industriales
        if any(word in text_norm for word in ['automovil', 'automóvil']):
            if any(word in text_norm for word in ['hibrido', 'híbrido', 'gasolina', 'electrico']):
                return self.specific_rules.get('automovil hibrido')
        
        if any(word in text_norm for word in ['tractor']):
            if any(word in text_norm for word in ['agricola', 'agrícola', 'hp', 'traccion']):
                return self.specific_rules.get('tractor agricola')
        
        if any(word in text_norm for word in ['excavadora']):
            if any(word in text_norm for word in ['hidraulica', 'hidráulica', 'orugas', 'cuchara']):
                return self.specific_rules.get('excavadora hidraulica')
        
        if any(word in text_norm for word in ['cosechadora']):
            if any(word in text_norm for word in ['granos', 'autopropulsada', 'diesel']):
                return self.specific_rules.get('cosechadora granos')
        
        if any(word in text_norm for word in ['motocicleta']):
            if any(word in text_norm for word in ['electrica', 'eléctrica', 'w', 'velocidad']):
                return self.specific_rules.get('motocicleta electrica')
        
        if any(word in text_norm for word in ['patineta']):
            if any(word in text_norm for word in ['electrica', 'eléctrica', 'motor', 'bateria']):
                return self.specific_rules.get('patineta electrica')
        
        if any(word in text_norm for word in ['casco']):
            if any(word in text_norm for word in ['seguridad', 'motociclista', 'abs', 'visera']):
                return self.specific_rules.get('casco seguridad')
        
        if any(word in text_norm for word in ['chaleco']):
            if any(word in text_norm for word in ['reflectivo', 'poliéster', 'visibilidad']):
                return self.specific_rules.get('chaleco reflectivo')
        
        if any(word in text_norm for word in ['guantes']):
            if any(word in text_norm for word in ['nitrilo', 'industriales', 'químicos']):
                return self.specific_rules.get('guantes nitrilo')
        
        if any(word in text_norm for word in ['gafas']):
            if any(word in text_norm for word in ['proteccion', 'protección', 'uv', 'ajustables']):
                return self.specific_rules.get('gafas proteccion')
        
        if any(word in text_norm for word in ['neumatico', 'neumático']):
            if any(word in text_norm for word in ['automovil', 'automóvil', 'radial', 'camara']):
                return self.specific_rules.get('neumatico automovil')
        
        if any(word in text_norm for word in ['pastillas']):
            if any(word in text_norm for word in ['freno', 'disco', 'ceramico', 'cerámico']):
                return self.specific_rules.get('pastillas freno')
        
        if any(word in text_norm for word in ['filtro']):
            if any(word in text_norm for word in ['aceite', 'diesel', 'rosca']):
                return self.specific_rules.get('filtro aceite')
        
        if any(word in text_norm for word in ['amortiguador']):
            return self.specific_rules.get('amortiguador')
        
        if any(word in text_norm for word in ['parachoques']):
            return self.specific_rules.get('parachoques')
        
        if any(word in text_norm for word in ['retrovisor']):
            return self.specific_rules.get('retrovisor')
        
        if any(word in text_norm for word in ['limpiaparabrisas']):
            return self.specific_rules.get('limpiaparabrisas')
        
        if any(word in text_norm for word in ['radiador']):
            if any(word in text_norm for word in ['aluminio', 'motor', 'deposito']):
                return self.specific_rules.get('radiador aluminio')
        
        if any(word in text_norm for word in ['aceite']):
            if any(word in text_norm for word in ['hidraulico', 'hidráulico', 'iso', 'vg']):
                return self.specific_rules.get('aceite hidraulico')
        
        if any(word in text_norm for word in ['grasa']):
            if any(word in text_norm for word in ['lubricante', 'litio', 'goteo']):
                return self.specific_rules.get('grasa lubricante')
        
        if any(word in text_norm for word in ['adhesivo']):
            if any(word in text_norm for word in ['epoxico', 'epóxico', 'bicomponente']):
                return self.specific_rules.get('adhesivo epoxico')
        
        if any(word in text_norm for word in ['sellante']):
            if any(word in text_norm for word in ['silicona', 'transparente', 'cartucho']):
                return self.specific_rules.get('sellante silicona')
        
        if any(word in text_norm for word in ['tuberia', 'tubería']):
            if any(word in text_norm for word in ['pvc', 'polietileno', 'corrugada']):
                return self.specific_rules.get('tuberia pvc')
        
        if any(word in text_norm for word in ['bolsa']):
            if any(word in text_norm for word in ['plastica', 'plástica', 'polipropileno']):
                return self.specific_rules.get('bolsa plastica')
        
        if any(word in text_norm for word in ['envase']):
            if any(word in text_norm for word in ['pet', 'bebidas', 'tapa']):
                return self.specific_rules.get('envase pet')
        
        if any(word in text_norm for word in ['etiqueta']):
            if any(word in text_norm for word in ['autoadhesiva', 'impresa', 'papel']):
                return self.specific_rules.get('etiqueta autoadhesiva')
        
        if any(word in text_norm for word in ['caja']):
            if any(word in text_norm for word in ['carton', 'cartón', 'corrugado', 'embalaje']):
                return self.specific_rules.get('caja carton')
        
        if any(word in text_norm for word in ['paleta']):
            if any(word in text_norm for word in ['madera', 'carga', 'dimensiones']):
                return self.specific_rules.get('paleta madera')
        
        if any(word in text_norm for word in ['soldadora']):
            if any(word in text_norm for word in ['inverter', 'corriente', 'industrial']):
                return self.specific_rules.get('soldadora inverter')
        
        if any(word in text_norm for word in ['compresor']):
            if any(word in text_norm for word in ['aire', 'piston', 'pistón', 'tanque']):
                return self.specific_rules.get('compresor aire')
        
        if any(word in text_norm for word in ['bomba']):
            if any(word in text_norm for word in ['centrifuga', 'centrífuga', 'agua', 'caudal']):
                return self.specific_rules.get('bomba centrifuga')
        
        if any(word in text_norm for word in ['generador']):
            if any(word in text_norm for word in ['electrico', 'eléctrico', 'portatil', 'kva']):
                return self.specific_rules.get('generador electrico')
        
        if any(word in text_norm for word in ['motor']):
            if any(word in text_norm for word in ['electrico', 'eléctrico', 'trifasico', 'hp']):
                return self.specific_rules.get('motor electrico')
        
        if any(word in text_norm for word in ['transformador']):
            if any(word in text_norm for word in ['electrico', 'eléctrico', 'kva', 'aceite']):
                return self.specific_rules.get('transformador electrico')
        
        if any(word in text_norm for word in ['panel']):
            if any(word in text_norm for word in ['solar', 'fotovoltaico', 'w', 'monocristalino']):
                return self.specific_rules.get('panel solar')
        
        if any(word in text_norm for word in ['inversor']):
            if any(word in text_norm for word in ['corriente', 'onda', 'pura', 'dc']):
                return self.specific_rules.get('inversor corriente')
        
        if any(word in text_norm for word in ['cable']):
            if any(word in text_norm for word in ['fibra', 'optica', 'óptica', 'monomodo']):
                return self.specific_rules.get('cable fibra optica')
        
        if any(word in text_norm for word in ['router']):
            if any(word in text_norm for word in ['wifi', 'banda', 'ieee']):
                return self.specific_rules.get('router wifi')
        
        if any(word in text_norm for word in ['camara', 'cámara']):
            if any(word in text_norm for word in ['seguridad', 'ip', 'resolucion', 'nocturna']):
                return self.specific_rules.get('camara seguridad')
        
        if any(word in text_norm for word in ['sensor']):
            if any(word in text_norm for word in ['movimiento', 'pir', 'alcance', 'digital']):
                return self.specific_rules.get('sensor movimiento')
        
        if any(word in text_norm for word in ['placa']):
            if any(word in text_norm for word in ['circuito', 'pcb', 'doble', 'capa']):
                return self.specific_rules.get('placa circuito')
        
        if any(word in text_norm for word in ['microcontrolador']):
            return self.specific_rules.get('microcontrolador')
        
        if any(word in text_norm for word in ['modulo', 'módulo']):
            if any(word in text_norm for word in ['gps', 'antena', 'uart']):
                return self.specific_rules.get('modulo gps')
        
        if any(word in text_norm for word in ['resistor']):
            if any(word in text_norm for word in ['ceramico', 'cerámico', 'ohm', 'w']):
                return self.specific_rules.get('resistor ceramico')
        
        if any(word in text_norm for word in ['condensador']):
            if any(word in text_norm for word in ['electrolitico', 'electrolítico', 'microf', 'v']):
                return self.specific_rules.get('condensador electrolitico')
        
        if any(word in text_norm for word in ['fuente']):
            if any(word in text_norm for word in ['poder', 'conmutada', 'estabilizada']):
                return self.specific_rules.get('fuente poder')
        
        if any(word in text_norm for word in ['bombilla']):
            if any(word in text_norm for word in ['halogena', 'halógena', 'automovil', 'w']):
                return self.specific_rules.get('bombilla halogena')
        
        if any(word in text_norm for word in ['llanta']):
            if any(word in text_norm for word in ['motocicleta', 'radial', 'camara']):
                return self.specific_rules.get('llanta motocicleta')
        
        return None

    def _check_case_exists(self, case_id: int) -> bool:
        """Verifica si un caso existe en la base de datos"""
        try:
            query = "SELECT id FROM cases WHERE id = %s"
            result = self.cc.ejecutar_consulta_sql(query, (case_id,))
            return len(result) > 0
        except Exception:
            return False

    def classify(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """Clasifica un caso a código nacional de 10 dígitos y guarda candidate(rank=1)."""
        text = f"{case.get('product_title','')} {case.get('product_desc','')}".strip()
        attrs_raw = case.get('attrs_json')
        try:
            attrs = json.loads(attrs_raw) if isinstance(attrs_raw, str) else (attrs_raw or {})
        except Exception:
            attrs = {}

        # Preprocesar y normalizar texto usando NLP mejorado
        text_processed = self.nlp.preprocess_for_classification(text)
        text_original = text  # Guardar original para referencias
        
        # Extraer características mejoradas con banderas clave
        features = self.nlp.extract_classification_features(text)
        
        # También extraer características antiguas para compatibilidad
        features_old = self._extract_features(text)
        features.update(features_old)  # Combinar ambos

        # 0) Intentar reglas específicas primero (mejora de precisión)
        # Usar text_processed que tiene stopwords removidos
        specific_result = self._try_specific_rules(text_processed)
        if specific_result:
            print(f"[SUCCESS] Regla específica encontrada: {specific_result['title']}")
            # Guardar candidato con regla específica solo si el caso existe en BD
            try:
                # Verificar si el caso existe en la base de datos
                case_exists = self._check_case_exists(case['id'])
                if case_exists:
                    rationale = f"Clasificación por regla específica: {specific_result['title']}"
                    self.candidate_repo.create_candidates_batch([
                        {
                            'case_id': case['id'],
                            'hs_code': specific_result['national_code'] or specific_result['hs6'],
                            'hs6': specific_result['hs6'],
                            'national_code': specific_result['national_code'],
                            'title': specific_result['title'],
                            'confidence': 0.95,
                            'rationale': rationale,
                            'legal_refs_json': json.dumps({'method': 'specific_rule', 'pattern': 'matched'}),
                            'rank': 1,
                        }
                    ])
                else:
                    print(f"[LOG] Caso {case['id']} no existe en BD, no se guarda candidato")
            except Exception as e:
                print(f"Error guardando candidato: {e}")
                # Continuar sin fallar si no se puede guardar
            
            return {
                'case_id': case['id'],
                'hs6': specific_result['hs6'],
                'national_code': specific_result['national_code'],
                'title': specific_result['title'],
                'rgi_applied': ['Regla específica'],
                'legal_notes': [],
                'sources': [],
                'rationale': f"Clasificación por regla específica para productos comunes: {specific_result['title']}",
            }

        # --- MEJORA CLASIFICACIÓN HS CONTEXTUAL ---
        # 1) Ejecutar motor RGI -> HS6 + trazabilidad (con features para priorización contextual)
        rgi_result = rgi_apply_all(text, [], features=features)
        hs6 = rgi_result.get('hs6')
        trace = rgi_result.get('trace', [])
        # --- FIN MEJORA CLASIFICACIÓN HS CONTEXTUAL ---

        # Fallback HS6 si RGI no lo determinó
        if not hs6:
            hs6 = self._fallback_hs6(text)

        # 2) Obtener aperturas nacionales vigentes
        options = self._fetch_tariff_options(hs6) if hs6 else []
        if not options:
            return {
                'case_id': case['id'],
                'hs6': hs6 or '',
                'national_code': '',
                'title': '',
                'rgi_applied': [s.get('rgi') for s in trace],
                'legal_notes': self._collect_notes(trace),
                'sources': self._collect_sources(trace),
                'rationale': (("Identificación: " + str(features) + " | ") if features else '') + ('No hay aperturas nacionales vigentes para el HS6 identificado' if hs6 else 'No se pudo determinar un HS6 (RGI + fallback)'),
                'analysis': {'features': features},
            }

        # 3) Seleccionar exactamente un national_code
        # Heurística simple con attrs: priorizar por title/keywords si coincide con alguna clave del attrs
        chosen = None
        if attrs and options:
            attrs_text = ' '.join([str(v) for v in attrs.values() if v is not None]).lower()
            for opt in options:
                line = ' '.join([str(opt.get('title','')), str(opt.get('keywords','')), str(opt.get('notes',''))]).lower()
                # Si hay intersección mínima de términos, elegir
                hits = 0
                for token in set([t for t in attrs_text.split() if len(t) > 3]):
                    if token in line:
                        hits += 1
                        if hits >= 2:
                            chosen = opt
                            break
                if chosen:
                    break

        # Si sigue sin elegirse, usar similitud semántica con embeddings y features
        if chosen is None:
            chosen = self._select_by_semantics(text_processed if text_processed else text, options, features)

        national_code = str(chosen.get('national_code', '')).strip()
        title = chosen.get('title') or chosen.get('description') or ''

        # 4) Guardar candidate rank=1
        try:
            # Verificar si el caso existe en la base de datos
            case_exists = self._check_case_exists(case['id'])
            if case_exists:
                rationale = self._build_rationale(trace)
                self.candidate_repo.create_candidates_batch([
                    {
                        'case_id': case['id'],
                        'hs_code': national_code or hs6 or '',
                        'title': title or 'Tariff item',
                        'confidence': 0.95 if national_code else 0.7,
                        'rationale': rationale,
                        'legal_refs_json': json.dumps({
                            'rgi_applied': [s.get('rgi') for s in trace],
                            'trace': trace,
                        }),
                        'rank': 1,
                    }
                ])
                print(f"[LOG] Clasificación registrada: {national_code or hs6}")
            else:
                print(f"[LOG] Caso {case['id']} no existe en BD, no se guarda candidato")
        except Exception:
            pass

        # 5) Analizar resultado para aprendizaje automático
        try:
            learning_integration.analyze_classification_result(case, {
                'national_code': national_code,
                'title': title,
                'hs6': hs6
            })
        except Exception as e:
            print(f"⚠️ Error en sistema de aprendizaje: {e}")

        # Construir rationale detallado
        # --- MEJORA CLASIFICACIÓN HS CONTEXTUAL ---
        rationale_parts = []
        
        # Agregar features si existen
        if features:
            factores_clave = []
            
            # Nuevas features contextuales
            if features.get('tipo_de_bien'):
                factores_clave.append(f"tipo: {features['tipo_de_bien']}")
            if features.get('uso_principal'):
                factores_clave.append(f"uso: {features['uso_principal']}")
            if features.get('nivel_procesamiento'):
                factores_clave.append(f"procesamiento: {features['nivel_procesamiento']}")
            
            # Features legacy
            if features.get('es_equipo_completo'):
                factores_clave.append('producto completo (no repuesto)')
            if features.get('es_parte'):
                factores_clave.append('parte o accesorio')
            if features.get('uso_medico'):
                factores_clave.append('uso médico')
            if features.get('uso_animal_vivo'):
                factores_clave.append('animal vivo')
            if features.get('inalambrico'):
                factores_clave.append('inalámbrico')
            if features.get('materiales'):
                factores_clave.append(f"material: {', '.join(features['materiales'][:2])}")
            
            if factores_clave:
                rationale_parts.append(f"Factores clave: {', '.join(factores_clave)}")
        
        # Registrar descartes si existen
        if chosen and chosen.get('_why'):
            why_details = chosen['_why']
            descartes = [d for d in why_details if 'Descarte' in d or 'descarte' in d]
            if descartes:
                rationale_parts.append(f"Descartes: {', '.join(descartes[:2])}")
        # --- FIN MEJORA CLASIFICACIÓN HS CONTEXTUAL ---
        
        # Agregar RGI aplicado
        if trace:
            rationale_parts.append(f"RGI aplicado: {', '.join([s.get('rgi', '') for s in trace if s.get('rgi')])}")
        
        # Agregar detalles de selección si existen
        if chosen and chosen.get('_why'):
            rationale_parts.append(f"Selección: {', '.join(chosen['_why'][:3])}")
        
        rationale_final = ' | '.join(rationale_parts) if rationale_parts else 'Clasificación automática'

        return {
            'case_id': case['id'],
            'hs6': hs6,
            'national_code': national_code,
            'title': title,
            'rgi_applied': [s.get('rgi') for s in trace],
            'legal_notes': self._collect_notes(trace),
            'sources': self._collect_sources(trace),
            'rationale': rationale_final,
            'rationale_detail': {
                'regla_usada': 'RGI + Semántica' if trace else 'Semántica',
                'factores_clave': factores_clave if features else [],
                'rgi_trace': trace,
                'why_details': chosen.get('_why', []) if chosen else []
            },
            'analysis': {'features': features},
        }

    def _fallback_hs6(self, text: str) -> str:
        """Intentar proponer un HS6 cuando RGI no lo determinó, combinando búsqueda léxica y semántica sobre hs_items."""
        try:
            # 1) Recuperar candidatos hs_items filtrando por tokens relevantes para limitar el set
            tokens = [t for t in set(text.lower().replace(',', ' ').split()) if len(t) > 3]
            like_filters = ' OR '.join([f"title ILIKE '%{t}%'" for t in tokens[:6]])
            base_q = "SELECT id, hs_code, title, keywords FROM hs_items"
            q = base_q + (f" WHERE {like_filters} LIMIT 200" if like_filters else " LIMIT 200")
            df = self.cc.ejecutar_consulta_sql(q)
            if df.empty:
                return ''

            # 2) Pre-calcular embedding del texto
            try:
                qvec = np.array(self.embed.generate_embedding(text))
            except Exception:
                qvec = None

            # 3) Traer embeddings para hs_items candidatos
            emb_map = {}
            try:
                ids = [int(r['id']) for _, r in df.iterrows() if r.get('id') is not None]
                if ids:
                    in_clause = '(' + ','.join([str(i) for i in ids]) + ')'
                    qe = (
                        "SELECT owner_id, vector FROM embeddings "
                        "WHERE owner_type='hs_item' AND owner_id IN " + in_clause
                    )
                    df_emb = self.cc.ejecutar_consulta_sql(qe)
                    for _, row in df_emb.iterrows():
                        vec_str = row['vector']
                        try:
                            emb_map[int(row['owner_id'])] = np.array(json.loads(vec_str))
                        except Exception:
                            s = str(vec_str).strip().strip('[]{}')
                            parts = [p for p in s.replace('{','').replace('}','').split(',') if p.strip()]
                            emb_map[int(row['owner_id'])] = np.array([float(p) for p in parts]) if parts else None
            except Exception:
                emb_map = {}

            # 4) Calcular score combinado (semántico + léxico) y elegir mejor hs6, con sesgo por dominio
            garment_terms = ['chaqueta', 'abrigo', 'parka', 'anorak', 'cazadora', 'impermeable', 'prenda', 'ropa', 'sobretodo', 'saco']
            garment_intent = any(t in text.lower() for t in garment_terms)
            domain = self._infer_domain(text.lower())

            best_hs6 = ''
            best_score = -1.0
            for _, row in df.iterrows():
                item_text = f"{str(row.get('title') or '')} {str(row.get('keywords') or '')}"
                lex = fuzz.token_set_ratio(text, item_text) / 100.0
                sem = 0.0
                if qvec is not None:
                    v = emb_map.get(int(row['id']))
                    if v is not None and v.size > 0:
                        denom = (np.linalg.norm(qvec) * np.linalg.norm(v))
                        if denom:
                            sim = float(np.dot(qvec, v) / denom)
                            sem = (sim + 1.0) / 2.0
                w_sem_fb = float(os.getenv('CLS_FB_W_SEM', '0.6'))
                w_lex_fb = float(os.getenv('CLS_FB_W_LEX', '0.4'))
                score = w_sem_fb * sem + w_lex_fb * lex

                # Ajuste por dominio prendas de vestir
                hs = ''.join([c for c in str(row.get('hs_code') or '') if c.isdigit()])
                ch = hs[:2] if len(hs) >= 2 else ''
                if garment_intent or domain == 'textiles':
                    if ch in ('61', '62'):
                        score += float(os.getenv('CLS_W_GARMENT_BOOST', '0.15'))  # boost por capítulo de prendas
                    elif ch in ('05', '67'):
                        score -= float(os.getenv('CLS_W_GARMENT_PENALTY', '0.25'))  # penalización por materias primas (plumas)
                elif domain == 'vehiculos':
                    if ch == '87':
                        score += float(os.getenv('CLS_W_DOM_VEH', '0.12'))
                elif domain == 'electronicos':
                    if ch in ('84','85'):
                        score += float(os.getenv('CLS_W_DOM_ELEC', '0.10'))
                elif domain == 'minerales':
                    if ch in ('25','26','27'):
                        score += float(os.getenv('CLS_W_DOM_MIN', '0.10'))
                elif domain == 'herramientas':
                    if ch == '82':
                        score += float(os.getenv('CLS_W_DOM_TOOL', '0.12'))
                elif domain == 'calzado':
                    if ch == '64':
                        score += float(os.getenv('CLS_W_DOM_SHOE', '0.12'))

                if score > best_score:
                    hs6 = hs[:6] if len(hs) >= 6 else ''
                    if hs6:
                        best_score = score
                        best_hs6 = hs6

            return best_hs6
        except Exception:
            return ''

    @staticmethod
    def _collect_notes(trace: List[Dict[str, Any]]) -> List[int]:
        note_ids: List[int] = []
        for step in trace:
            for nid in step.get('legal_refs', {}).get('note_id', []) or []:
                if nid not in note_ids:
                    note_ids.append(nid)
        return note_ids

    @staticmethod
    def _collect_sources(trace: List[Dict[str, Any]]) -> List[str]:
        srcs: List[str] = []
        for step in trace:
            for s in step.get('sources', []) or []:
                if s not in srcs:
                    srcs.append(s)
        return srcs

    @staticmethod
    def _preprocess_text(text: str) -> str:
        """Normaliza y limpia el texto de entrada."""
        if not text:
            return ''
        # Convertir a minúsculas
        text = text.lower()
        # Normalizar espacios múltiples
        text = ' '.join(text.split())
        # Remover caracteres extraños pero mantener acentos y ñ
        import re as _re
        text = _re.sub(r'[^a-záéíóúüñ\s\d\.,%-]', ' ', text)
        text = ' '.join(text.split())
        return text
    
    @staticmethod
    def _infer_domain(text_lower: str) -> str:
        """Inferir un dominio general a partir del texto para aplicar sesgos suaves.
        Dominios: textiles, vehiculos, electronicos, medico, minerales, alimentos.
        """
        groups = {
            'textiles': ['camiseta','camisa','pantalon','chaqueta','abrigo','prenda','ropa','algodon','poliester','lana','tejido','cuero','zapato','bolso','gorra','plumas','impermeable'],
            'vehiculos': ['automovil','carro','vehiculo','moto','motocicleta','bicicleta','camion','bus','neumatico','llanta','chasis'],
            'electronicos': ['monitor','teclado','mouse','consola','led','bateria','refrigerador','lavadora','microondas','acondicionado','aspiradora','licuadora','plancha','sensor'],
            'medico': ['tensiometro','termometro','oximetro','mascarilla','guantes','vendaje','quirurgico','clinico'],
            'minerales': ['mineral','mena','concentrado','manganeso','hierro','cobre','turba','carbon'],
            'alimentos': ['cafe','azucar','harina','bebida','alimento','chocolate','leche'],
            'herramientas': ['martillo','taladro','destornillador','llave inglesa','sierra','cinta metrica','cuchillo','alicate'],
            'calzado': ['zapato','zapatilla','tenis','botin','bota','calzado','sandalia','deportivo','suela','antideslizante','malla']
        }
        for dom, kws in groups.items():
            if any(k in text_lower for k in kws):
                return dom
        return ''

    @staticmethod
    def _build_rationale(trace: List[Dict[str, Any]]) -> str:
        msgs = []
        for step in trace:
            msgs.append(f"{step.get('rgi')}: {step.get('decision')}")
        return ' | '.join(msgs) if msgs else 'Clasificación basada en RGI y vigencia DIAN'

    @staticmethod
    def _preprocess_text(text: str) -> str:
        """
        Procesamiento avanzado de texto con limpieza, normalización y extracción de características.
        Incluye: minúsculas, quitar ruido, lematización básica, y normalización de términos.
        """
        if not text:
            return ''
        
        import re as _re
        import unicodedata
        
        # 1. Convertir a minúsculas
        text = text.lower()
        
        # 2. Normalizar acentos y caracteres especiales
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        
        # 3. Quitar ruido y términos comerciales no relevantes (mejorado)
        noise_patterns = [
            r'\b(nuevo|original|100%|genuino|auténtico|oficial|premium|professional)\b',
            r'\b(certificado|garantía|warranty|certified|approved|tested)\b',
            r'\b(envío|envio|gratis|free|shipping|delivery)\b',
            r'\b(disponible|stock|inventario|venta|compra|precio|oferta)\b',
            r'\b(marca|brand|modelo|model|serie|version|versión)\b',
            r'\b(ref|referencia|code|código|codigo|sku|item)\b',
            r'\b(caja|box|pack|paquete|kit|set|conjunto)\b',
            r'\b(manual|instrucciones|guía|guide|documentation)\b',
            r'\b(accesorio|accessory|accesorios|accessories)\b',
            r'\b(color|colors|colores|tamaño|size|talla|tamano)\b',
            # Términos comerciales adicionales
            r'\b(unidad|unidades|pieza|piezas|par|pares|docena|docenas)\b',
            r'\b(envase|envases|empaque|empaques|bolsa|bolsas|frasco|frascos)\b',
            r'\b(contenido|neto|bruto|peso|volumen|capacidad|litros|gramos|kg)\b',
            r'\b(hecho|fabricado|manufacturado|producido|elaborado)\b',
            r'\b(importado|exportado|nacional|internacional|global)\b'
        ]
        
        for pattern in noise_patterns:
            text = _re.sub(pattern, ' ', text, flags=_re.IGNORECASE)
        
        # 4. Lematización básica de términos comunes
        lemmatization_map = {
            # Plurales comunes
            's': '', 'es': '', 'ces': '', 'ones': 'ón', 'anes': 'án',
            # Verbos comunes
            'ando': 'ar', 'iendo': 'er', 'yendo': 'ir',
            'ado': 'ar', 'ido': 'er', 'ido': 'ir',
            # Adjetivos
            'oso': 'o', 'osa': 'a', 'ivo': 'o', 'iva': 'a',
            # Terminaciones específicas
            'ción': 'ción', 'sión': 'sión', 'dad': 'dad', 'tad': 'tad'
        }
        
        # Aplicar lematización básica
        words = text.split()
        lemmatized_words = []
        for word in words:
            original_word = word
            for suffix, replacement in lemmatization_map.items():
                if word.endswith(suffix) and len(word) > len(suffix) + 2:
                    word = word[:-len(suffix)] + replacement
                    break
            lemmatized_words.append(word)
        
        text = ' '.join(lemmatized_words)
        
        # 5. Normalización de términos técnicos y comerciales
        technical_terms = {
            # Electrónicos
            'bluetooth': 'inalámbrico', 'wifi': 'inalámbrico', 'wireless': 'inalámbrico',
            'usb': 'conexión', 'hdmi': 'conexión', 'aux': 'conexión', 'auxiliar': 'conexión',
            'dpi': 'resolución', 'pixel': 'píxel', 'resolution': 'resolución',
            'battery': 'batería', 'bateria': 'batería', 'power': 'energía',
            'led': 'luz', 'lcd': 'pantalla', 'oled': 'pantalla', 'ips': 'pantalla',
            
            # Materiales
            'cotton': 'algodón', 'polyester': 'poliéster', 'poly': 'poliéster',
            'leather': 'cuero', 'plastic': 'plástico', 'metal': 'metal',
            'wood': 'madera', 'steel': 'acero', 'aluminum': 'aluminio',
            'rubber': 'caucho', 'silicone': 'silicona',
            
            # Medidas y unidades
            'inch': 'pulgada', 'inches': 'pulgadas', 'cm': 'centímetro', 'mm': 'milímetro',
            'kg': 'kilogramo', 'g': 'gramo', 'lb': 'libra', 'lbs': 'libras',
            'ml': 'mililitro', 'l': 'litro', 'oz': 'onza', 'fl': 'flujo',
            
            # Estados y condiciones
            'new': 'nuevo', 'used': 'usado', 'refurbished': 'reacondicionado',
            'damaged': 'dañado', 'broken': 'roto', 'working': 'funcionando',
            
            # Presentación
            'bulk': 'granel', 'pack': 'paquete', 'individual': 'individual',
            'set': 'conjunto', 'kit': 'kit', 'bundle': 'paquete'
        }
        
        for term, normalized in technical_terms.items():
            text = _re.sub(r'\b' + term + r'\b', normalized, text, flags=_re.IGNORECASE)
        
        # 6. Limpiar caracteres especiales pero mantener números y medidas
        text = _re.sub(r'[^a-záéíóúüñ\s\d\.,%-]', ' ', text)
        
        # 7. Normalizar espacios múltiples y eliminar palabras muy cortas
        words = [w for w in text.split() if len(w) > 2 or w.isdigit()]
        text = ' '.join(words)
        
        return text

    @staticmethod
    def _extract_features(text: str) -> Dict[str, Any]:
        """
        Extracción avanzada de características del texto de producto:
        - Materiales, uso/función, estado, presentación, incompleto/kit, modo de operación, sector, dimensiones
        - Señales RGI para 2(a) incompletos, 2(b) mezclas, 3(b) conjuntos/surtidos
        """
        import re as _re
        import unicodedata
        
        t = (text or '').lower()
        # Normalizar acentos
        t_norm = ''.join(c for c in unicodedata.normalize('NFD', t) if unicodedata.category(c) != 'Mn')
        feats: Dict[str, Any] = {}
        
        # 1. MATERIALES (expandido)
        materials = []
        material_keywords = {
            # Metales
            'acero': ['steel', 'hierro', 'metal', 'metálico'],
            'aluminio': ['aluminum', 'aluminium', 'metálico'],
            'cobre': ['copper', 'metálico'],
            'hierro': ['iron', 'metálico'],
            'bronce': ['bronze', 'metálico'],
            'plata': ['silver', 'metálico'],
            'oro': ['gold', 'metálico'],
            
            # Textiles
            'algodón': ['cotton', 'algodon', 'textil', 'fibra'],
            'poliéster': ['polyester', 'poliester', 'textil', 'fibra'],
            'lana': ['wool', 'textil', 'fibra'],
            'seda': ['silk', 'textil', 'fibra'],
            'lino': ['linen', 'textil', 'fibra'],
            'cuero': ['leather', 'piel', 'textil'],
            'sintético': ['synthetic', 'sintetico', 'textil', 'fibra'],
            'malla': ['mesh', 'red', 'textil'],
            
            # Plásticos y polímeros
            'plástico': ['plastic', 'plastico', 'pvc', 'polímero'],
            'goma': ['rubber', 'caucho', 'elástico'],
            'silicona': ['silicone', 'silicon'],
            
            # Otros materiales
            'madera': ['wood', 'timber', 'leño'],
            'vidrio': ['glass', 'cristal'],
            'cerámica': ['ceramic', 'ceramica', 'porcelana'],
            'papel': ['paper', 'cartón', 'carton'],
            'cartón': ['cardboard', 'carton', 'papel'],
        }
        
        for material, synonyms in material_keywords.items():
            if material in t_norm or any(syn in t_norm for syn in synonyms):
                materials.append(material)
        
        if materials:
            feats['materiales'] = materials
        
        # 2. USO/FUNCIÓN (expandido)
        usage_keywords = {
            'deportivo': ['sport', 'deporte', 'atlético', 'athletic', 'fitness', 'gym', 'ejercicio'],
            'industrial': ['industrial', 'profesional', 'comercial', 'business', 'manufactura'],
            'médico': ['medical', 'medico', 'hospital', 'clínico', 'clinical', 'sanitario', 'salud'],
            'construcción': ['construction', 'construccion', 'obra', 'edificación', 'building'],
            'carpintería': ['carpentry', 'carpinteria', 'madera', 'woodworking', 'maderero'],
            'cocina': ['kitchen', 'cocina', 'culinario', 'culinary', 'gastronomía'],
            'hogar': ['home', 'hogar', 'doméstico', 'domestic', 'household', 'casa'],
            'automotriz': ['automotive', 'automotriz', 'vehículo', 'vehicle', 'car', 'auto'],
            'infantil': ['children', 'infantil', 'niño', 'baby', 'kids', 'child', 'bebé'],
            'oficina': ['office', 'oficina', 'escolar', 'school', 'academic', 'trabajo'],
            'jardinería': ['gardening', 'jardineria', 'jardín', 'garden', 'plantas'],
            'decoración': ['decoration', 'decoracion', 'decorativo', 'ornamental', 'arte'],
            'seguridad': ['security', 'seguridad', 'protección', 'protection', 'vigilancia'],
            'comunicación': ['communication', 'comunicacion', 'telecomunicaciones', 'telecom'],
            'gaming': ['gaming', 'gamer', 'juego', 'videojuego', 'esports', 'gaming'],
            'audio': ['audio', 'sonido', 'música', 'music', 'acústico', 'acoustic'],
            'fotografía': ['photography', 'fotografia', 'cámara', 'camera', 'foto'],
            'iluminación': ['lighting', 'iluminacion', 'luz', 'light', 'led', 'lámpara'],
        }
        
        for usage, synonyms in usage_keywords.items():
            if usage in t_norm or any(syn in t_norm for syn in synonyms):
                feats['uso'] = usage
                break
        
        # 3. ESTADO (crudo, procesado, etc.)
        state_keywords = {
            'crudo': ['raw', 'crudo', 'natural', 'sin procesar', 'unprocessed'],
            'procesado': ['processed', 'procesado', 'elaborado', 'manufacturado'],
            'cocido': ['cooked', 'cocido', 'preparado', 'ready'],
            'congelado': ['frozen', 'congelado', 'freeze'],
            'seco': ['dry', 'seco', 'deshidratado'],
            'líquido': ['liquid', 'liquido', 'fluido'],
            'sólido': ['solid', 'solido', 'compacto'],
            'polvo': ['powder', 'polvo', 'dust'],
            'granulado': ['granular', 'granulado', 'grain'],
        }
        
        for state, synonyms in state_keywords.items():
            if state in t_norm or any(syn in t_norm for syn in synonyms):
                feats['estado'] = state
                break
        
        # 4. PRESENTACIÓN (a granel/envase, etc.)
        presentation_keywords = {
            'granel': ['bulk', 'granel', 'suelto', 'a granel'],
            'envase': ['packaged', 'envase', 'empaque', 'packaging'],
            'individual': ['individual', 'unit', 'single', 'unidad'],
            'paquete': ['pack', 'paquete', 'packet', 'bundle'],
            'caja': ['box', 'caja', 'carton'],
            'bolsa': ['bag', 'bolsa', 'sack'],
            'botella': ['bottle', 'botella', 'frasco'],
            'lata': ['can', 'lata', 'tin'],
        }
        
        for presentation, synonyms in presentation_keywords.items():
            if presentation in t_norm or any(syn in t_norm for syn in synonyms):
                feats['presentación'] = presentation
                break
        
        # 5. MODO DE OPERACIÓN (eléctrico/no)
        operation_keywords = {
            'eléctrico': ['electric', 'electrico', 'electrical', 'powered', 'battery', 'batería'],
            'mecánico': ['mechanical', 'mecanico', 'manual', 'hand-operated'],
            'hidráulico': ['hydraulic', 'hidraulico', 'water-powered'],
            'neumático': ['pneumatic', 'neumatico', 'air-powered'],
            'solar': ['solar', 'sun-powered', 'photovoltaic'],
            'gas': ['gas-powered', 'gasolina', 'fuel'],
        }
        
        for operation, synonyms in operation_keywords.items():
            if operation in t_norm or any(syn in t_norm for syn in synonyms):
                feats['modo_operación'] = operation
                break
        
        # 6. SECTOR (textil, maquinaria, alimentos, etc.)
        sector_keywords = {
            'textil': ['textile', 'textil', 'clothing', 'ropa', 'vestimenta', 'prenda'],
            'maquinaria': ['machinery', 'maquinaria', 'machine', 'máquina', 'equipment'],
            'alimentos': ['food', 'alimento', 'foodstuff', 'comestible', 'beverage', 'bebida'],
            'electrónico': ['electronic', 'electronico', 'electrical', 'electric'],
            'farmacéutico': ['pharmaceutical', 'farmaceutico', 'medical', 'medicinal'],
            'químico': ['chemical', 'quimico', 'chemicals'],
            'construcción': ['construction', 'construccion', 'building', 'edificación'],
            'automotriz': ['automotive', 'automotriz', 'vehicle', 'vehículo'],
            'juguete': ['toy', 'juguete', 'game', 'juego'],
            'mueble': ['furniture', 'mueble', 'furnishing'],
        }
        
        for sector, synonyms in sector_keywords.items():
            if sector in t_norm or any(syn in t_norm for syn in synonyms):
                feats['sector'] = sector
                break
        
        # 7. DIMENSIONES/TEJIDO/GRAMAJES
        # Dimensiones
        dimensions = _re.findall(r"(\d+(?:[\.\,]\d+)?)(?:\s*)(mm|cm|m|inch|inches|pulgadas|kg|g|l|ml|w|v|ah|cc|btu)", t_norm)
        if dimensions:
            feats['dimensiones'] = [f"{d[0]}{d[1]}" for d in dimensions]
        
        # Gramaje para textiles
        gramaje_patterns = [
            r'(\d+)\s*g/m[²2]', r'(\d+)\s*gsm', r'(\d+)\s*gramos?\s*por\s*metro',
            r'(\d+)\s*oz/yd[²2]', r'(\d+)\s*ounces?\s*per\s*yard'
        ]
        
        for pattern in gramaje_patterns:
            match = _re.search(pattern, t_norm)
            if match:
                feats['gramaje'] = match.group(1)
                break
        
        # 8. SEÑALES RGI
        
        # RGI 2(a) - Incompletos/desarmados
        rgi2a_signals = ['incompleto', 'incomplete', 'desarmado', 'disassembled', 'sin terminar', 'unfinished', 
                        'semiarmado', 'semi-assembled', 'parte', 'part', 'componente', 'component', 
                        'repuesto', 'spare', 'accesorio', 'accessory']
        
        if any(signal in t_norm for signal in rgi2a_signals):
            feats['rgi_2a_incompleto'] = True
        
        # RGI 2(b) - Mezclas/conjuntos
        rgi2b_signals = ['mezcla', 'mixture', 'mixto', 'mixed', 'conjunto', 'set', 'kit', 'combinado', 
                        'combined', 'surtico', 'assortment', 'variedad', 'variety', 'colección', 'collection']
        
        if any(signal in t_norm for signal in rgi2b_signals):
            feats['rgi_2b_mezcla'] = True
        
        # RGI 3(b) - Conjuntos/surtidos
        rgi3b_signals = ['conjunto', 'set', 'kit', 'paquete', 'pack', 'bundle', 'surtico', 'assortment',
                        'colección', 'collection', 'lote', 'lot', 'grupo', 'group']
        
        if any(signal in t_norm for signal in rgi3b_signals):
            feats['rgi_3b_conjunto'] = True
        
        # 9. TIPO DE PRODUCTO (palabras clave expandidas)
        product_type_keywords = [
            # Herramientas
            'martillo', 'taladro', 'destornillador', 'sierra', 'nivel', 'multímetro', 'tijeras', 'llave', 'alicate',
            # Ropa
            'chaqueta', 'camiseta', 'pantalón', 'pantalon', 'zapato', 'zapatilla', 'tenis', 'calzado', 'vestido', 'falda', 'blusa',
            # Electrodomésticos
            'refrigerador', 'lavadora', 'microondas', 'horno', 'licuadora', 'tostadora', 'plancha',
            # Electrónicos
            'computadora', 'laptop', 'smartphone', 'tablet', 'monitor', 'teclado', 'mouse', 'auriculares', 'altavoz', 'parlante',
            # Vehículos
            'automóvil', 'automovil', 'motocicleta', 'bicicleta', 'camión', 'camion', 'neumático', 'neumatico',
            # Alimentos
            'café', 'cafe', 'chocolate', 'miel', 'cerveza', 'vino', 'aceite', 'leche', 'queso', 'pan', 'arroz',
            # Construcción
            'cemento', 'ladrillo', 'pintura', 'madera', 'acero', 'vidrio',
            # Juguetes
            'juguete', 'muñeca', 'puzzle', 'pelota', 'tren', 'carro', 'oso', 'bloques',
            # Médicos
            'termómetro', 'termometro', 'mascarilla', 'vendaje', 'jeringa', 'medicina', 'vitamina',
            # Oficina
            'lápiz', 'lapiz', 'cuaderno', 'bolígrafo', 'boligrafo', 'pincel', 'papel', 'goma', 'regla', 'calculadora'
        ]
        
        for kw in product_type_keywords:
            if kw in t_norm:
                feats['tipo_producto'] = kw
                break
        
        return feats

    def _detect_product_type(self, text_lower: str, features: Dict[str, Any]) -> str:
        """
        Detecta el tipo de producto de manera más sofisticada.
        Retorna: 'materia_prima', 'producto_tecnologico', 'textil_vestimenta', 
                 'herramienta', 'vehiculo', 'alimento', 'equipo_medico', 'otros'
        """
        # Materias primas
        materia_prima_keywords = ['arena', 'grava', 'piedra', 'mineral', 'mena', 'concentrado', 
                                  'acero', 'aluminio', 'cobre', 'madera', 'algodón', 'grano', 
                                  'semilla', 'petroleo', 'gas', 'carbón', 'carbon']
        if any(kw in text_lower for kw in materia_prima_keywords):
            return 'materia_prima'
        
        # Productos tecnológicos
        if any(kw in text_lower for kw in ['computadora', 'laptop', 'smartphone', 'tablet', 
                                            'monitor', 'teclado', 'mouse', 'auriculares', 
                                            'impresora', 'escáner', 'webcam']):
            return 'producto_tecnologico'
        
        # Textiles y vestimenta
        if any(kw in text_lower for kw in ['camiseta', 'camisa', 'pantalón', 'pantalon', 
                                            'zapato', 'zapatilla', 'tenis', 'calzado', 
                                            'vestido', 'falda', 'blusa', 'gorra', 'sombrero']):
            return 'textil_vestimenta'
        
        # Herramientas
        if any(kw in text_lower for kw in ['martillo', 'taladro', 'destornillador', 'sierra', 
                                            'llave', 'alicate', 'tijeras', 'cuchillo', 
                                            'herramienta', 'tool']):
            return 'herramienta'
        
        # Vehículos
        if any(kw in text_lower for kw in ['automóvil', 'automovil', 'carro', 'vehículo', 
                                            'vehiculo', 'moto', 'motocicleta', 'bicicleta', 
                                            'camión', 'camion', 'neumático', 'neumatico']):
            return 'vehiculo'
        
        # Alimentos
        if any(kw in text_lower for kw in ['café', 'cafe', 'chocolate', 'miel', 'cerveza', 
                                            'vino', 'aceite', 'leche', 'queso', 'pan', 
                                            'arroz', 'azúcar', 'azucar', 'harina']):
            return 'alimento'
        
        # Equipos médicos
        if any(kw in text_lower for kw in ['termómetro', 'termometro', 'mascarilla', 'vendaje', 
                                            'jeringa', 'medicina', 'vitamina', 'guante', 
                                            'quirúrgico', 'quirurgico', 'médico', 'medico']):
            return 'equipo_medico'
        
        return 'otros'
    
    def _get_dynamic_weights(self, product_type: str, domain: str) -> Dict[str, float]:
        """
        Calcula pesos dinámicos según el tipo de producto detectado.
        Para materias primas: más peso a similitud léxica y contexto
        Para productos tecnológicos: más peso a similitud semántica
        """
        # Pesos base por defecto
        weights = {
            'semantic': 0.35,
            'lexical': 0.35,
            'category': 0.20,
            'fulltext': 0.10
        }
        
        if product_type == 'materia_prima':
            # Materias primas: énfasis en léxico y contexto (capítulos)
            weights['lexical'] = 0.45
            weights['semantic'] = 0.25
            weights['category'] = 0.20
            weights['fulltext'] = 0.10
        elif product_type == 'producto_tecnologico':
            # Productos tecnológicos: énfasis en semántica
            weights['semantic'] = 0.50
            weights['lexical'] = 0.25
            weights['category'] = 0.15
            weights['fulltext'] = 0.10
        elif product_type == 'textil_vestimenta':
            # Textiles: balanceado con algo más de léxico
            weights['semantic'] = 0.35
            weights['lexical'] = 0.35
            weights['category'] = 0.20
            weights['fulltext'] = 0.10
        elif product_type == 'herramienta' or product_type == 'vehiculo':
            # Herramientas y vehículos: énfasis en contexto
            weights['lexical'] = 0.40
            weights['semantic'] = 0.30
            weights['category'] = 0.20
            weights['fulltext'] = 0.10
        elif product_type == 'alimento':
            # Alimentos: balanceado
            weights['semantic'] = 0.35
            weights['lexical'] = 0.35
            weights['category'] = 0.20
            weights['fulltext'] = 0.10
        elif product_type == 'equipo_medico':
            # Equipos médicos: énfasis en semántica y contexto
            weights['semantic'] = 0.40
            weights['lexical'] = 0.30
            weights['category'] = 0.20
            weights['fulltext'] = 0.10
        
        # Ajuste según dominio si es relevante
        if domain == 'textiles':
            weights['category'] = 0.25
            weights['fulltext'] = 0.10
        elif domain == 'minerales':
            weights['lexical'] = 0.45
            weights['semantic'] = 0.25
        
        return weights


# --- BLOQUE TEMPORAL PARA PRUEBA DE PRECISIÓN MASIVA ---
if __name__ == '__main__':
    """
    Script temporal para probar la precisión del clasificador con 50 productos de prueba.
    Ejecutar con: python -m servicios.classifier
    """
    import sys
    from repos import get_repos
    
    # Productos de prueba
    productos_test = [
        ("Arena de río lavada, grano fino, para construcción", "Arena construcción"),
        ("Computadora portátil de 15 pulgadas con procesador Intel i7, 16GB RAM, 512GB SSD", "Laptop"),
        ("Camiseta de algodón 100%, color blanco, manga corta", "Camiseta algodón"),
        ("Teléfono celular inteligente con pantalla táctil AMOLED de 6.5 pulgadas", "Smartphone"),
        ("Neumático radial para automóvil, medida 205/55R16", "Neumático"),
        ("Batería de plomo-ácido para automóvil, 12V, 60Ah", "Batería auto"),
        ("Café verde sin tostar, sin descafeinar, en sacos de 60 kg", "Café sin tostar"),
        ("Cacao en grano fermentado y seco, de origen colombiano", "Cacao grano"),
        ("Botella plástica PET transparente de 1 litro", "Botella PET"),
        ("Leche entera en polvo, fortificada con vitaminas A y D", "Leche polvo"),
        ("Silla de oficina ergonómica con base metálica y ruedas", "Silla oficina"),
        ("Papel bond tamaño A4, 75 gramos, blanco", "Papel bond"),
        ("Tornillos de acero inoxidable, cabeza hexagonal, 5 mm", "Tornillos acero"),
        ("Tubo de PVC de 2 pulgadas para instalación sanitaria", "Tubo PVC"),
        ("Aceite lubricante para motor diésel SAE 15W40", "Aceite motor"),
        ("Zapatos deportivos de suela de caucho y parte superior textil", "Zapatos deportivos"),
        ("Azúcar blanca refinada en bolsas de 25 kg", "Azúcar refinada"),
        ("Atún enlatado en aceite vegetal, 170 g", "Atún enlatado"),
        ("Ventilador eléctrico de pedestal, 3 velocidades, 50 cm", "Ventilador"),
        ("Refrigerador doméstico de 400 litros, consumo eficiente", "Refrigerador"),
        ("Cemento gris Portland tipo I, saco de 50 kg", "Cemento Portland"),
        ("Pintura acrílica blanca para interiores, 4 litros", "Pintura acrílica"),
        ("Cuchillo de acero inoxidable con mango plástico", "Cuchillo acero"),
        ("Mesa de comedor de madera sólida, 6 puestos", "Mesa madera"),
        ("Lavadora automática de 18 kg, carga superior", "Lavadora"),
        ("Horno microondas de 20 litros, 800W", "Microondas"),
        ("Motor eléctrico trifásico 5HP, 220V", "Motor eléctrico"),
        ("Panel solar fotovoltaico monocristalino, 450W", "Panel solar"),
        ("Cable de cobre aislado, 10 AWG, recubierto de PVC", "Cable cobre"),
        ("Jugo de naranja pasteurizado en botella de vidrio, 1 litro", "Jugo naranja"),
        ("Harina de trigo fortificada, bolsa de 1 kg", "Harina trigo"),
        ("Pantalón de mezclilla (jean) azul, talla 32", "Pantalón jeans"),
        ("Reloj de pulsera digital resistente al agua", "Reloj digital"),
        ("Dispositivo USB de almacenamiento 64GB 3.0", "USB"),
        ("Auriculares inalámbricos con estuche de carga", "Auriculares"),
        ("Cámara fotográfica digital 24 MP con lente intercambiable", "Cámara digital"),
        ("Impresora multifuncional láser, color, conexión WiFi", "Impresora"),
        ("Lámpara LED de escritorio con brazo flexible", "Lámpara LED"),
        ("Botiquín de primeros auxilios con gasas, vendas y alcohol", "Botiquín"),
        ("Guantes quirúrgicos de látex, esterilizados", "Guantes quirúrgicos"),
        ("Tornillo autorroscante galvanizado para madera, 3 cm", "Tornillo autorroscante"),
        ("Detergente líquido para ropa, aroma floral, botella 3 L", "Detergente"),
        ("Perfume en spray, 100 ml, fragancia cítrica", "Perfume"),
        ("Bebida energizante en lata de 250 ml", "Bebida energizante"),
        ("Juguete de plástico educativo para niños mayores de 3 años", "Juguete plástico"),
        ("Ladrillo cerámico hueco para muro estructural", "Ladrillo cerámico"),
        ("Plátano maduro fresco para consumo humano", "Plátano"),
        ("Filete de salmón congelado, empacado al vacío", "Salmón congelado"),
        ("Tubo de acero galvanizado para construcción, 2 metros", "Tubo acero"),
        ("Maleta de viaje con ruedas, material poliéster, 70 litros", "Maleta viaje"),
    ]
    
    print("\n" + "="*100)
    print(" PRUEBA DE PRECISIÓN MASIVA - CLASIFICODE")
    print("="*100 + "\n")
    
    # Inicializar clasificador
    repos = get_repos()
    clasificador = NationalClassifier()
    
    resultados = []
    
    for i, (descripcion, nombre_corto) in enumerate(productos_test, 1):
        print(f"\n[{i}/50] {nombre_corto}")
        print(f"Descripción: {descripcion}")
        
        try:
            # Crear caso temporal (no se guarda en BD)
            caso = {
                'id': i,
                'product_title': nombre_corto,
                'product_desc': descripcion,
                'attrs_json': '{}'
            }
            
            # Clasificar
            resultado = clasificador.classify(caso)
            
            hs = resultado.get('national_code', 'N/A')
            confianza = 0.95 if resultado.get('national_code') else 0.7
            rationale = resultado.get('rationale', 'N/A')
            
            # Si rationale es dict, extraer texto
            if isinstance(rationale, dict):
                factores = rationale.get('factores_clave', [])
                descartes = rationale.get('descartes', [])
                rationale_str = f"RGI: {', '.join(resultado.get('rgi_applied', []))}"
                if factores:
                    rationale_str += f" | Factores: {', '.join(factores[:3])}"
                if descartes:
                    rationale_str += f" | Descartes: {', '.join(descartes[:2])}"
            else:
                rationale_str = str(rationale)[:100]
            
            print(f"Código HS: {hs}")
            print(f"Confianza: {confianza*100:.1f}%")
            print(f"Rationale: {rationale_str}")
            print("-" * 100)
            
            resultados.append({
                'numero': i,
                'nombre': nombre_corto,
                'descripcion': descripcion,
                'hs': hs,
                'confianza': confianza,
                'rationale': rationale_str,
                'exito': hs != 'N/A' and hs != ''
            })
            
        except Exception as e:
            print(f"ERROR: {str(e)}")
            print("-" * 100)
            resultados.append({
                'numero': i,
                'nombre': nombre_corto,
                'descripcion': descripcion,
                'hs': 'ERROR',
                'confianza': 0.0,
                'rationale': str(e),
                'exito': False
            })
    
    # Resumen final
    total = len(resultados)
    exitosos = sum(1 for r in resultados if r['exito'])
    porcentaje = (exitosos / total * 100) if total > 0 else 0
    
    print("\n" + "="*100)
    print(" RESUMEN DE PRUEBAS")
    print("="*100)
    print(f"Total de productos: {total}")
    print(f"Clasificaciones exitosas: {exitosos}")
    print(f"Clasificaciones fallidas: {total - exitosos}")
    print(f"Precisión: {porcentaje:.1f}%")
    print("="*100)
    
    # Detalle de fallos
    fallos = [r for r in resultados if not r['exito']]
    if fallos:
        print("\nFALLOS DETECTADOS:")
        for fallo in fallos:
            print(f"  - [{fallo['numero']}] {fallo['nombre']}: {fallo['rationale']}")
    
    print("\n")
