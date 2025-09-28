#!/usr/bin/env python3
"""
Script para poblar la base de datos con datos iniciales
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from servicios.control_conexion import ControlConexion
import hashlib
import json

def hash_password(password: str) -> str:
    """Generar hash de contraseña"""
    return hashlib.sha256(password.encode()).hexdigest()

def seed_database():
    """Poblar la base de datos con datos iniciales"""
    control_conexion = ControlConexion()
    
    try:
        # Abrir conexión
        control_conexion.abrir_bd()
        
        # Crear usuarios iniciales
        users_data = [
            {
                'email': 'admin@clasificode.com',
                'password_hash': hash_password('admin123'),
                'name': 'Administrador',
                'role': 'admin',
                'is_active': True
            },
            {
                'email': 'auditor@clasificode.com',
                'password_hash': hash_password('auditor123'),
                'name': 'Auditor Principal',
                'role': 'auditor',
                'is_active': True
            },
            {
                'email': 'operator@clasificode.com',
                'password_hash': hash_password('operator123'),
                'name': 'Operador',
                'role': 'operator',
                'is_active': True
            }
        ]
        
        print("Creando usuarios...")
        for user in users_data:
            query = """
            INSERT INTO users (email, password_hash, name, role, is_active, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (email) DO NOTHING
            """
            control_conexion.ejecutar_comando_sql(query, (
                user['email'], user['password_hash'], user['name'], 
                user['role'], user['is_active']
            ))
        
        # Obtener ID del primer usuario para crear casos
        user_query = "SELECT id FROM users WHERE email = 'operator@clasificode.com' LIMIT 1"
        user_df = control_conexion.ejecutar_consulta_sql(user_query)
        if not user_df.empty:
            user_id = user_df.iloc[0]['id']
            
            # Crear casos de ejemplo
            cases_data = [
                {
                    'created_by': user_id,
                    'status': 'open',
                    'product_title': 'Computadora portátil Dell Inspiron 15',
                    'product_desc': 'Laptop con procesador Intel i7, 16GB RAM, 512GB SSD, pantalla 15.6"',
                    'attrs_json': json.dumps({
                        'brand': 'Dell',
                        'model': 'Inspiron 15',
                        'processor': 'Intel i7',
                        'ram': '16GB',
                        'storage': '512GB SSD'
                    })
                },
                {
                    'created_by': user_id,
                    'status': 'open',
                    'product_title': 'Conjunto deportivo Nike',
                    'product_desc': 'Camiseta y pantalón deportivo de poliéster, marca Nike',
                    'attrs_json': json.dumps({
                        'brand': 'Nike',
                        'material': 'poliéster',
                        'type': 'deportivo',
                        'pieces': 2
                    })
                },
                {
                    'created_by': user_id,
                    'status': 'validated',
                    'product_title': 'Manzanas orgánicas',
                    'product_desc': 'Manzanas frescas orgánicas, variedad Gala, importadas',
                    'attrs_json': json.dumps({
                        'type': 'fruta',
                        'variety': 'Gala',
                        'organic': True,
                        'origin': 'importado'
                    })
                }
            ]
            
            print("Creando casos de ejemplo...")
            for case in cases_data:
                query = """
                INSERT INTO cases (created_by, status, product_title, product_desc, attrs_json, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                """
                control_conexion.ejecutar_comando_sql(query, (
                    case['created_by'], case['status'], case['product_title'], 
                    case['product_desc'], case['attrs_json']
                ))
        
        # Crear reglas RGI
        rules_data = [
            {
                'rgi': 'RGI1',
                'description': 'Los títulos de las Secciones, Capítulos y Subcapítulos no tienen valor legal para la clasificación arancelaria'
            },
            {
                'rgi': 'RGI2A',
                'description': 'Cualquier referencia en un epígrafe a una materia o sustancia debe entenderse como referida a esa materia o sustancia, ya sea pura o impura'
            },
            {
                'rgi': 'RGI2B',
                'description': 'Cualquier referencia a mercancías de un material o sustancia determinados debe entenderse como referida a las mercancías constituidas total o parcialmente por ese material o sustancia'
            },
            {
                'rgi': 'RGI3A',
                'description': 'Cuando por aplicación de la Regla 2(b) o por cualquier otra razón, una mercancía pudiera clasificarse en dos o más partidas, la clasificación se efectuará de la manera siguiente'
            },
            {
                'rgi': 'RGI3B',
                'description': 'Las mezclas, las mercancías compuestas que consten de materias diferentes o estén constituidas por la unión de mercancías diferentes'
            },
            {
                'rgi': 'RGI3C',
                'description': 'Cuando una mercancía pudiera clasificarse en dos o más partidas en virtud de la Regla 3(b), se clasificará en la partida que contenga la materia o componente que le confiera el carácter esencial'
            },
            {
                'rgi': 'RGI4',
                'description': 'Las mercancías que no puedan clasificarse aplicando las Reglas anteriores se clasificarán en la partida que comprenda las mercancías más análogas'
            },
            {
                'rgi': 'RGI5A',
                'description': 'Los estuches para cámaras fotográficas, instrumentos musicales, armas, instrumentos de dibujo, collares y estuches similares, especialmente conformados y acondicionados para contener una mercancía determinada'
            },
            {
                'rgi': 'RGI5B',
                'description': 'Sujeta a las disposiciones de la Regla 5(a), los embalajes presentados con las mercancías que contengan se clasificarán con dichas mercancías cuando sean del tipo normalmente utilizado para esa clase de mercancías'
            },
            {
                'rgi': 'RGI6',
                'description': 'La clasificación de mercancías en las subpartidas de una misma partida está determinada legalmente por los textos de estas subpartidas y de las Notas de subpartida correspondientes'
            }
        ]
        
        print("Creando reglas RGI...")
        for rule in rules_data:
            query = """
            INSERT INTO rgi_rules (rgi, description, created_at, updated_at)
            VALUES (%s, %s, NOW(), NOW())
            ON CONFLICT (rgi) DO NOTHING
            """
            control_conexion.ejecutar_comando_sql(query, (rule['rgi'], rule['description']))
        
        # Crear fuentes legales
        legal_sources_data = [
            {
                'source_type': 'RGI',
                'ref_code': 'RGI-2024-001',
                'url': 'https://www.wcoomd.org/en/topics/nomenclature/instrument-and-tools/general-rules.aspx',
                'summary': 'Reglas Generales de Interpretación del Sistema Armonizado'
            },
            {
                'source_type': 'RESOLUCION',
                'ref_code': 'RES-2024-001',
                'url': None,
                'summary': 'Resolución sobre clasificación de productos electrónicos'
            },
            {
                'source_type': 'MANUAL',
                'ref_code': 'MAN-2024-001',
                'url': None,
                'summary': 'Manual de procedimientos de clasificación arancelaria'
            }
        ]
        
        print("Creando fuentes legales...")
        for source in legal_sources_data:
            query = """
            INSERT INTO legal_sources (source_type, ref_code, url, summary, created_at, updated_at)
            VALUES (%s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (ref_code) DO NOTHING
            """
            control_conexion.ejecutar_comando_sql(query, (
                source['source_type'], source['ref_code'], source['url'], source['summary']
            ))
        
        # Crear items HS de ejemplo
        hs_items_data = [
            {
                'hs_code': '8471.30.00',
                'title': 'Computadoras portátiles, incluidas las de peso inferior o igual a 10 kg',
                'keywords': 'laptop, computadora portátil, notebook',
                'level': 6,
                'chapter': 84,
                'parent_code': '8471.30'
            },
            {
                'hs_code': '8471.41.00',
                'title': 'Computadoras de escritorio',
                'keywords': 'desktop, computadora de escritorio, PC',
                'level': 6,
                'chapter': 84,
                'parent_code': '8471.41'
            },
            {
                'hs_code': '8517.12.00',
                'title': 'Teléfonos móviles',
                'keywords': 'celular, smartphone, teléfono móvil',
                'level': 6,
                'chapter': 85,
                'parent_code': '8517.12'
            },
            {
                'hs_code': '6204.43.00',
                'title': 'Vestidos de mujer, de fibras sintéticas',
                'keywords': 'vestido, mujer, sintético, poliéster',
                'level': 6,
                'chapter': 62,
                'parent_code': '6204.43'
            },
            {
                'hs_code': '0808.10.00',
                'title': 'Manzanas frescas',
                'keywords': 'manzana, fruta, fresca',
                'level': 6,
                'chapter': 8,
                'parent_code': '0808.10'
            }
        ]
        
        print("Creando items HS...")
        for item in hs_items_data:
            query = """
            INSERT INTO hs_items (hs_code, title, keywords, level, chapter, parent_code, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (hs_code) DO NOTHING
            """
            control_conexion.ejecutar_comando_sql(query, (
                item['hs_code'], item['title'], item['keywords'], 
                item['level'], item['chapter'], item['parent_code']
            ))
        
        print("¡Base de datos poblada exitosamente!")
        
    except Exception as e:
        print(f"Error poblando la base de datos: {str(e)}")
        raise
    finally:
        # Cerrar conexión
        control_conexion.cerrar_bd()

if __name__ == "__main__":
    seed_database()
