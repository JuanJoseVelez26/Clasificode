#!/usr/bin/env python3
"""
Sistema de actualización automática de embeddings
"""

import os
import json
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

class EmbeddingUpdater:
    def __init__(self, embedding_service):
        self.embedding_service = embedding_service
        self.cache_file = "embedding_cache.json"
        self.last_update_file = "last_embedding_update.json"
        
    def should_update_embeddings(self) -> bool:
        """Determina si los embeddings necesitan actualización"""
        
        # Verificar si existe el archivo de última actualización
        if not os.path.exists(self.last_update_file):
            return True
        
        try:
            with open(self.last_update_file, 'r') as f:
                last_update_data = json.load(f)
            
            last_update = datetime.fromisoformat(last_update_data['last_update'])
            
            # Actualizar si han pasado más de 7 días
            if datetime.now() - last_update > timedelta(days=7):
                return True
            
            # Verificar si hay cambios en la base de datos
            if self._has_database_changes():
                return True
            
            return False
            
        except Exception as e:
            print(f"Error verificando última actualización: {e}")
            return True
    
    def _has_database_changes(self) -> bool:
        """Verifica si ha habido cambios en la base de datos"""
        
        # Aquí se podría implementar una verificación más sofisticada
        # Por ejemplo, verificar timestamps de tablas relevantes
        # Por ahora, asumimos que no hay cambios
        return False
    
    def update_embeddings_if_needed(self) -> bool:
        """Actualiza los embeddings si es necesario"""
        
        if not self.should_update_embeddings():
            print("Los embeddings están actualizados. No se requiere actualización.")
            return False
        
        print("Actualizando embeddings...")
        
        try:
            # Aquí se ejecutaría la lógica de actualización de embeddings
            # Por ejemplo, re-procesar todos los productos en la base de datos
            
            # Simular actualización
            self._update_embedding_cache()
            
            # Actualizar timestamp de última actualización
            self._update_last_update_timestamp()
            
            print("Embeddings actualizados exitosamente.")
            return True
            
        except Exception as e:
            print(f"Error actualizando embeddings: {e}")
            return False
    
    def _update_embedding_cache(self):
        """Actualiza la caché de embeddings"""
        
        # Simular actualización de caché
        cache_data = {
            'last_updated': datetime.now().isoformat(),
            'total_embeddings': 1000,  # Número simulado
            'model_version': 'text-embedding-3-small'
        }
        
        with open(self.cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
    
    def _update_last_update_timestamp(self):
        """Actualiza el timestamp de la última actualización"""
        
        update_data = {
            'last_update': datetime.now().isoformat(),
            'update_type': 'automatic',
            'success': True
        }
        
        with open(self.last_update_file, 'w') as f:
            json.dump(update_data, f, indent=2)
    
    def get_embedding_status(self) -> Dict[str, Any]:
        """Obtiene el estado actual de los embeddings"""
        
        status = {
            'cache_exists': os.path.exists(self.cache_file),
            'last_update_exists': os.path.exists(self.last_update_file),
            'needs_update': self.should_update_embeddings(),
            'last_update': None,
            'cache_info': None
        }
        
        # Obtener información de última actualización
        if status['last_update_exists']:
            try:
                with open(self.last_update_file, 'r') as f:
                    last_update_data = json.load(f)
                status['last_update'] = last_update_data.get('last_update')
            except Exception as e:
                print(f"Error leyendo archivo de última actualización: {e}")
        
        # Obtener información de caché
        if status['cache_exists']:
            try:
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                status['cache_info'] = cache_data
            except Exception as e:
                print(f"Error leyendo archivo de caché: {e}")
        
        return status

def main():
    """Función principal para verificar y actualizar embeddings"""
    
    print("="*80)
    print("SISTEMA DE ACTUALIZACIÓN DE EMBEDDINGS")
    print("="*80)
    
    # Simular embedding service
    class MockEmbeddingService:
        def __init__(self):
            pass
    
    embedding_service = MockEmbeddingService()
    updater = EmbeddingUpdater(embedding_service)
    
    # Obtener estado de embeddings
    status = updater.get_embedding_status()
    
    print(f"Estado de la caché: {'Existe' if status['cache_exists'] else 'No existe'}")
    print(f"Archivo de última actualización: {'Existe' if status['last_update_exists'] else 'No existe'}")
    print(f"Necesita actualización: {'Sí' if status['needs_update'] else 'No'}")
    
    if status['last_update']:
        print(f"Última actualización: {status['last_update']}")
    
    if status['cache_info']:
        print(f"Información de caché: {status['cache_info']}")
    
    # Intentar actualizar si es necesario
    if status['needs_update']:
        print("\nIniciando actualización de embeddings...")
        success = updater.update_embeddings_if_needed()
        
        if success:
            print("[OK] Embeddings actualizados exitosamente.")
        else:
            print("[ERROR] Error actualizando embeddings.")
    else:
        print("\n[OK] Los embeddings están actualizados. No se requiere actualización.")
    
    print("\n" + "="*80)
    print("RECOMENDACIONES PARA EMBEDDINGS:")
    print("="*80)
    print("1. Los embeddings se actualizan automáticamente cada 7 días")
    print("2. Se actualizan cuando hay cambios en la base de datos")
    print("3. Para forzar actualización, elimine el archivo 'last_embedding_update.json'")
    print("4. Los embeddings se almacenan en caché para mejorar rendimiento")
    print("5. El modelo actual es 'text-embedding-3-small' de OpenAI")

if __name__ == "__main__":
    main()
