#!/usr/bin/env python3
"""
Script de prueba para verificar los endpoints de exportación
"""

import requests
import json
import os
from datetime import datetime

def test_export_endpoints():
    """Prueba los endpoints de exportación"""
    
    base_url = "http://localhost:5000"
    
    # Datos de prueba
    test_data = {
        "hs_code": "8509400000",
        "description": "Licuadoras y mezcladoras",
        "confidence": 0.85,
        "product_description": "Licuadora eléctrica de 1000W con 6 velocidades",
        "input_type": "text",
        "classification_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "explanation": "Clasificación por regla específica para productos comunes: Licuadoras y mezcladoras",
        "similar_items": [
            {"hs_code": "8509400000", "description": "Licuadoras y mezcladoras", "confidence": 0.85},
            {"hs_code": "8509800000", "description": "Otros aparatos electrodomésticos", "confidence": 0.70}
        ],
        "top_k": [
            {"hs_code": "8509400000", "description": "Licuadoras y mezcladoras", "confidence": 0.85},
            {"hs_code": "8509800000", "description": "Otros aparatos electrodomésticos", "confidence": 0.70},
            {"hs_code": "8414200000", "description": "Bombas de vacío", "confidence": 0.45}
        ]
    }
    
    print("🧪 Probando endpoints de exportación...")
    print("="*60)
    
    # 1. Probar endpoint de formatos disponibles
    print("1. Probando GET /export/formats")
    try:
        response = requests.get(f"{base_url}/export/formats")
        if response.status_code == 200:
            formats = response.json()
            print(f"   ✅ Formatos disponibles: {len(formats.get('formats', []))}")
            for fmt in formats.get('formats', []):
                print(f"      - {fmt.get('name')}: {fmt.get('description')}")
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Error de conexión: {e}")
    
    print()
    
    # 2. Probar exportación a PDF
    print("2. Probando POST /export/pdf")
    try:
        response = requests.post(
            f"{base_url}/export/pdf",
            json=test_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            # Guardar archivo PDF
            filename = f"test_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"   ✅ PDF generado exitosamente: {filename}")
            print(f"   📄 Tamaño: {len(response.content)} bytes")
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()
    
    # 3. Probar exportación a CSV
    print("3. Probando POST /export/csv")
    try:
        response = requests.post(
            f"{base_url}/export/csv",
            json=test_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            # Guardar archivo CSV
            filename = f"test_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"   ✅ CSV generado exitosamente: {filename}")
            print(f"   📊 Contenido:")
            print(response.text[:200] + "..." if len(response.text) > 200 else response.text)
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()
    print("="*60)
    print("✅ Pruebas completadas")

def test_export_with_minimal_data():
    """Prueba con datos mínimos"""
    
    base_url = "http://localhost:5000"
    
    minimal_data = {
        "hs_code": "8471300000",
        "description": "Computadoras portátiles",
        "confidence": 0.90,
        "product_description": "Laptop gaming de 15 pulgadas",
        "input_type": "text"
    }
    
    print("🧪 Probando exportación con datos mínimos...")
    print("="*60)
    
    # Probar PDF con datos mínimos
    print("1. Probando PDF con datos mínimos")
    try:
        response = requests.post(
            f"{base_url}/export/pdf",
            json=minimal_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            filename = f"test_minimal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"   ✅ PDF generado: {filename}")
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Probar CSV con datos mínimos
    print("2. Probando CSV con datos mínimos")
    try:
        response = requests.post(
            f"{base_url}/export/csv",
            json=minimal_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            filename = f"test_minimal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"   ✅ CSV generado: {filename}")
            print(f"   📊 Contenido:")
            print(response.text)
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    print("🚀 Iniciando pruebas de exportación...")
    print("Asegúrate de que el servidor Flask esté ejecutándose en http://localhost:5000")
    print()
    
    try:
        test_export_endpoints()
        print()
        test_export_with_minimal_data()
    except KeyboardInterrupt:
        print("\n⏹️ Pruebas interrumpidas por el usuario")
    except Exception as e:
        print(f"\n❌ Error general: {e}")
    
    print("\n🎉 Pruebas finalizadas")
