import re
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

class NLPService:
    """Servicio de Procesamiento de Lenguaje Natural"""
    
    def __init__(self):
        self.spacy_model = None
        self._load_spacy_model()
        
        # Stopwords comerciales de marketing (NO eliminar)
        self.stopwords_comerciales = {
            'premium', 'ofert', 'nuevo', 'original', 'genuino', 'autentico', 'certificado',
            'garantia', 'envio', 'envío', 'gratis', 'free', 'shipping', 'delivery',
            'disponible', 'stock', 'venta', 'compra', 'precio', 'marca', 'brand', 'modelo',
            'model', 'serie', 'version', 'ref', 'referencia', 'code', 'codigo', 'sku',
            'item', 'caja', 'pack', 'paquete', 'kit', 'set', 'manual', 'instrucciones',
            'guia', 'accesorio', 'color', 'tamaño', 'talla', 'unidad', 'pieza', 'par',
            'docena', 'envase', 'empaque', 'bolsa', 'frasco', 'contenido', 'neto',
            'bruto', 'peso', 'volumen', 'capacidad', 'litros', 'gramos', 'hecho',
            'fabricado', 'manufacturado', 'producido', 'importado', 'exportado',
            'alta calidad', 'super', 'plus', 'ultra', 'max', 'pro', 'expert', 'deluxe',
            'edicion limitada', 'especial', 'edicion especial', 'coleccion', 'collection',
            '2024', '2023', '2025', 'RGB', 'gamer', 'extreme', 'performance', 'speed',
            'turbo', 'advanced', 'elite', 'master', 'legend', 'champion'
        }
        
        # Palabras clave técnicas que SÍ afectan arancel
        self.terminos_tecnicos_relevantes = {
            'inalambrico', 'inalámbrico', 'wireless', 'bluetooth', 'usb', 'hdmi', 'vga',
            'displayport', 'thunderbolt', 'ethernet', 'wifi', 'wlan', 'nfc', 'gps',
            'reutilizable', 'desechable', 'recargable', 'extraible', 'desmontable',
            'quirurgico', 'quirúrgico', 'quirurgico', 'esteril', 'esterilizado',
            'acero inoxidable', 'inoxidable', 'aluminio', 'titanio', 'fibra carbono',
            'vivo', 'vivos', 'animal', 'animales', 'bovino', 'porcino', 'pollos',
            'pescado', 'marisco', 'crustaceo', 'molusco', 'para bovino', 'para equino',
            'para porcino', 'para aves', 'uso medico', 'uso médico', 'uso veterinario',
            'profesional', 'industrial', 'comercial', 'domestico', 'doméstico'
        }
        
        # Categorías de clasificación
        self.categories = {
            'electronics': ['computadora', 'telefono', 'celular', 'laptop', 'tablet', 'smartphone', 'electronic', 'digital'],
            'textiles': ['ropa', 'tela', 'textil', 'vestido', 'camisa', 'pantalon', 'zapatos', 'calzado'],
            'food': ['alimento', 'comida', 'fruta', 'verdura', 'carne', 'pescado', 'cereal', 'bebida'],
            'machinery': ['maquina', 'equipo', 'herramienta', 'motor', 'bomba', 'compresor', 'turbina'],
            'chemicals': ['quimico', 'acido', 'base', 'solvente', 'polimero', 'resina', 'adhesivo']
        }
        
        # Palabras de sentimiento
        self.sentiment_words = {
            'positive': ['excelente', 'bueno', 'calidad', 'premium', 'superior', 'mejor', 'optimizado'],
            'negative': ['defectuoso', 'malo', 'pobre', 'inferior', 'dañado', 'roto', 'usado'],
            'neutral': ['estandar', 'normal', 'regular', 'basico', 'comun', 'tipico']
        }
        
        # Entidades comunes en comercio
        self.entity_patterns = {
            'material': r'\b(acero|aluminio|plastico|madera|vidrio|ceramica|textil|cuero)\b',
            'brand': r'\b(apple|samsung|sony|nike|adidas|ford|toyota|bmw)\b',
            'measurement': r'\b(\d+(?:\.\d+)?)\s*(kg|g|m|cm|mm|l|ml|unidad|pieza)\b',
            'country': r'\b(china|usa|alemania|japon|mexico|brasil|argentina|colombia)\b'
        }
    
    def _load_spacy_model(self):
        """Cargar modelo de spaCy para español (fallback silencioso)"""
        try:
            import spacy
            # Intentar cargar modelo español
            try:
                self.spacy_model = spacy.load("es_core_news_sm")
            except OSError:
                # Si no está instalado, intentar con modelo básico
                try:
                    self.spacy_model = spacy.load("es_core_web_sm")
                except OSError:
                    # Fallback: usar modelo en inglés
                    self.spacy_model = spacy.load("en_core_web_sm")
        except ImportError:
            # spaCy no está instalado, usar procesamiento básico
            self.spacy_model = None
    
    def normalize(self, text: str) -> str:
        """Normalizar texto: lowercase, espacios, limpieza básica"""
        if not text:
            return ""
        
        # Convertir a minúsculas
        normalized = text.lower()
        
        # Remover caracteres especiales pero mantener espacios
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        
        # Normalizar espacios múltiples
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remover espacios al inicio y final
        normalized = normalized.strip()
        
        return normalized
    
    def lemmatize(self, text: str) -> str:
        """Lematizar texto usando spaCy (fallback silencioso)"""
        if not self.spacy_model:
            return text
        
        try:
            doc = self.spacy_model(text)
            lemmas = [token.lemma_ for token in doc if not token.is_stop and not token.is_punct]
            return ' '.join(lemmas)
        except Exception:
            # Fallback silencioso: retornar texto original
            return text
    
    def preprocess_text(self, text: str) -> str:
        """Preprocesar texto completo: normalizar + lematizar"""
        normalized = self.normalize(text)
        lemmatized = self.lemmatize(normalized)
        return lemmatized
    
    def _remove_commercial_stopwords(self, text: str) -> str:
        """Eliminar stopwords comerciales manteniendo términos técnicos relevantes"""
        if not text:
            return text
        
        words = text.lower().split()
        filtered_words = []
        
        for word in words:
            # Verificar si es stopword comercial
            is_stopword = any(stopword in word for stopword in self.stopwords_comerciales)
            # Verificar si es término técnico relevante
            is_technical = any(term in word for term in self.terminos_tecnicos_relevantes)
            
            # Mantener si es técnico o si no es stopword
            if is_technical or not is_stopword:
                filtered_words.append(word)
        
        return ' '.join(filtered_words)
    
    def preprocess_for_classification(self, text: str) -> str:
        """Preprocesamiento avanzado para clasificación: normalizar + remover stopwords comerciales"""
        if not text:
            return ""
        
        # Paso 1: Normalizar
        normalized = self.normalize(text)
        
        # Paso 2: Remover stopwords comerciales
        cleaned = self._remove_commercial_stopwords(normalized)
        
        # Paso 3: Lematizar si tenemos spaCy
        if self.spacy_model:
            try:
                cleaned = self.lemmatize(cleaned)
            except:
                pass
        
        return cleaned
    
    def extract_classification_features(self, text: str) -> Dict[str, Any]:
        """Extraer características para clasificación arancelaria"""
        if not text:
            return {}
        
        text_lower = text.lower()
        features = {}
        
        # Bandera: es parte/accesorio vs producto completo
        partes_keywords = ['parte', 'partes', 'repuesto', 'repuestos', 'accesorio', 'accesorios',
                          'pieza', 'piezas', 'componente', 'componentes', 'recambio']
        equipo_completo_keywords = ['equipo', 'maquina', 'dispositivo', 'aparato', 'producto',
                                   'sistema', 'unidad', 'herramienta', 'instrumento']
        
        has_partes = any(keyword in text_lower for keyword in partes_keywords)
        has_equipo = any(keyword in text_lower for keyword in equipo_completo_keywords)
        
        # Si menciona "parte" pero NO menciona que es un equipo completo, probablemente es parte
        if has_partes and not has_equipo:
            features['es_parte'] = True
            features['es_equipo_completo'] = False
        elif has_equipo and not has_partes:
            features['es_equipo_completo'] = True
            features['es_parte'] = False
        else:
            features['es_parte'] = False
            features['es_equipo_completo'] = False
        
        # Bandera: uso médico
        uso_medico_keywords = ['medico', 'médico', 'hospital', 'clinico', 'quirurgico', 'quirúrgico',
                              'quirurgico', 'esteril', 'esterilizado', 'uso medico', 'uso médico',
                              'para hospital', 'para clinica', 'para clínica', 'veterinario',
                              'terapeutico', 'terapéutico', 'diagnostico', 'diagnóstico']
        features['uso_medico'] = any(keyword in text_lower for keyword in uso_medico_keywords)
        
        # Bandera: animal vivo
        animal_vivo_keywords = ['vivo', 'vivos', 'animal', 'animales', 'bovino', 'porcino', 'pollos',
                               'ternero', 'terneros', 'vaca', 'ganado', 'equino', 'cerdo', 'pollo']
        features['uso_animal_vivo'] = any(keyword in text_lower for keyword in animal_vivo_keywords)
        
        # Bandera: inalámbrico
        inalambrico_keywords = ['inalambrico', 'inalámbrico', 'wireless', 'bluetooth', 'wifi', 'wlan']
        features['inalambrico'] = any(keyword in text_lower for keyword in inalambrico_keywords)
        
        # Bandera: reutilizable/desechable
        reutilizable_keywords = ['reutilizable', 'recargable', 'lavable', 'rehusable']
        desechable_keywords = ['desechable', 'unico uso', 'único uso', 'usa y tira']
        features['es_reutilizable'] = any(keyword in text_lower for keyword in reutilizable_keywords)
        features['es_desechable'] = any(keyword in text_lower for keyword in desechable_keywords)
        
        # Bandera: material específico
        materiales = []
        material_keywords = {
            'acero': ['acero', 'steel'],
            'aluminio': ['aluminio', 'aluminum'],
            'plastico': ['plastico', 'plástico', 'plastic', 'polimero', 'polímero'],
            'madera': ['madera', 'wood'],
            'cuero': ['cuero', 'leather', 'piel'],
            'algodon': ['algodon', 'algodón', 'cotton'],
            'vacio': ['vacio', 'vacío', 'vacuum'],
            'inoxidable': ['inoxidable', 'stainless']
        }
        
        for material, keywords in material_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                materiales.append(material)
        
        if materiales:
            features['materiales'] = materiales
        
        # Bandera: uso/género específico
        usage_keywords = {
            'infantil': ['infantil', 'niño', 'niña', 'bebe', 'bebé', 'baby', 'kids'],
            'deportivo': ['deportivo', 'sport', 'atletico', 'atlético', 'fitness'],
            'profesional': ['profesional', 'professional', 'comercial', 'industrial']
        }
        
        for usage, keywords in usage_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                features['uso'] = usage
                break
        
        # --- MEJORA CLASIFICACIÓN HS CONTEXTUAL ---
        # Extraer características de clasificación arancelaria (razonamiento humano aduanero)
        self._extract_contextual_features(text_lower, features)
        # --- FIN MEJORA CLASIFICACIÓN HS CONTEXTUAL ---
        
        return features
    
    def _extract_contextual_features(self, text_lower: str, features: Dict[str, Any]) -> None:
        """
        --- MEJORA CLASIFICACIÓN HS CONTEXTUAL ---
        Extraer banderas contextuales que replican razonamiento humano aduanero:
        - tipo_de_bien: materia_prima, producto_terminado, accesorio_repuesto
        - uso_principal: computo, construccion, alimentario, vestimenta, agropecuario, medico, otro
        - nivel_procesamiento: crudo, semiprocesado, terminado
        """
        
        # 1. Determinar tipo_de_bien
        materia_prima_keywords = [
            'arena', 'piedra', 'caliza', 'yeso', 'cemento', 'arcilla', 'grava',
            'grano', 'semilla', 'cereal', 'cafe', 'café', 'verde', 'sin tostar',
            'sin descafeinar', 'crudo', 'natural', 'sin procesar', 'piedra natural'
        ]
        producto_terminado_keywords = [
            'laptop', 'computadora', 'portatil', 'portátil', 'notebook', 'pc',
            'procesador', 'ram', 'ssd', 'hdd', 'pantalla', 'monitor', 'pantalla integrada',
            'sistema completo', 'equipo completo', 'maquina completa', 'dispositivo completo',
            'producto terminado', 'listo para usar', 'listo para consumir'
        ]
        accesorio_repuesto_keywords = [
            'parte de', 'partes de', 'accesorio para', 'repuesto', 'recambio', 
            'componente', 'pieza', 'carcasa', 'bateria', 'batería', 'cargador',
            'cable', 'adaptador', 'funda', 'case', 'protector', 'tapa', 'fundas',
            'carcasa para', 'batería para', 'cargador para', 'pieza de repuesto'
        ]
        
        has_materia_prima = any(keyword in text_lower for keyword in materia_prima_keywords)
        has_producto_terminado = any(keyword in text_lower for keyword in producto_terminado_keywords)
        has_accesorio_repuesto = any(keyword in text_lower for keyword in accesorio_repuesto_keywords)
        
        if has_accesorio_repuesto and not has_producto_terminado:
            features['tipo_de_bien'] = 'accesorio_repuesto'
        elif has_materia_prima and not has_producto_terminado:
            features['tipo_de_bien'] = 'materia_prima'
        elif has_producto_terminado:
            features['tipo_de_bien'] = 'producto_terminado'
        else:
            # Default: intentar inferir por contexto
            if features.get('es_equipo_completo'):
                features['tipo_de_bien'] = 'producto_terminado'
            elif features.get('es_parte'):
                features['tipo_de_bien'] = 'accesorio_repuesto'
            else:
                features['tipo_de_bien'] = 'producto_terminado'  # Default conservador
        
        # 2. Determinar uso_principal
        computo_keywords = [
            'computadora', 'laptop', 'portatil', 'portátil', 'notebook', 'pc', 'desktop',
            'procesador', 'cpu', 'gpu', 'ram', 'memoria', 'ssd', 'hard disk', 'disco duro',
            'monitor', 'pantalla', 'teclado', 'mouse', 'raton', 'impresora', 'escanner',
            'tablet', 'celular', 'smartphone', 'telefono movil', 'digital'
        ]
        construccion_keywords = [
            'arena', 'piedra', 'roca', 'caliza', 'yeso', 'cemento', 'hormigon', 'concreto',
            'arcilla', 'ladrillo', 'teja', 'azulejo', 'ceramica', 'vidrio plano', 'ventana',
            'mortero', 'cal', 'grava', 'piedra triturada', 'para construccion', 'para construcción'
        ]
        alimentario_keywords = [
            'alimento', 'comida', 'fruta', 'verdura', 'carne', 'pescado', 'cereal',
            'grano', 'cafe', 'café', 'te', 'té', 'bebida', 'jugo', 'lacteo', 'lácteo',
            'leche', 'queso', 'mantequilla', 'aceite', 'azucar', 'azúcar', 'sal',
            'arroz', 'trigo', 'maiz', 'maíz', 'avena', 'consumo humano', 'para consumo'
        ]
        vestimenta_keywords = [
            'ropa', 'vestido', 'camisa', 'pantalon', 'pantalón', 'chaqueta', 'abrigo',
            'zapatos', 'zapato', 'calzado', 'botas', 'zapatilla', 'medias', 'calcetines',
            'gorra', 'sombrero', 'guantes', 'bufanda', 'tela', 'textil', 'algodon', 'algodón',
            'poliester', 'nylon', 'lana', 'seda', 'cuero'
        ]
        agropecuario_keywords = [
            'vivo', 'vivos', 'animal', 'animales', 'ternero', 'terneros', 'ganado', 'bovino',
            'porcino', 'cerdo', 'equino', 'caballo', 'oveja', 'pollos', 'pollo', 'gallina',
            'ave', 'pescado vivo', 'marisco', 'semilla', 'planta', 'arbol', 'árbol',
            'vaca', 'caballo', 'para ganado', 'para bovino', 'para porcino'
        ]
        medico_keywords = [
            'medico', 'médico', 'hospital', 'clinico', 'clínico', 'quirurgico', 'quirúrgico',
            'esteril', 'esterilizado', 'quirurgico', 'veterinario', 'terapeutico', 'terapéutico',
            'diagnostico', 'diagnóstico', 'uso medico', 'uso médico', 'hospitalario'
        ]
        
        if any(keyword in text_lower for keyword in computo_keywords):
            features['uso_principal'] = 'computo'
        elif any(keyword in text_lower for keyword in construccion_keywords):
            features['uso_principal'] = 'construccion'
        elif any(keyword in text_lower for keyword in alimentario_keywords):
            features['uso_principal'] = 'alimentario'
        elif any(keyword in text_lower for keyword in vestimenta_keywords):
            features['uso_principal'] = 'vestimenta'
        elif any(keyword in text_lower for keyword in agropecuario_keywords):
            features['uso_principal'] = 'agropecuario'
        elif any(keyword in text_lower for keyword in medico_keywords):
            features['uso_principal'] = 'medico'
        else:
            features['uso_principal'] = 'otro'
        
        # 3. Determinar nivel_procesamiento
        crudo_keywords = [
            'crudo', 'natural', 'sin procesar', 'sin tostar', 'sin descafeinar',
            'sin refinar', 'sin elaborar', 'bruto', 'raw', 'green', 'verde',
            'sin cocer', 'sin cocinar'
        ]
        terminado_keywords = [
            'terminado', 'completo', 'listo para usar', 'listo para consumir',
            'listo para vender', 'final', 'elaborado', 'procesado', 'manufacturado',
            'fabricado', 'ensamblado', 'armado', 'montado', 'cocinado', 'tostado',
            'refinado', 'empacado', 'envasado'
        ]
        
        if any(keyword in text_lower for keyword in crudo_keywords):
            features['nivel_procesamiento'] = 'crudo'
        elif any(keyword in text_lower for keyword in terminado_keywords):
            features['nivel_procesamiento'] = 'terminado'
        elif features['tipo_de_bien'] == 'materia_prima':
            features['nivel_procesamiento'] = 'crudo'
        elif features['tipo_de_bien'] == 'producto_terminado':
            features['nivel_procesamiento'] = 'terminado'
        else:
            features['nivel_procesamiento'] = 'semiprocesado'
    
    def classify_text(self, text: str) -> Dict[str, Any]:
        """Clasificar texto en categorías predefinidas"""
        if not text:
            return {'category': 'unknown', 'confidence': 0.0, 'keywords': []}
        
        # Preprocesar texto
        processed_text = self.preprocess_text(text)
        words = processed_text.split()
        
        # Contar ocurrencias por categoría
        category_scores = {}
        matched_keywords = {}
        
        for category, keywords in self.categories.items():
            score = 0
            matched = []
            
            for keyword in keywords:
                if keyword in processed_text:
                    score += 1
                    matched.append(keyword)
            
            category_scores[category] = score
            matched_keywords[category] = matched
        
        # Determinar categoría principal
        if category_scores:
            best_category = max(category_scores, key=category_scores.get)
            max_score = category_scores[best_category]
            
            # Calcular confianza basada en palabras coincidentes
            total_words = len(words)
            confidence = min(max_score / max(total_words, 1), 1.0)
            
            return {
                'category': best_category if max_score > 0 else 'unknown',
                'confidence': confidence,
                'keywords': matched_keywords[best_category],
                'all_scores': category_scores
            }
        
        return {'category': 'unknown', 'confidence': 0.0, 'keywords': []}
    
    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analizar sentimiento del texto"""
        if not text:
            return {'sentiment': 'neutral', 'score': 0.0, 'words': []}
        
        processed_text = self.preprocess_text(text)
        words = processed_text.split()
        
        sentiment_scores = {'positive': 0, 'negative': 0, 'neutral': 0}
        sentiment_words = {'positive': [], 'negative': [], 'neutral': []}
        
        for word in words:
            for sentiment, sentiment_word_list in self.sentiment_words.items():
                if word in sentiment_word_list:
                    sentiment_scores[sentiment] += 1
                    sentiment_words[sentiment].append(word)
        
        # Determinar sentimiento dominante
        if sentiment_scores['positive'] > sentiment_scores['negative']:
            dominant_sentiment = 'positive'
        elif sentiment_scores['negative'] > sentiment_scores['positive']:
            dominant_sentiment = 'negative'
        else:
            dominant_sentiment = 'neutral'
        
        # Calcular score de sentimiento
        total_sentiment_words = sum(sentiment_scores.values())
        if total_sentiment_words > 0:
            score = sentiment_scores[dominant_sentiment] / total_sentiment_words
        else:
            score = 0.0
        
        return {
            'sentiment': dominant_sentiment,
            'score': score,
            'words': sentiment_words[dominant_sentiment],
            'all_scores': sentiment_scores
        }
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extraer entidades del texto"""
        if not text:
            return {}
        
        entities = {}
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, text.lower())
            if matches:
                entities[entity_type] = list(set(matches))
        
        # Extraer números y medidas
        measurements = re.findall(r'\b(\d+(?:\.\d+)?)\s*(kg|g|m|cm|mm|l|ml|unidad|pieza)\b', text.lower())
        if measurements:
            entities['measurements'] = [f"{value} {unit}" for value, unit in measurements]
        
        # Extraer códigos HS (patrón básico)
        hs_codes = re.findall(r'\b\d{2,4}\.\d{2}\.\d{2}\b', text)
        if hs_codes:
            entities['hs_codes'] = hs_codes
        
        return entities
    
    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extraer palabras clave del texto"""
        if not text:
            return []
        
        processed_text = self.preprocess_text(text)
        words = processed_text.split()
        
        # Filtrar palabras muy cortas y comunes
        stop_words = {'el', 'la', 'de', 'del', 'y', 'o', 'a', 'en', 'un', 'una', 'es', 'son', 'para', 'con', 'por', 'se', 'su', 'que', 'como', 'mas', 'muy', 'este', 'esta', 'estos', 'estas', 'pero', 'si', 'no', 'al', 'lo', 'le', 'les', 'me', 'mi', 'tu', 'te', 'nos', 'nuestro', 'nuestra'}
        
        # Contar frecuencia de palabras
        word_freq = {}
        for word in words:
            if len(word) > 2 and word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Ordenar por frecuencia y retornar top keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        keywords = [word for word, freq in sorted_words[:max_keywords]]
        
        return keywords
    
    def extract_technical_terms(self, text: str) -> List[str]:
        """Extraer términos técnicos específicos"""
        if not text:
            return []
        
        # Patrones para términos técnicos
        technical_patterns = [
            r'\b\d{2,4}\.\d{2}\.\d{2}\b',  # Códigos HS
            r'\b[A-Z]{2,4}\d{2,4}\b',      # Códigos de producto
            r'\b\d+(?:\.\d+)?\s*(?:mm|cm|m|kg|g|l|ml)\b',  # Medidas
            r'\b(?:acero|aluminio|plastico|madera|vidrio|ceramica|textil|cuero)\b',  # Materiales
            r'\b(?:motor|bomba|compresor|turbina|generador|transformador)\b',  # Maquinaria
            r'\b(?:acido|base|solvente|polimero|resina|adhesivo)\b'  # Químicos
        ]
        
        technical_terms = []
        for pattern in technical_patterns:
            matches = re.findall(pattern, text.lower())
            technical_terms.extend(matches)
        
        return list(set(technical_terms))
    
    def calculate_text_complexity(self, text: str) -> Dict[str, Any]:
        """Calcular complejidad del texto"""
        if not text:
            return {'complexity': 'low', 'score': 0.0, 'metrics': {}}
        
        words = text.split()
        sentences = re.split(r'[.!?]+', text)
        
        # Métricas básicas
        word_count = len(words)
        sentence_count = len([s for s in sentences if s.strip()])
        avg_sentence_length = word_count / max(sentence_count, 1)
        
        # Palabras únicas
        unique_words = len(set(words))
        lexical_diversity = unique_words / max(word_count, 1)
        
        # Palabras largas (>6 caracteres)
        long_words = len([w for w in words if len(w) > 6])
        long_word_ratio = long_words / max(word_count, 1)
        
        # Calcular score de complejidad
        complexity_score = (avg_sentence_length * 0.4 + 
                          lexical_diversity * 0.3 + 
                          long_word_ratio * 0.3)
        
        # Clasificar complejidad
        if complexity_score < 0.3:
            complexity = 'low'
        elif complexity_score < 0.6:
            complexity = 'medium'
        else:
            complexity = 'high'
        
        return {
            'complexity': complexity,
            'score': complexity_score,
            'metrics': {
                'word_count': word_count,
                'sentence_count': sentence_count,
                'avg_sentence_length': avg_sentence_length,
                'lexical_diversity': lexical_diversity,
                'long_word_ratio': long_word_ratio
            }
        }
    
    def get_text_summary(self, text: str) -> Dict[str, Any]:
        """Obtener resumen completo del análisis de texto"""
        if not text:
            return {'error': 'Texto vacío'}
        
        return {
            'original_text': text,
            'normalized_text': self.normalize(text),
            'preprocessed_text': self.preprocess_text(text),
            'classification': self.classify_text(text),
            'sentiment': self.analyze_sentiment(text),
            'entities': self.extract_entities(text),
            'keywords': self.extract_keywords(text),
            'technical_terms': self.extract_technical_terms(text),
            'complexity': self.calculate_text_complexity(text),
            'analysis_timestamp': datetime.now().isoformat()
        }
