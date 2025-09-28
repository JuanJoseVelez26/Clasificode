import re
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

class NLPService:
    """Servicio de Procesamiento de Lenguaje Natural"""
    
    def __init__(self):
        self.spacy_model = None
        self._load_spacy_model()
        
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
