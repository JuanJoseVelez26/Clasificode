from typing import Dict, Any, List
import json
import numpy as np
from rapidfuzz import fuzz
import unicodedata
import os
from datetime import datetime
import logging
from sqlalchemy import text

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
            "8471300000",  # Máquinas automáticas para procesamiento de datos
            "1905000000",  # Pan y productos de panadería
            "0901110000",  # Café sin tostar
            "7001000000",  # Vidrio en bruto
            "7207110000",  # Hierro o acero sin alear
            "8711100000",  # Motocicletas
            "2201100000"   # Agua mineral
        ]
        
        # Reglas específicas para productos comunes
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
            'automovil': {'hs6': '870323', 'national_code': '8703230000', 'title': 'Automóviles de cilindrada entre 1000 y 1500 cm³'},
            'carro': {'hs6': '870323', 'national_code': '8703230000', 'title': 'Automóviles de cilindrada entre 1000 y 1500 cm³'},
            'moto': {'hs6': '871110', 'national_code': '8711100000', 'title': 'Motocicletas con motor de cilindrada no superior a 50 cm³'},
            'motocicleta': {'hs6': '871110', 'national_code': '8711100000', 'title': 'Motocicletas con motor de cilindrada no superior a 50 cm³'},
            'bicicleta': {'hs6': '871200', 'national_code': '8712000000', 'title': 'Bicicletas'},
            'medicamento': {'hs6': '300490', 'national_code': '3004900000', 'title': 'Medicamentos'},
            'vacuna': {'hs6': '300220', 'national_code': '3002200000', 'title': 'Vacunas'},
            'libro': {'hs6': '490199', 'national_code': '4901990000', 'title': 'Libros impresos'},
            'papel': {'hs6': '480100', 'national_code': '4801000000', 'title': 'Papel para periódicos'},
            'madera': {'hs6': '440710', 'national_code': '4407100000', 'title': 'Madera aserrada de coníferas'},
            'hierro': {'hs6': '720711', 'national_code': '7207110000', 'title': 'Hierro o acero sin alear'},
            'acero': {'hs6': '720711', 'national_code': '7207110000', 'title': 'Hierro o acero sin alear'},
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
            # Extraer texto del caso
            text = case.get('product_desc', '') or case.get('product_title', '')
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
                hs6 = self._fallback_hs6(text_processed if text_processed else text)
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
            
            # Seleccionar candidato usando pipeline mejorado
            chosen = self._select_best_candidate(text_processed, options, features, attrs)
            
            if not chosen:
                return self._create_error_result(
                    case['id'], 
                    "No se pudo seleccionar candidato",
                    start_time,
                    hs6=hs6,
                    trace=trace,
                    features=features
                )

            national_code = str(chosen.get('national_code', '')).strip()
            title = chosen.get('title') or chosen.get('description') or ''

            # Calcular scores combinados para confianza real
            score_semantic = chosen.get('semantic_score', 0.0)
            score_lexical = chosen.get('lexical_score', 0.0)
            score_contextual = self._calculate_contextual_score(national_code, features)
            
            # Score total ponderado
            score_total = (
                0.6 * score_semantic +
                0.3 * score_lexical +
                0.1 * score_contextual
            )
            
            # Confianza real basada en score total
            confidence = float(max(0.0, min(1.0, score_total)))
            
            # Aplicar validación de consistencia
            validation_result = self._validate_classification_consistency(
                features, national_code or hs6 or '', title
            )
            
            # Ajustar confianza basada en validación
            validation_penalty = 0.2 * (1.0 - validation_result['validation_score'])
            final_confidence = max(0.0, confidence - validation_penalty)
            
            # NUEVAS VALIDACIONES: Verificar coherencia de capítulo y códigos sospechosos
            chapter_coherence = self._chapter_coherence_check(national_code, features, text_processed)
            is_suspect = self._is_suspect_code(national_code)
            requires_review = False
            
            # MEJORA DE COBERTURA AUTOMÁTICA: Elevar confianza para casos coherentes y no sospechosos
            if chapter_coherence and not is_suspect and score_total >= 0.65:
                final_confidence = min(0.75, round(score_total, 2))
                requires_review = False
                logging.info(f"Caso {case['id']}: Cobertura automática aplicada - confianza elevada a {final_confidence}")
            
            # Si hay incoherencia de capítulo, forzar baja confianza
            elif not chapter_coherence:
                final_confidence = 0.0
                requires_review = True
                logging.warning(f"Caso {case['id']}: Incoherencia detectada, confianza forzada a 0.0")
            # Si es código sospechoso, aplicar controles estrictos
            elif is_suspect:
                # Solo aceptar alta confianza si hay coherencia Y diferencia clara con siguiente candidato
                if final_confidence <= 0.75 or not chapter_coherence:
                    final_confidence = 0.4
                    requires_review = True
                    logging.warning(f"Caso {case['id']}: Código sospechoso {national_code}, confianza reducida a 0.4")
                # Si hay diferencia clara, mantener alta confianza
                elif chapter_coherence:
                    # Verificar si hay diferencia suficiente con el segundo mejor candidato
                    if len(options) > 1:
                        second_best_score = options[1].get('semantic_score', 0.0)
                        second_best_lexical = options[1].get('lexical_score', 0.0)
                        second_best_total = 0.6 * second_best_score + 0.3 * second_best_lexical
                        
                        if score_total - second_best_total < 0.15:
                            final_confidence = 0.4
                            requires_review = True
                            logging.warning(f"Caso {case['id']}: Código sospechoso con diferencia insuficiente, confianza reducida a 0.4")
            
            # Guardar candidato
            self._save_candidate(case['id'], national_code, hs6, title, final_confidence, trace, validation_result, features)
            
            # Registrar métricas (incluyendo requires_review)
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            self._record_metrics(case['id'], final_confidence, response_time, validation_result['validation_score'], requires_review=requires_review)
            
            # Registrar para validación incremental
            self._record_incremental_validation(case['id'], start_time, end_time, final_confidence, national_code, validation_result, features, 'rgi')
            
            # Feedback automático para baja confianza o casos sospechosos
            if final_confidence < 0.6 or requires_review:
                comment = 'baja confianza' if final_confidence < 0.6 else 'clasificación sospechosa (alta similitud pero incoherente)'
                self._register_automatic_feedback(case['id'], national_code, final_confidence, comment)
            
            # Construir rationale detallado (incluyendo nuevas validaciones)
            rationale = self._build_detailed_rationale(features, trace, chosen, validation_result, chapter_coherence, is_suspect, requires_review)

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
                'topK': self._get_top_candidates(options, text_processed, features)
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
            'material_principal': 'no_especificado'
        }
        
        text_lower = text.lower()
        
        # Detectar tipo de bien
        if any(word in text_lower for word in ['parte', 'componente', 'repuesto', 'accesorio']):
            features['tipo_de_bien'] = 'parte_componente'
        elif any(word in text_lower for word in ['materia prima', 'insumo', 'material']):
            features['tipo_de_bien'] = 'materia_prima'
        
        # Detectar uso principal
        if any(word in text_lower for word in ['construccion', 'obra', 'edificacion', 'cemento', 'arena', 'ladrillo']):
            features['uso_principal'] = 'construccion'
        elif any(word in text_lower for word in ['alimentacion', 'comida', 'bebida', 'leche']) and not any(word in text_lower for word in ['color', 'café como', 'cafe como']):
            features['uso_principal'] = 'alimentacion'
        elif any(word in text_lower for word in ['computo', 'informatica', 'electronico', 'digital']):
            features['uso_principal'] = 'computo'
        elif any(word in text_lower for word in ['textil', 'ropa', 'vestido', 'tela']):
            features['uso_principal'] = 'textil'
        elif any(word in text_lower for word in ['automotriz', 'vehiculo', 'carro', 'moto', 'motor', 'diesel', 'gasolina']):
            features['uso_principal'] = 'automotriz'
        elif any(word in text_lower for word in ['calzado', 'zapato', 'zapatos']):
            features['uso_principal'] = 'calzado'
        elif any(word in text_lower for word in ['panel solar', 'placa solar', 'celula fotovoltaica']):
            features['uso_principal'] = 'electricidad'
        elif any(word in text_lower for word in ['ferreteria', 'herramienta', 'herramientas', 'pala']):
            features['uso_principal'] = 'ferreteria'
        
        # Detectar material principal
        if any(word in text_lower for word in ['metal', 'acero', 'hierro', 'aluminio']):
            features['material_principal'] = 'metal'
        elif any(word in text_lower for word in ['plastico', 'polietileno', 'pvc']):
            features['material_principal'] = 'plastico'
        elif any(word in text_lower for word in ['madera', 'pino', 'roble']):
            features['material_principal'] = 'madera'
        elif any(word in text_lower for word in ['vidrio', 'cristal']):
            features['material_principal'] = 'vidrio'
        elif any(word in text_lower for word in ['ceramica', 'porcelana']):
            features['material_principal'] = 'ceramica'
        
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
        
        # Feedback automático si requiere revisión
        if requires_review:
            comment = 'clasificación sospechosa (regla específica con incoherencia)'
            self._register_automatic_feedback(case['id'], national_code, final_confidence, comment)
        
        # Construir rationale (incluyendo nuevas validaciones)
        rationale = self._build_detailed_rationale(features, trace, result, validation_result, chapter_coherence, is_suspect, requires_review)

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

    def _fallback_hs6(self, text: str) -> str:
        """Fallback para determinar HS6 usando embeddings."""
        try:
            # Generar embedding del texto
            embedding = self.embed.generate_embedding(text)
            
            # Buscar HS6 más similar usando embeddings
            # Por simplicidad, retornamos un HS6 genérico
            return '847130'  # Máquinas automáticas para procesamiento de datos
            
        except Exception as e:
            logging.warning(f"Error en fallback HS6: {str(e)}")
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
    
    def _select_best_candidate(self, text: str, options: List[Dict[str, Any]], features: Dict[str, Any], attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Selecciona el mejor candidato usando scores combinados."""
        if not options:
            return None
        
        best_candidate = None
        best_score = -1
        
        for option in options:
            # Calcular score contextual
            contextual_score = self._calculate_contextual_score(option.get('national_code', ''), features)
            
            # Score total ponderado
            score_total = (
                0.6 * option.get('semantic_score', 0.0) +
                0.3 * option.get('lexical_score', 0.0) +
                0.1 * contextual_score
            )
            
            if score_total > best_score:
                best_score = score_total
                best_candidate = option.copy()
                best_candidate['contextual_score'] = contextual_score
                best_candidate['total_score'] = score_total
        
        return best_candidate
    
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
        
        # Capítulos de alimentos/bebidas
        food_chapters = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23']
        
        # Capítulos de maquinaria y electrónica
        machinery_chapters = ['84', '85', '90']
        
        # Capítulos de materias primas minerales
        mineral_chapters = ['25', '26']
        
        # Verificar incoherencias graves
        
        # 1. Alimentos con uso no alimentario
        if chapter in food_chapters:
            if uso_principal in ['construccion', 'ferreteria', 'herramienta', 'industrial', 'electricidad', 'automotriz', 'computo']:
                logging.warning(f"Incoherencia detectada: HS {hs_code} (alimentos) con uso {uso_principal}")
                return False
        
        # 2. Maquinaria/electrónica con tipo "materia prima" o material construcción
        if chapter in machinery_chapters:
            if tipo_bien == 'materia_prima' or material in ['arena', 'ladrillo', 'cemento', 'piedra']:
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
        if chapter == '64' and 'cafe' in text_lower or 'café' in text_lower:
            logging.warning(f"Incoherencia detectada: HS {hs_code} (calzado) pero menciona café")
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
                case_id, confidence, response_time, validation_score
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
    
    def _record_incremental_validation(self, case_id: int, start_time: datetime, end_time: datetime, confidence: float, national_code: str, validation_result: Dict, features: Dict, method: str):
        """Registra datos para validación incremental."""
        try:
            incremental_validation.record_classification(
                case_id=case_id,
                start_time=start_time,
                end_time=end_time,
                confidence=confidence,
                hs_code=national_code,
                validation_score=validation_result.get('validation_score', 0.0),
                features=features,
                method=method
            )
        except Exception as e:
            logging.warning(f"Error registrando validación incremental: {str(e)}")
    
    def _register_automatic_feedback(self, case_id: int, national_code: str, confidence: float, comment: str):
        """Registra feedback automático para casos de baja confianza o sospechosos."""
        try:
            # Solo intentar registrar feedback si case_id es válido
            if case_id and case_id > 0:
                learning_integration.register_feedback(
                    case_id=case_id,
                    predicted_hs=national_code,
                    requires_review=confidence < 0.6,
                    original_result={
                        'national_code': national_code,
                        'confidence': confidence,
                        'validation_flags': {},
                        'features': {}
                    },
                    user_comment=comment
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
            'requires_review': requires_review or validation_result.get('validation_score', 1.0) < 0.7
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
        
        for i, option in enumerate(options[:5]):  # Top 5
            candidate = {
                'hs': option.get('national_code', ''),
                'title': option.get('title', ''),
                'score': option.get('semantic_score', 0.0),
                'rank': i + 1
            }
            top_candidates.append(candidate)
        
        return top_candidates