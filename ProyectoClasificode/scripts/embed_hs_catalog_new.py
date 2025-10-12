#!/usr/bin/env python3
"""
Script para generar embeddings del catálogo HS
"""

import sys
import os
import numpy as np
from typing import List, Dict, Any, Optional

# Añadir directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from servicios.control_conexion import ControlConexion
from servicios.modeloPln.embedding_service import EmbeddingService
from servicios.modeloPln.vector_index import PgVectorIndex as VectorIndex

def load_hs_catalog(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Cargar catálogo HS desde la base de datos
    
    Args:
        limit: Número máximo de ítems a cargar (opcional)
        
    Returns:
        Lista de diccionarios con los ítems del catálogo HS
    """
    control_conexion = ControlConexion()
    
    try:
        control_conexion.abrir_bd()
        
        # Consulta para obtener los ítems HS
        query = """
        SELECT 
            id, 
            hs_code, 
            title as description, 
            chapter, 
            parent_code,
            keywords,
            level
        FROM hs_items
        WHERE hs_code IS NOT NULL AND title IS NOT NULL
        """
        
        if limit:
            query += f" LIMIT {limit}"
            
        # Ejecutar consulta vía SQLAlchemy y pandas
        df = control_conexion.ejecutar_consulta_sql(query)
        
        if df is None or df.empty:
            print("Se cargaron 0 ítems HS desde la base de datos")
            return []
        
        # Convertir DataFrame a lista de dicts y normalizar tipos
        records = df.to_dict('records')
        for item in records:
            if 'id' in item and item['id'] is not None:
                item['id'] = int(item['id'])
            if 'level' in item and item['level'] is not None:
                item['level'] = int(item['level'])
            if 'chapter' in item and item['chapter'] is not None:
                try:
                    item['chapter'] = int(item['chapter'])
                except Exception:
                    pass
        
        print(f"Se cargaron {len(records)} ítems HS desde la base de datos")
        return records
        
    except Exception as e:
        print(f"Error al cargar el catálogo HS: {str(e)}")
        raise
        
    finally:
        if control_conexion and hasattr(control_conexion, 'cerrar_bd'):
            control_conexion.cerrar_bd()

def generate_hs_embeddings(limit: Optional[int] = None):
    """Generar embeddings para el catálogo HS"""
    embedding_service = EmbeddingService()
    vector_index = VectorIndex()
    
    try:
        # Cargar catálogo HS
        hs_catalog = load_hs_catalog(limit)
        
        if not hs_catalog:
            print("No se encontraron ítems HS para procesar")
            return
            
        print(f"Generando embeddings para {len(hs_catalog)} códigos HS...")
        
        # Contadores para estadísticas
        success = 0
        errors = 0
        
        # Generar embeddings y guardar en base de datos
        for i, hs_item in enumerate(hs_catalog, 1):
            try:
                # Crear texto combinado para embedding
                text = f"{hs_item['hs_code']} - {hs_item['description']}"
                
                print(f"Procesando ítem {i}/{len(hs_catalog)}: {hs_item['hs_code']} - {hs_item['description']}")
                
                # Generar embedding
                embedding = embedding_service.generate_embedding(text)
                
                # Convertir a lista de Python si es un array de NumPy
                if isinstance(embedding, np.ndarray):
                    embedding = embedding.tolist()
                
                # Asegurarse de que el ID sea un entero nativo de Python
                item_id = int(hs_item['id'])
                
                # Guardar embedding usando PgVectorIndex
                vector_index.upsert(
                    owner_type='hs_item',
                    owner_id=item_id,
                    vector=embedding,
                    meta={
                        'hs_code': hs_item['hs_code'],
                        'title': hs_item['description'],
                        'chapter': hs_item.get('chapter')
                    }
                )
                
                print(f"  ✓ Embedding generado para {hs_item['hs_code']}")
                success += 1
                
            except Exception as e:
                errors += 1
                print(f"  ✗ Error procesando {hs_item.get('hs_code', 'desconocido')}: {str(e)}")
                continue
        
        # Mostrar resumen
        print("\n" + "="*50)
        print("RESUMEN DE EJECUCIÓN")
        print("="*50)
        print(f"Total de ítems procesados: {len(hs_catalog)}")
        print(f"Éxitos: {success}")
        print(f"Errores: {errors}")
        print("="*50)
        
    except Exception as e:
        print(f"Error generando embeddings: {str(e)}")
        raise

def search_most_similar_hs_code(query_text: str):
    """Imprime en stdout el código HS más similar para el texto dado"""
    embedding_service = EmbeddingService()
    vector_index = VectorIndex()
    
    try:
        # Generar embedding para la consulta
        query_embedding = embedding_service.generate_embedding(query_text)
        
        # Convertir a lista de Python si es un array de NumPy
        if isinstance(query_embedding, np.ndarray):
            query_embedding = query_embedding.tolist()
        
        # Buscar solo el resultado más similar
        results = vector_index.search(
            query_embedding=query_embedding,
            owner_type='hs_item',
            top_k=1
        )
        
        if not results:
            print("")
            return
        
        best = results[0]
        meta = best.get('meta', {})
        hs_code = meta.get('hs_code', '')
        
        # Imprimir únicamente el código HS para consumo por el agente
        print(hs_code)
            
    except Exception as e:
        # En caso de error, imprimir vacío para no romper el consumo
        print("")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generar y buscar embeddings del catálogo HS')
    
    # Subcomandos
    subparsers = parser.add_subparsers(dest='command', help='Comandos disponibles')
    
    # Comando para generar embeddings
    gen_parser = subparsers.add_parser('generate', help='Generar embeddings para los códigos HS')
    gen_parser.add_argument('--limit', type=int, help='Número máximo de ítems a procesar')
    
    # Comando para buscar el código HS más similar
    search_parser = subparsers.add_parser('search', help='Retorna el código HS más similar')
    search_parser.add_argument('query', help='Texto de búsqueda')
    
    # Parsear argumentos
    args = parser.parse_args()
    
    # Ejecutar comando correspondiente
    if args.command == 'generate':
        generate_hs_embeddings(args.limit)
    elif args.command == 'search':
        search_most_similar_hs_code(args.query)
    else:
        parser.print_help()