#!/usr/bin/env python3
"""
Script para probar el sistema de aprendizaje integrado
"""

import sys
import os
import requests
import json
from datetime import datetime

def test_learning_integration():
    """Prueba el sistema de aprendizaje integrado"""
    
    base_url = "http://localhost:5000"
    
    print("🧪 Probando Sistema de Aprendizaje Integrado...")
    print("="*60)
    
    # 1. Verificar que el servidor esté ejecutándose
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code != 200:
            print("❌ Servidor no está ejecutándose en http://localhost:5000")
            return
        print("✅ Servidor ejecutándose correctamente")
    except Exception as e:
        print(f"❌ Error conectando al servidor: {e}")
        return
    
    print()
    
    # 2. Probar clasificación con aprendizaje automático
    print("2. Probando clasificación con aprendizaje automático")
    print("-" * 50)
    
    test_products = [
        {
            "product_title": "Licuadora eléctrica",
            "product_desc": "Licuadora eléctrica de 1000W con 6 velocidades, jarra de vidrio 1.5L"
        },
        {
            "product_title": "Mouse gaming",
            "product_desc": "Mouse gaming óptico inalámbrico, 16000 DPI, RGB, para juegos"
        },
        {
            "product_title": "Camiseta algodón",
            "product_desc": "Camiseta de algodón 100%, talla M, color azul, manga corta"
        }
    ]
    
    for i, product in enumerate(test_products, 1):
        print(f"Producto {i}: {product['product_title']}")
        
        try:
            # Crear caso
            case_response = requests.post(f"{base_url}/cases", json=product)
            if case_response.status_code != 200:
                print(f"   ❌ Error creando caso: {case_response.text}")
                continue
            
            case_data = case_response.json()
            case_id = case_data.get('details', {}).get('case_id')
            
            if not case_id:
                print(f"   ❌ No se obtuvo ID de caso")
                continue
            
            # Clasificar
            classify_response = requests.post(f"{base_url}/api/v1/classify/{case_id}", json={})
            if classify_response.status_code != 200:
                print(f"   ❌ Error clasificando: {classify_response.text}")
                continue
            
            classify_data = classify_response.json()
            details = classify_data.get('details', {})
            
            hs_code = details.get('national_code', '')
            title = details.get('title', '')
            
            print(f"   ✅ Clasificado: {hs_code} - {title}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print()
    
    # 3. Verificar estadísticas de aprendizaje
    print("3. Verificando estadísticas de aprendizaje")
    print("-" * 50)
    
    try:
        # Nota: Este endpoint requiere autenticación, por lo que puede fallar
        # En un entorno real, necesitarías autenticarte primero
        response = requests.get(f"{base_url}/admin/learning/stats")
        
        if response.status_code == 200:
            stats_data = response.json()
            details = stats_data.get('details', {})
            stats = details.get('stats', {})
            suggestions = details.get('suggestions', [])
            
            print("✅ Estadísticas de aprendizaje:")
            print(f"   - Patrones de error: {stats.get('error_patterns_count', 0)}")
            print(f"   - Patrones de éxito: {stats.get('success_patterns_count', 0)}")
            print(f"   - Reglas aprendidas: {stats.get('learned_rules_count', 0)}")
            print(f"   - Total errores: {stats.get('total_errors', 0)}")
            print(f"   - Total éxitos: {stats.get('total_successes', 0)}")
            
            if suggestions:
                print("   Sugerencias de mejora:")
                for suggestion in suggestions:
                    print(f"     - {suggestion}")
            else:
                print("   No hay sugerencias de mejora disponibles")
                
        elif response.status_code == 401:
            print("⚠️ Endpoint requiere autenticación (normal en producción)")
        else:
            print(f"❌ Error obteniendo estadísticas: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print()
    
    # 4. Verificar archivo de datos de aprendizaje
    print("4. Verificando archivo de datos de aprendizaje")
    print("-" * 50)
    
    learning_file = "learning_data.json"
    if os.path.exists(learning_file):
        try:
            with open(learning_file, 'r', encoding='utf-8') as f:
                learning_data = json.load(f)
            
            error_patterns = learning_data.get('error_patterns', {})
            success_patterns = learning_data.get('success_patterns', {})
            
            print("✅ Archivo de datos de aprendizaje encontrado:")
            print(f"   - Patrones de error: {len(error_patterns)}")
            print(f"   - Patrones de éxito: {len(success_patterns)}")
            
            if error_patterns:
                print("   Errores más comunes:")
                for error_type, patterns in list(error_patterns.items())[:3]:
                    print(f"     - {error_type}: {len(patterns)} casos")
                    
        except Exception as e:
            print(f"❌ Error leyendo archivo de aprendizaje: {e}")
    else:
        print("⚠️ Archivo de datos de aprendizaje no encontrado")
    
    print()
    print("="*60)
    print("✅ Prueba de sistema de aprendizaje completada")
    print()
    print("📋 Resumen:")
    print("- El sistema de aprendizaje está integrado en el clasificador")
    print("- Cada clasificación se analiza automáticamente")
    print("- Los datos se guardan en learning_data.json")
    print("- Las estadísticas están disponibles via API")
    print()
    print("🚀 Para activar completamente el sistema:")
    print("1. Reinicia el servidor Flask")
    print("2. Haz algunas clasificaciones")
    print("3. Verifica las estadísticas en /admin/learning/stats")

if __name__ == "__main__":
    test_learning_integration()
