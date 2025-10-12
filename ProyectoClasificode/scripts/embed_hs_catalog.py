#!/usr/bin/env python3
"""
Script para generar embeddings del catálogo HS
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from servicios.control_conexion import ControlConexion
from servicios.modeloPln.embedding_service import EmbeddingService
from servicios.modeloPln.vector_index import PgVectorIndex as VectorIndex
import json
import numpy as np

def load_hs_catalog():
    """Cargar catálogo HS desde archivo o base de datos"""
    # En una implementación real, esto cargaría desde una fuente de datos
    # Por ahora, usamos datos de ejemplo
    hs_catalog = [
        {
            'hs_code': '8471.30.00',
            'description': 'Computadoras portátiles, incluidas las de peso inferior o igual a 10 kg',
            'chapter': '84',
            'section': '85'
        },
        {
            'hs_code': '8471.41.00',
            'description': 'Computadoras de escritorio',
            'chapter': '84',
            'section': '85'
        },
        {
            'hs_code': '8517.12.00',
            'description': 'Teléfonos móviles',
            'chapter': '85',
            'section': '85'
        },
        {
            'hs_code': '6204.43.00',
            'description': 'Vestidos de mujer, de fibras sintéticas',
            'chapter': '62',
            'section': '11'
        },
        {
            'hs_code': '6104.43.00',
            'description': 'Vestidos de mujer, de fibras sintéticas',
            'chapter': '61',
            'section': '11'
        },
        {
            'hs_code': '0808.10.00',
            'description': 'Manzanas frescas',
            'chapter': '08',
            'section': '2'
        },
        {
            'hs_code': '0809.30.00',
            'description': 'Peras frescas',
            'chapter': '08',
            'section': '2'
        },
        {
            'hs_code': '8474.10.00',
            'description': 'Máquinas de clasificar, cribar, separar o lavar',
            'chapter': '84',
            'section': '16'
        },
        {
            'hs_code': '3004.90.00',
            'description': 'Medicamentos, excepto los de las partidas 3002, 3005 o 3006',
            'chapter': '30',
            'section': '6'
        }
    ]
    
    return hs_catalog

def generate_hs_embeddings():
    """Generar embeddings para el catálogo HS"""
    embedding_service = EmbeddingService()
    vector_index = VectorIndex()
    control_conexion = ControlConexion()
    
    try:
        # Abrir conexión
        control_conexion.abrir_bd()
        
        # Cargar catálogo HS
        hs_catalog = load_hs_catalog()
        
        print(f"Generando embeddings para {len(hs_catalog)} códigos HS...")
        
        # Generar embeddings y guardar en base de datos
        for i, hs_item in enumerate(hs_catalog, 1):
            # Crear texto combinado para embedding
            text = f"{hs_item['hs_code']} - {hs_item['description']}"
            
            # Generar embedding
            embedding = embedding_service.generate_embedding(text)
            
            # Guardar en base de datos
            print(f"Procesando ítem: {hs_item['hs_code']} - {hs_item['description']}")
            
            # Insertar o actualizar el ítem HS
            query = """
            INSERT INTO hs_items (
                hs_code, 
                title, 
                keywords, 
                level, 
                chapter, 
                parent_code,
                created_at, 
                updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (hs_code) DO UPDATE SET
                title = EXCLUDED.title,
                keywords = EXCLUDED.keywords,
                level = EXCLUDED.level,
                chapter = EXCLUDED.chapter,
                parent_code = EXCLUDED.parent_code,
                updated_at = NOW()
            RETURNING id
            """
            
            # Extraer el capítulo del código HS (primeros 2 dígitos)
            chapter = hs_item['hs_code'].split('.')[0][:2] if 'hs_code' in hs_item else None
            # El parent_code sería el código HS sin los últimos 3 caracteres (p.ej. 8471.30.00 -> 8471.30)
            parent_code = '.'.join(hs_item['hs_code'].split('.')[:2]) if 'hs_code' in hs_item else None
            
            params = (
                hs_item.get('hs_code'), 
                hs_item.get('description', ''),
                '',  # keywords vacío por defecto
                6,   # nivel 6 para códigos de 10 dígitos
                chapter,
                parent_code
            )
            
            try:
                print(f"Ejecutando query con parámetros: {params}")
                # Usar ejecutar_consulta_sql que devuelve un DataFrame
                result = control_conexion.ejecutar_consulta_sql(query, params)
                
                if result.empty:
                    print(f"Error: No se pudo insertar el ítem {hs_item['hs_code']}")
                    continue
                    
                # Obtener el ID del primer resultado
                item_id = result.iloc[0, 0]
                print(f"Ítem insertado/actualizado con ID: {item_id}")
                
                # Guardar embedding usando PgVectorIndex
                try:
                    vector_index.upsert(
                        owner_type='hs_item',
                        owner_id=item_id,
                        vector=embedding,
                        meta={
                            'hs_code': hs_item['hs_code'],
                            'title': hs_item['description']
                        }
                    )
                    print(f"  ✓ Embedding generado para {hs_item['hs_code']}")
                    
                except Exception as e:
                    print(f"  ✗ Error guardando embedding para {hs_item['hs_code']}: {str(e)}")
                    continue
                
            except Exception as e:
                print(f"Error al procesar el ítem {hs_item['hs_code']}: {str(e)}")
                continue
        
        print(f"\n✅ Se generaron embeddings para {len(hs_catalog)} códigos HS")
        
    except Exception as e:
        print(f"Error generando embeddings: {str(e)}")
        raise
    
    finally:
        # Cerrar conexiones
        if 'control_conexion' in locals():
            control_conexion.cerrar_conexion()
        control_conexion.cerrar_bd()

def search_similar_hs_codes(query_text: str, top_k: int = 5):
    """Buscar códigos HS similares"""
    vector_index = VectorIndex()
    
    try:
        # Cargar índice si existe
        if os.path.exists('data/hs_catalog_index.json'):
            vector_index.load_index('data/hs_catalog_index.json')
            print(f"Índice cargado con {vector_index.get_stats()['total_vectors']} vectores")
        else:
            print("Índice no encontrado. Ejecute primero generate_hs_embeddings()")
            return
        
        # Buscar similares
        results = vector_index.search_text(query_text, top_k=top_k, threshold=0.3)
        
        print(f"\nResultados para: '{query_text}'")
        print("-" * 50)
        
        for i, result in enumerate(results, 1):
            metadata = result['metadata']
            print(f"{i}. Código HS: {metadata['hs_code']}")
            print(f"   Descripción: {metadata['description']}")
            print(f"   Similitud: {result['similarity']:.3f}")
            print(f"   Capítulo: {metadata['chapter']}, Sección: {metadata['section']}")
            print()
        
    except Exception as e:
        print(f"Error en búsqueda: {str(e)}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generar embeddings del catálogo HS')
    parser.add_argument('--generate', action='store_true', help='Generar embeddings')
    parser.add_argument('--search', type=str, help='Buscar códigos HS similares')
    parser.add_argument('--top-k', type=int, default=5, help='Número de resultados')
    
    args = parser.parse_args()
    
    if args.generate:
        generate_hs_embeddings()
    elif args.search:
        search_similar_hs_codes(args.search, args.top_k)
    else:
        print("Use --generate para generar embeddings o --search 'texto' para buscar")
