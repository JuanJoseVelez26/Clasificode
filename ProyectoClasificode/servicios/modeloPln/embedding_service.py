import os
import json
import numpy as np
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

class EmbeddingService:
    """Servicio de embeddings con adaptador para múltiples proveedores"""
    
    def __init__(self):
        self.provider = None
        self.model = None
        self.dimension = None
        self.client = None
        self._load_config()
        self._initialize_client()
    
    def _load_config(self):
        """Cargar configuración desde config.json o variables de entorno"""
        # Asegura cargar .env incluso si Main no lo cargó aún
        try:
            from dotenv import load_dotenv  # type: ignore
            load_dotenv()
        except Exception:
            pass
        try:
            # Intentar cargar desde config/config.json y luego configuracion/config.json (compatibilidad)
            config = None
            try:
                with open('config/config.json', 'r') as f:
                    config = json.load(f)
            except Exception:
                with open('configuracion/config.json', 'r') as f:
                    config = json.load(f)

            self.provider = config.get('EMBED_PROVIDER', os.getenv('EMBED_PROVIDER', 'openai'))
            # Modelo por defecto actualizado a la serie text-embedding-3
            self.model = config.get('EMBED_MODEL', os.getenv('EMBED_MODEL', 'text-embedding-3-small'))
            
        except (FileNotFoundError, json.JSONDecodeError):
            # Fallback a variables de entorno
            self.provider = os.getenv('EMBED_PROVIDER', 'openai')
            self.model = os.getenv('EMBED_MODEL', 'text-embedding-3-small')
        
        # Configurar dimensiones por modelo
        self.dimension_map = {
            'text-embedding-ada-002': 1536,
            'text-embedding-3-small': 1536,
            'text-embedding-3-large': 3072,
            'sentence-transformers/all-MiniLM-L6-v2': 384,
            'sentence-transformers/all-mpnet-base-v2': 768,
            'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2': 384
        }
        
        self.dimension = self.dimension_map.get(self.model, 768)
    
    def _initialize_client(self):
        """Inicializar cliente del proveedor de embeddings"""
        try:
            if self.provider.lower() == 'openai':
                self._init_openai_client()
            elif self.provider.lower() in ['huggingface', 'hf']:
                self._init_huggingface_client()
            else:
                # Fallback a embeddings simulados
                self._init_mock_client()
            # Log claro del estado
            print(f"EmbeddingService -> provider: {self.provider}, model: {self.model}")
        except Exception as e:
            print(f"Error inicializando cliente de embeddings: {e}")
            self._init_mock_client()
            print(f"EmbeddingService -> provider: {self.provider}, model: {self.model}")
    
    def _init_openai_client(self):
        """Inicializar cliente de OpenAI"""
        try:
            # Intentar importar cliente OpenAI v1 (preferido)
            try:
                from openai import OpenAI  # type: ignore
                _client_ctor = OpenAI
            except Exception:
                # Compatibilidad: algunos entornos exponen openai.OpenAI
                import openai  # type: ignore
                _client_ctor = getattr(openai, 'OpenAI')
            
            # Resolver API key (prioriza env, luego config)
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                try:
                    config = None
                    try:
                        with open('config/config.json', 'r') as f:
                            config = json.load(f)
                    except Exception:
                        with open('configuracion/config.json', 'r') as f:
                            config = json.load(f)
                    api_key = config.get('OPENAI_API_KEY')
                except Exception:
                    api_key = None
            
            if not api_key:
                raise ValueError("OpenAI API key no encontrada")

            # Construir cliente con la API key
            self.client = _client_ctor(api_key=api_key)
            self.provider = 'openai'
            
        except ImportError:
            raise ImportError("openai no está instalado. Instalar con: pip install openai")
    
    def _init_huggingface_client(self):
        """Inicializar cliente de HuggingFace"""
        try:
            from sentence_transformers import SentenceTransformer
            
            # Obtener token desde config o variable de entorno
            token = None
            try:
                config = None
                try:
                    with open('config/config.json', 'r') as f:
                        config = json.load(f)
                except Exception:
                    with open('configuracion/config.json', 'r') as f:
                        config = json.load(f)
                token = config.get('HF_TOKEN')
            except:
                pass
            
            if not token:
                token = os.getenv('HF_TOKEN')
            
            # Cargar modelo
            self.client = SentenceTransformer(self.model)
            self.provider = 'huggingface'
            
        except ImportError:
            raise ImportError("sentence-transformers no está instalado. Instalar con: pip install sentence-transformers")
    
    def _init_mock_client(self):
        """Inicializar cliente simulado para desarrollo"""
        self.client = None
        self.provider = 'mock'
        print("Usando embeddings simulados para desarrollo")
    
    def embed(self, texts: Union[str, List[str]]) -> Union[np.ndarray, List[np.ndarray]]:
        """Generar embeddings para texto(s)"""
        if isinstance(texts, str):
            texts = [texts]
        
        if not texts:
            return np.array([])
        
        try:
            if self.provider == 'openai':
                return self._embed_openai(texts)
            elif self.provider == 'huggingface':
                return self._embed_huggingface(texts)
            else:
                return self._embed_mock(texts)
                
        except Exception as e:
            print(f"Error generando embeddings: {e}")
            return self._embed_mock(texts)
    
    def _embed_openai(self, texts: List[str]) -> np.ndarray:
        """Generar embeddings usando OpenAI"""
        if not self.client:
            raise ValueError("Cliente OpenAI no inicializado")
        
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts
            )
            
            embeddings = [data.embedding for data in response.data]
            return np.array(embeddings)
            
        except Exception as e:
            raise Exception(f"Error en OpenAI embeddings: {e}")
    
    def _embed_huggingface(self, texts: List[str]) -> np.ndarray:
        """Generar embeddings usando HuggingFace"""
        if not self.client:
            raise ValueError("Cliente HuggingFace no inicializado")
        
        try:
            embeddings = self.client.encode(texts)
            return embeddings
            
        except Exception as e:
            raise Exception(f"Error en HuggingFace embeddings: {e}")
    
    def _embed_mock(self, texts: List[str]) -> np.ndarray:
        """Generar embeddings simulados para desarrollo"""
        # Generar embeddings aleatorios pero consistentes
        embeddings = []
        
        for text in texts:
            # Usar hash del texto para generar embedding consistente
            import hashlib
            text_hash = hashlib.md5(text.encode()).hexdigest()
            seed = int(text_hash[:8], 16)
            
            np.random.seed(seed)
            embedding = np.random.normal(0, 1, self.dimension)
            # Normalizar
            embedding = embedding / np.linalg.norm(embedding)
            embeddings.append(embedding)
        
        return np.array(embeddings)
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """Generar embedding para un texto (alias para compatibilidad)"""
        return self.embed(text)
    
    def dim(self) -> int:
        """Obtener dimensión de los embeddings"""
        return self.dimension
    
    def id(self) -> str:
        """Obtener identificador del modelo"""
        return f"{self.provider}:{self.model}"
    
    def get_model_info(self) -> Dict[str, Any]:
        """Obtener información del modelo"""
        return {
            'provider': self.provider,
            'model': self.model,
            'dimension': self.dimension,
            'model_id': self.id(),
            'status': 'active' if self.client else 'mock'
        }
    
    def calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray, method: str = 'cosine') -> float:
        """Calcular similitud entre dos embeddings"""
        if method == 'cosine':
            return self._cosine_similarity(embedding1, embedding2)
        elif method == 'euclidean':
            return self._euclidean_distance(embedding1, embedding2)
        elif method == 'dot':
            return self._dot_product(embedding1, embedding2)
        else:
            raise ValueError(f"Método de similitud no soportado: {method}")
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calcular similitud coseno"""
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    def _euclidean_distance(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calcular distancia euclidiana"""
        return np.linalg.norm(a - b)
    
    def _dot_product(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calcular producto punto"""
        return np.dot(a, b)
    
    def find_similar_embeddings(self, query_embedding: np.ndarray, 
                               candidate_embeddings: List[np.ndarray], 
                               k: int = 5, 
                               method: str = 'cosine') -> List[Dict[str, Any]]:
        """Encontrar embeddings más similares"""
        similarities = []
        
        for i, candidate in enumerate(candidate_embeddings):
            similarity = self.calculate_similarity(query_embedding, candidate, method)
            similarities.append({
                'index': i,
                'similarity': similarity,
                'distance': 1 - similarity if method == 'cosine' else similarity
            })
        
        # Ordenar por similitud (descendente para cosine, ascendente para euclidean)
        reverse = method == 'cosine'
        similarities.sort(key=lambda x: x['similarity'], reverse=reverse)
        
        return similarities[:k]
    
    def batch_embed(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Generar embeddings en lotes para mejor rendimiento"""
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self.embed(batch)
            all_embeddings.append(batch_embeddings)
        
        return np.vstack(all_embeddings)
    
    def normalize_embeddings(self, embeddings: np.ndarray) -> np.ndarray:
        """Normalizar embeddings a vectores unitarios"""
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Evitar división por cero
        return embeddings / norms
    
    def get_embedding_statistics(self, embeddings: np.ndarray) -> Dict[str, Any]:
        """Obtener estadísticas de los embeddings"""
        if len(embeddings) == 0:
            return {}
        
        return {
            'count': len(embeddings),
            'dimension': embeddings.shape[1] if len(embeddings.shape) > 1 else 1,
            'mean_norm': np.mean(np.linalg.norm(embeddings, axis=1)),
            'std_norm': np.std(np.linalg.norm(embeddings, axis=1)),
            'min_norm': np.min(np.linalg.norm(embeddings, axis=1)),
            'max_norm': np.max(np.linalg.norm(embeddings, axis=1)),
            'mean_values': np.mean(embeddings, axis=0).tolist(),
            'std_values': np.std(embeddings, axis=0).tolist()
        }
    
    def test_connection(self) -> Dict[str, Any]:
        """Probar conexión con el proveedor de embeddings"""
        try:
            test_text = "Test embedding generation"
            embedding = self.embed(test_text)
            
            return {
                'status': 'success',
                'provider': self.provider,
                'model': self.model,
                'dimension': self.dimension,
                'test_embedding_shape': embedding.shape,
                'test_embedding_norm': float(np.linalg.norm(embedding)),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'provider': self.provider,
                'model': self.model,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
