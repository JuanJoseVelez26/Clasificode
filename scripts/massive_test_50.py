#!/usr/bin/env python3
"""
Script de prueba masiva (50 productos) para ClasifiCode.

Ejecuta el flujo completo:
1. Login y obtención de token JWT.
2. Creación de casos.
3. Clasificación vía /api/v1/classify/<case_id>.
4. Registro de métricas locales y generación de reporte.

Uso:
    python scripts/massive_test_50.py

Variables de entorno opcionales:
    CLASSIFICODE_BASE_URL         (default: http://127.0.0.1:5000)
    CLASSIFICODE_TEST_EMAIL       (default: juan.velez221@tau.usbmed.co)
    CLASSIFICODE_TEST_PASSWORD    (default: admin123)
"""

from __future__ import annotations

import json
import os
import statistics
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests


BASE_URL = os.getenv("CLASSIFICODE_BASE_URL", "http://127.0.0.1:5000")
TEST_EMAIL = os.getenv("CLASSIFICODE_TEST_EMAIL", "juan.velez221@tau.usbmed.co")
TEST_PASSWORD = os.getenv("CLASSIFICODE_TEST_PASSWORD", "admin123")
OUTPUTS_DIR = Path("outputs")
REPORT_PATH = OUTPUTS_DIR / "massive_test_50_report.json"
CSV_PATH = OUTPUTS_DIR / "massive_test_50_report.csv"


PRODUCT_DESCRIPTIONS: List[Tuple[str, str]] = [
    # Electrónica / informática
    ("Laptop profesional ultraliviana", "Laptop profesional ultraliviana con procesador Intel i7, 16GB RAM y SSD 1TB."),
    ("Servidor rack 2U", "Servidor rack 2U con 2 procesadores Xeon, 128GB RAM y 8 bahías hot-swap."),
    ("Monitor curvo gaming", "Monitor curvo gaming 34 pulgadas QHD, 165Hz, HDR y puertos HDMI/DisplayPort."),
    ("Router Wi-Fi 6 empresarial", "Router Wi-Fi 6 con administración en la nube, doble banda y seguridad WPA3."),
    ("Tablet resistente industrial", "Tablet industrial IP67, pantalla 10'', Android, NFC y lector de códigos."),

    # Maquinaria y herramientas
    ("Compresor de aire industrial", "Compresor de aire industrial 5HP, tanque 200 litros, lubricado por aceite."),
    ("Torno CNC", "Torno CNC de precisión para metales, control FANUC, 5 ejes, refrigeración integrada."),
    ("Taladro percutor inalámbrico", "Taladro percutor inalámbrico 20V, 2 baterías litio ion, torque ajustable."),
    ("Generador eléctrico diésel", "Generador eléctrico diésel 30kVA, arranque automático, cabina insonorizada."),
    ("Pulidora angular industrial", "Pulidora angular 230mm, 2200W, mango antivibración, uso continuo."),

    # Ferretería y construcción
    ("Panel de yeso resistente a la humedad", "Panel de yeso verde 12.5mm x 1.2m x 2.4m, resistente a la humedad para baños."),
    ("Perfil estructural galvanizado", "Perfil estructural galvanizado tipo C, 3 metros, calibre 14."),
    ("Adhesivo epóxico estructural", "Adhesivo epóxico bicomponente para anclajes, cartucho 585ml."),
    ("Membrana asfáltica prefabricada", "Membrana asfáltica prefabricada 4mm con refuerzo poliéster, para impermeabilización."),
    ("Broca de carburo para concreto", "Broca de carburo tungsteno SDS Max 20mm x 400mm."),

    # Textil y calzado
    ("Chaqueta impermeable outdoor", "Chaqueta impermeable outdoor con membrana transpirable, costuras termoselladas."),
    ("Guantes de seguridad anticorte", "Guantes de seguridad nivel anticorte 5, recubrimiento nitrilo en palma."),
    ("Botas de seguridad dieléctricas", "Botas de seguridad dieléctricas punta composite, suela antideslizante."),
    ("Pantalón ignífugo", "Pantalón ignífugo modacrílico para soldador, cintas reflectivas."),
    ("Calcetines deportivos compresión", "Calcetines deportivos de compresión graduada, fibras técnicas antibacteriales."),

    # Alimentos y bebidas
    ("Café tostado en grano gourmet", "Café tostado en grano gourmet 500g, origen único, tueste medio."),
    ("Bebida isotónica sin azúcar", "Bebida isotónica sin azúcar 600ml, sabor cítrico, adicionada con electrolitos."),
    ("Harina de almendra", "Harina de almendra 1kg, libre de gluten, molienda fina."),
    ("Chocolate artesano 80%", "Chocolate oscuro artesano 80% cacao, tableta 100g, origen Ecuador."),
    ("Conserva de atún premium", "Conserva de atún premium en aceite de oliva extra virgen, latas 160g."),

    # Químicos y pinturas
    ("Resina epóxica transparente", "Resina epóxica transparente para pisos autonivelantes, kit 10kg."),
    ("Pintura acrílica polvo anticorrosiva", "Pintura acrílica en polvo anticorrosiva para estructuras metálicas, color gris."),
    ("Detergente industrial enzimático", "Detergente industrial enzimático concentrado para lavandería, bidón 20L."),
    ("Sellador poliuretánico bicomponente", "Sellador poliuretánico bicomponente para juntas de dilatación, cartucho 600ml."),
    ("Removedor de óxido fosfatizante", "Removedor de óxido fosfatizante a base de ácido fosfórico, tambor 25L."),

    # Cosméticos y cuidado personal
    ("Serum facial vitamina C", "Serum facial antioxidante vitamina C al 15%, ácido hialurónico, frasco 30ml."),
    ("Protector solar mineral", "Protector solar mineral SPF50+, resistente al agua, 120ml."),
    ("Champú profesional keratina", "Champú profesional con keratina para cabellos tratados, envase 1L."),
    ("Crema hidratante corporal", "Crema hidratante corporal con manteca de karité y aloe vera, 400ml."),
    ("Aceite esencial lavanda", "Aceite esencial de lavanda 100% puro, botella ámbar 15ml."),

    # Agro / fertilizantes / pesticidas
    ("Fertilizante NPK control liberación", "Fertilizante granular NPK 14-14-14 de liberación controlada, saco 25kg."),
    ("Herbicida selectivo pos-emergente", "Herbicida selectivo pos-emergente para gramíneas, concentrado 1L."),
    ("Bioestimulante foliar algas", "Bioestimulante foliar a base de extracto de algas y aminoácidos, bidón 5L."),
    ("Insecticida biológico Bacillus", "Insecticida biológico con Bacillus thuringiensis, polvo mojable 1kg."),
    ("Trampa cromática adhesiva", "Trampa cromática adhesiva amarilla para monitoreo de plagas, paquete 50 unidades."),

    # Salud y dispositivos médicos
    ("Monitor de signos vitales", "Monitor de signos vitales multiparámetro, pantalla 12 pulgadas, batería interna."),
    ("Silla de ruedas plegable aluminio", "Silla de ruedas plegable aluminio, frenos asistente y asiento acolchado."),
    ("Termómetro infrarrojo clínico", "Termómetro infrarrojo clínico sin contacto, precisión ±0.2°C."),
    ("Guantes quirúrgicos estériles", "Guantes quirúrgicos estériles látex sin polvo, par embalado, talla 7.5."),
    ("Oxímetro de pulso portátil", "Oxímetro de pulso portátil con alarma de saturación y pantalla OLED."),

    # Maquinaria pesada / transporte
    ("Retroexcavadora compacta", "Retroexcavadora compacta diésel 70HP, cabina climatizada, cuchara 0.3m³."),
    ("Motor fueraborda 4 tiempos", "Motor fueraborda 4 tiempos 60HP, inyección electrónica, arranque eléctrico."),
    ("Sistema de riego pivote central", "Sistema de riego pivote central 400m, panel control y bomba eléctrica."),
    ("Carretilla elevadora eléctrica", "Carretilla elevadora eléctrica 2 toneladas, mástil triplex, batería litio."),
    ("Bomba centrífuga química", "Bomba centrífuga para productos químicos, caudal 25m³/h, carcasa acero inoxidable."),

    # Textil hogar / lifestyle
    ("Juego de sábanas microfibra", "Juego de sábanas microfibra hipoalergénica, cama queen, 4 piezas."),
    ("Alfombra lana natural", "Alfombra de lana natural tejida a mano, 2m x 3m, diseño geométrico."),
    ("Bolso de cuero artesanal", "Bolso de cuero artesanal con forro textil y herrajes metálicos, color café."),
    ("Gorro deportivo térmico", "Gorro deportivo térmico respirable con fibras sintéticas."),
    ("Bufanda de alpaca", "Bufanda tejida con fibra de alpaca, teñido natural, 180cm."),
]

CUSTOM_PRODUCTS_PRINCIPAL: List[Dict[str, str]] = [
    # Electrónica y computación
    {"descripcion": "Computadora portátil de 15 pulgadas con procesador Intel i7, 16GB RAM, 512GB SSD, pantalla Full HD", "hs6_correcto": "847130", "categoria": "Electrónica y computación"},
    {"descripcion": "Smartphone Android con pantalla táctil de 6.1 pulgadas, 128GB almacenamiento, cámara triple", "hs6_correcto": "851712", "categoria": "Electrónica y computación"},
    {"descripcion": "Tablet iPad de 10.9 pulgadas con procesador A14 Bionic, 256GB, WiFi y celular", "hs6_correcto": "847130", "categoria": "Electrónica y computación"},
    {"descripcion": "Monitor LED de 27 pulgadas, resolución 4K, HDMI y USB-C", "hs6_correcto": "852852", "categoria": "Electrónica y computación"},
    {"descripcion": "Impresora láser multifuncional, impresión, escaneo y copia, WiFi", "hs6_correcto": "844331", "categoria": "Electrónica y computación"},
    {"descripcion": "Router inalámbrico WiFi 6, velocidad hasta 1.2 Gbps, 4 puertos Ethernet", "hs6_correcto": "851762", "categoria": "Electrónica y computación"},
    {"descripcion": "Cámara digital DSLR, 24.2 megapíxeles, lente 18-55mm, grabación 4K", "hs6_correcto": "852580", "categoria": "Electrónica y computación"},
    {"descripcion": "Auriculares inalámbricos con cancelación de ruido, batería 30 horas", "hs6_correcto": "851830", "categoria": "Electrónica y computación"},
    {"descripcion": "Teclado mecánico gaming RGB, switches azules, retroiluminación", "hs6_correcto": "847160", "categoria": "Electrónica y computación"},
    {"descripcion": "Mouse inalámbrico óptico, 1600 DPI, batería recargable", "hs6_correcto": "847160", "categoria": "Electrónica y computación"},
    # Vehículos y transporte
    {"descripcion": "Automóvil eléctrico de 4 puertas, autonomía 400 km, carga rápida", "hs6_correcto": "870380", "categoria": "Vehículos y transporte"},
    {"descripcion": "Motocicleta de 250cc, motor monocilíndrico, frenos ABS", "hs6_correcto": "871150", "categoria": "Vehículos y transporte"},
    {"descripcion": "Bicicleta de montaña aro 29, cuadro de aluminio, 21 velocidades, sin motor", "hs6_correcto": "871200", "categoria": "Vehículos y transporte"},
    {"descripcion": "Scooter eléctrico plegable, velocidad máxima 25 km/h, batería de litio", "hs6_correcto": "871160", "categoria": "Vehículos y transporte"},
    {"descripcion": "Neumático para automóvil, medida 205/55R16, índice de velocidad H", "hs6_correcto": "401110", "categoria": "Vehículos y transporte"},
    {"descripcion": "Batería de automóvil 12V, 60Ah, ácido-plomo, libre mantenimiento", "hs6_correcto": "850710", "categoria": "Vehículos y transporte"},
    {"descripcion": "Faro LED para automóvil, luz blanca, 6000K, certificado DOT", "hs6_correcto": "851220", "categoria": "Vehículos y transporte"},
    # Hogar y electrodomésticos
    {"descripcion": "Refrigerador de dos puertas, 350 litros, tecnología inverter, acero inoxidable", "hs6_correcto": "841810", "categoria": "Hogar y electrodomésticos"},
    {"descripcion": "Lavadora automática de 8 kg, carga frontal, 15 programas, eficiencia A+++", "hs6_correcto": "845020", "categoria": "Hogar y electrodomésticos"},
    {"descripcion": "Microondas de 25 litros, potencia 800W, grill, plato giratorio", "hs6_correcto": "851650", "categoria": "Hogar y electrodomésticos"},
    {"descripcion": "Aspiradora robot inteligente, mapeo láser, control por app, 2.5 horas autonomía", "hs6_correcto": "850910", "categoria": "Hogar y electrodomésticos"},
    {"descripcion": "Aire acondicionado split de 12,000 BTU, eficiencia energética A++, WiFi", "hs6_correcto": "841510", "categoria": "Hogar y electrodomésticos"},
    {"descripcion": "Licuadora de 1.5 litros, motor 1000W, 6 velocidades, vaso de vidrio", "hs6_correcto": "850940", "categoria": "Hogar y electrodomésticos"},
    {"descripcion": "Plancha de vapor, potencia 2400W, suela cerámica, depósito 300ml", "hs6_correcto": "851640", "categoria": "Hogar y electrodomésticos"},
    # Textiles y ropa
    {"descripcion": "Camiseta de algodón 100%, talla M, color azul, manga corta", "hs6_correcto": "610910", "categoria": "Textiles y ropa"},
    {"descripcion": "Pantalón vaquero de mezclilla, talla 32, corte recto, color azul oscuro", "hs6_correcto": "620342", "categoria": "Textiles y ropa"},
    {"descripcion": "Zapatos deportivos de cuero sintético, talla 42, suela de goma, color blanco", "hs6_correcto": "640219", "categoria": "Textiles y ropa"},
    {"descripcion": "Chaqueta de invierno con relleno de plumas, talla L, impermeable", "hs6_correcto": "620113", "categoria": "Textiles y ropa"},
    {"descripcion": "Bolso de mano de cuero genuino, color negro, correa ajustable", "hs6_correcto": "420221", "categoria": "Textiles y ropa"},
    {"descripcion": "Gorra de béisbol de algodón, color rojo, logo bordado", "hs6_correcto": "650500", "categoria": "Textiles y ropa"},
    # Alimentos y bebidas
    {"descripcion": "Café en grano tostado de Colombia, 500g, tueste medio", "hs6_correcto": "090121", "categoria": "Alimentos y bebidas"},
    {"descripcion": "Aceite de oliva virgen extra, 1 litro, botella de vidrio, origen España", "hs6_correcto": "150910", "categoria": "Alimentos y bebidas"},
    {"descripcion": "Chocolate negro 70% cacao, 100g, tableta, sin azúcar añadido", "hs6_correcto": "180632", "categoria": "Alimentos y bebidas"},
    {"descripcion": "Miel de abeja natural, 500g, frasco de vidrio, origen local", "hs6_correcto": "040900", "categoria": "Alimentos y bebidas"},
    {"descripcion": "Té verde en bolsitas, 100 unidades, sabor natural, sin cafeína", "hs6_correcto": "090220", "categoria": "Alimentos y bebidas"},
    {"descripcion": "Vino tinto reserva, 750ml, botella de vidrio, origen Chile", "hs6_correcto": "220421", "categoria": "Alimentos y bebidas"},
    {"descripcion": "Cerveza artesanal IPA, 330ml, lata de aluminio, 6.5% alcohol", "hs6_correcto": "220300", "categoria": "Alimentos y bebidas"},
    # Construcción y herramientas
    {"descripcion": "Cemento Portland tipo I, bolsa de 50 kg, para construcción general", "hs6_correcto": "252329", "categoria": "Construcción y herramientas"},
    {"descripcion": "Ladrillo cerámico hueco, 12x20x40 cm, para muros estructurales", "hs6_correcto": "690410", "categoria": "Construcción y herramientas"},
    {"descripcion": "Taladro inalámbrico de 18V, batería de litio, 13mm chuck", "hs6_correcto": "846721", "categoria": "Construcción y herramientas"},
    {"descripcion": "Martillo de carpintero, mango de madera, cabeza de acero, 500g", "hs6_correcto": "820520", "categoria": "Construcción y herramientas"},
    {"descripcion": "Destornillador Phillips, mango ergonómico, punta magnética, 6mm", "hs6_correcto": "820540", "categoria": "Construcción y herramientas"},
    {"descripcion": "Cinta métrica de 5 metros, cinta de acero, carcasa de plástico", "hs6_correcto": "901780", "categoria": "Construcción y herramientas"},
    # Juguetes y entretenimiento
    {"descripcion": "Bloques de construcción plásticos para niños mayores de 6 años, 500 piezas", "hs6_correcto": "950300", "categoria": "Juguetes y entretenimiento"},
    {"descripcion": "Muñeca de tela para niñas, 30 cm, cabello rubio, vestido rosa", "hs6_correcto": "950300", "categoria": "Juguetes y entretenimiento"},
    {"descripcion": "Puzzle de 1000 piezas, imagen de paisaje, cartón reciclado", "hs6_correcto": "950300", "categoria": "Juguetes y entretenimiento"},
    {"descripcion": "Pelota de fútbol de cuero sintético, tamaño 5, peso reglamentario", "hs6_correcto": "950662", "categoria": "Juguetes y entretenimiento"},
    {"descripcion": "Juego de mesa familiar, 2-6 jugadores, edad 8+, cartón y plástico", "hs6_correcto": "950490", "categoria": "Juguetes y entretenimiento"},
    # Médico y farmacéutico
    {"descripcion": "Termómetro digital infrarrojo, medición sin contacto, pantalla LCD", "hs6_correcto": "902519", "categoria": "Médico y farmacéutico"},
    {"descripcion": "Mascarilla quirúrgica desechable, 3 capas, caja de 50 unidades", "hs6_correcto": "630790", "categoria": "Médico y farmacéutico"},
    {"descripcion": "Jeringa desechable estéril, 5ml, aguja 21G, uso médico", "hs6_correcto": "901831", "categoria": "Médico y farmacéutico"},
    {"descripcion": "Vendaje elástico de 10 cm x 4.5 m, algodón, color beige", "hs6_correcto": "300590", "categoria": "Médico y farmacéutico"},
    {"descripcion": "Guantes de látex desechables, talla M, caja de 100 unidades", "hs6_correcto": "401519", "categoria": "Médico y farmacéutico"},
    # Arte y oficina
    {"descripcion": "Lápiz de grafito HB, caja de 12 unidades, madera de cedro", "hs6_correcto": "960910", "categoria": "Arte y oficina"},
    {"descripcion": "Cuaderno de 200 hojas, rayado, tapa dura, espiral metálico", "hs6_correcto": "482010", "categoria": "Arte y oficina"},
    {"descripcion": "Bolígrafo de tinta azul, punta 0.7mm, cuerpo de plástico", "hs6_correcto": "960810", "categoria": "Arte y oficina"},
    {"descripcion": "Pintura acrílica blanca, 500ml, tubo de plástico, no tóxica", "hs6_correcto": "320910", "categoria": "Arte y oficina"},
    {"descripcion": "Pincel de cerdas naturales, número 8, mango de madera", "hs6_correcto": "960330", "categoria": "Arte y oficina"},
    # Industrial y maquinaria
    {"descripcion": "Motor eléctrico trifásico, 5 HP, 1800 RPM, carcasa de hierro fundido", "hs6_correcto": "850152", "categoria": "Industrial y maquinaria"},
    {"descripcion": "Bomba centrífuga para agua, 1 HP, acero inoxidable, conexión 2 pulgadas", "hs6_correcto": "841370", "categoria": "Industrial y maquinaria"},
    {"descripcion": "Válvula de compuerta de acero, 4 pulgadas, presión 150 PSI", "hs6_correcto": "848180", "categoria": "Industrial y maquinaria"},
    {"descripcion": "Cable eléctrico de cobre, 12 AWG, 3 conductores, aislamiento PVC", "hs6_correcto": "854449", "categoria": "Industrial y maquinaria"},
    {"descripcion": "Transformador de distribución, 25 kVA, 13.8kV/480V, aceite mineral", "hs6_correcto": "850421", "categoria": "Industrial y maquinaria"},
    # Agrícola y jardín
    {"descripcion": "Fertilizante NPK 15-15-15, bolsa de 25 kg, para uso agrícola", "hs6_correcto": "310520", "categoria": "Agrícola y jardín"},
    {"descripcion": "Semillas de tomate híbrido, 1000 semillas, variedad cherry", "hs6_correcto": "120930", "categoria": "Agrícola y jardín"},
    {"descripcion": "Manguera de riego de 20 metros, diámetro 1/2 pulgada, PVC", "hs6_correcto": "391739", "categoria": "Agrícola y jardín"},
    {"descripcion": "Pala de jardín con mango de madera, hoja de acero, 30 cm", "hs6_correcto": "820130", "categoria": "Agrícola y jardín"},
    # Lujo y accesorios
    {"descripcion": "Reloj de pulsera de acero inoxidable, movimiento automático, resistente al agua", "hs6_correcto": "910221", "categoria": "Lujo y accesorios"},
    {"descripcion": "Perfume de 100ml, fragancia floral, frasco de vidrio, origen Francia", "hs6_correcto": "330300", "categoria": "Lujo y accesorios"},
    {"descripcion": "Collar de plata esterlina 925, cadena de 45 cm, cierre de seguridad", "hs6_correcto": "711311", "categoria": "Lujo y accesorios"},
]

CUSTOM_PRODUCTS_ADICIONALES: List[Dict[str, str]] = [
    # Alimentos y bebidas
    {"descripcion": "Aceite de coco virgen extra", "hs6_correcto": "151319", "categoria": "Alimentos y bebidas"},
    {"descripcion": "Café instantáneo descafeinado", "hs6_correcto": "210111", "categoria": "Alimentos y bebidas"},
    {"descripcion": "Mermelada de fresa artesanal", "hs6_correcto": "200799", "categoria": "Alimentos y bebidas"},
    {"descripcion": "Cerveza sin alcohol", "hs6_correcto": "220291", "categoria": "Alimentos y bebidas"},
    {"descripcion": "Té negro Earl Grey", "hs6_correcto": "090240", "categoria": "Alimentos y bebidas"},
    {"descripcion": "Salsa de soja japonesa", "hs6_correcto": "210310", "categoria": "Alimentos y bebidas"},
    {"descripcion": "Vinagre balsámico", "hs6_correcto": "220900", "categoria": "Alimentos y bebidas"},
    {"descripcion": "Miel de eucalipto", "hs6_correcto": "040900", "categoria": "Alimentos y bebidas"},
    # Electrodomésticos y hogar
    {"descripcion": "Aspiradora sin cable", "hs6_correcto": "850910", "categoria": "Hogar y electrodomésticos"},
    {"descripcion": "Plancha de pelo", "hs6_correcto": "851632", "categoria": "Hogar y electrodomésticos"},
    {"descripcion": "Batidora de mano", "hs6_correcto": "850940", "categoria": "Hogar y electrodomésticos"},
    {"descripcion": "Tostadora", "hs6_correcto": "851672", "categoria": "Hogar y electrodomésticos"},
    {"descripcion": "Cafetera espresso manual", "hs6_correcto": "851671", "categoria": "Hogar y electrodomésticos"},
    {"descripcion": "Ventilador de techo con luz", "hs6_correcto": "841451", "categoria": "Hogar y electrodomésticos"},
    {"descripcion": "Purificador de aire HEPA", "hs6_correcto": "842139", "categoria": "Hogar y electrodomésticos"},
    # Automotriz y repuestos
    {"descripcion": "Filtro de aceite", "hs6_correcto": "842123", "categoria": "Automotriz y repuestos"},
    {"descripcion": "Pastillas de freno", "hs6_correcto": "870830", "categoria": "Automotriz y repuestos"},
    {"descripcion": "Aceite de motor sintético", "hs6_correcto": "271019", "categoria": "Automotriz y repuestos"},
    {"descripcion": "Bujía de encendido iridio", "hs6_correcto": "851110", "categoria": "Automotriz y repuestos"},
    {"descripcion": "Líquido refrigerante", "hs6_correcto": "382000", "categoria": "Automotriz y repuestos"},
    {"descripcion": "Bomba de combustible eléctrica", "hs6_correcto": "841330", "categoria": "Automotriz y repuestos"},
    # Textiles y calzado
    {"descripcion": "Chaqueta cuero genuino", "hs6_correcto": "420310", "categoria": "Textiles y ropa"},
    {"descripcion": "Zapatos seguridad, puntera acero", "hs6_correcto": "640340", "categoria": "Textiles y ropa"},
    {"descripcion": "Gorra algodón orgánico", "hs6_correcto": "650500", "categoria": "Textiles y ropa"},
    {"descripcion": "Bufanda lana merino", "hs6_correcto": "611710", "categoria": "Textiles y ropa"},
    {"descripcion": "Guantes de trabajo cuero", "hs6_correcto": "420329", "categoria": "Textiles y ropa"},
    {"descripcion": "Cinturón cuero genuino", "hs6_correcto": "420330", "categoria": "Textiles y ropa"},
    # Construcción y materiales
    {"descripcion": "Cemento Portland tipo II", "hs6_correcto": "252329", "categoria": "Construcción y herramientas"},
    {"descripcion": "Ladrillo refractario", "hs6_correcto": "690220", "categoria": "Construcción y herramientas"},
    {"descripcion": "Pintura acrílica 4L", "hs6_correcto": "320910", "categoria": "Construcción y herramientas"},
    {"descripcion": "Arena de río lavada", "hs6_correcto": "250590", "categoria": "Construcción y herramientas"},
    {"descripcion": "Varilla acero corrugado", "hs6_correcto": "721420", "categoria": "Construcción y herramientas"},
    {"descripcion": "Tubería PVC drenaje 4\"", "hs6_correcto": "391723", "categoria": "Construcción y herramientas"},
    # Electrónicos y gaming
    {"descripcion": "Consola de videojuegos portátil, pantalla 7 pulgadas, 128GB almacenamiento, WiFi", "hs6_correcto": "950450", "categoria": "Electrónica y computación"},
    {"descripcion": "Auriculares gaming con micrófono", "hs6_correcto": "851830", "categoria": "Electrónica y computación"},
    {"descripcion": "Teclado mecánico 60%", "hs6_correcto": "847160", "categoria": "Electrónica y computación"},
    {"descripcion": "Mouse gaming óptico", "hs6_correcto": "847160", "categoria": "Electrónica y computación"},
    {"descripcion": "Monitor gaming 144Hz", "hs6_correcto": "852852", "categoria": "Electrónica y computación"},
    {"descripcion": "Silla gaming ergonómica", "hs6_correcto": "940171", "categoria": "Electrónica y computación"},
    # Médico y farmacéutico
    {"descripcion": "Tensiómetro digital", "hs6_correcto": "901890", "categoria": "Médico y farmacéutico"},
    {"descripcion": "Termómetro infrarrojo", "hs6_correcto": "902519", "categoria": "Médico y farmacéutico"},
    {"descripcion": "Oxímetro digital", "hs6_correcto": "901819", "categoria": "Médico y farmacéutico"},
    {"descripcion": "Mascarilla N95", "hs6_correcto": "630790", "categoria": "Médico y farmacéutico"},
    {"descripcion": "Guantes de nitrilo", "hs6_correcto": "401519", "categoria": "Médico y farmacéutico"},
    {"descripcion": "Vendaje cohesivo", "hs6_correcto": "300590", "categoria": "Médico y farmacéutico"},
    # Arte y manualidades
    {"descripcion": "Pincel naturales N°12", "hs6_correcto": "960330", "categoria": "Arte y oficina"},
    {"descripcion": "Lápices de colores 72 unidades", "hs6_correcto": "960910", "categoria": "Arte y oficina"},
    {"descripcion": "Papel acuarela 300 g/m²", "hs6_correcto": "482390", "categoria": "Arte y oficina"},
    {"descripcion": "Pegamento termofusible", "hs6_correcto": "350610", "categoria": "Arte y oficina"},
    {"descripcion": "Cutter profesional", "hs6_correcto": "821193", "categoria": "Arte y oficina"},
    # Jardín y agricultura
    {"descripcion": "Semillas tomate cherry", "hs6_correcto": "120930", "categoria": "Agrícola y jardín"},
    {"descripcion": "Fertilizante NPK 8-3-5", "hs6_correcto": "310520", "categoria": "Agrícola y jardín"},
    {"descripcion": "Manguera riego expandible", "hs6_correcto": "391739", "categoria": "Agrícola y jardín"},
    {"descripcion": "Maceta terracota", "hs6_correcto": "691490", "categoria": "Agrícola y jardín"},
    {"descripcion": "Tijeras de podar", "hs6_correcto": "820150", "categoria": "Agrícola y jardín"},
    # Lujo y accesorios
    {"descripcion": "Reloj acero automático", "hs6_correcto": "910221", "categoria": "Lujo y accesorios"},
    {"descripcion": "Perfume masculino", "hs6_correcto": "330300", "categoria": "Lujo y accesorios"},
    {"descripcion": "Collar oro 18k", "hs6_correcto": "711319", "categoria": "Lujo y accesorios"},
    {"descripcion": "Gafas de sol polarizadas", "hs6_correcto": "900410", "categoria": "Lujo y accesorios"},
    # Herramientas industriales
    {"descripcion": "Taladro percutor inalámbrico", "hs6_correcto": "846721", "categoria": "Construcción y herramientas"},
    {"descripcion": "Sierra circular de mano", "hs6_correcto": "846722", "categoria": "Construcción y herramientas"},
    {"descripcion": "Nivel láser rotativo", "hs6_correcto": "901530", "categoria": "Construcción y herramientas"},
    {"descripcion": "Multímetro digital", "hs6_correcto": "903031", "categoria": "Construcción y herramientas"},
    {"descripcion": "Destornillador eléctrico", "hs6_correcto": "846729", "categoria": "Construcción y herramientas"},
]

CUSTOM_PRODUCTS_V2: List[Dict[str, str]] = [
    {"descripcion": "Cepillo de dientes manual, cerdas suaves, mango plástico", "hs6_correcto": "960321", "categoria": "Higiene"},
    {"descripcion": "Pasta dental fluorada 120g", "hs6_correcto": "330610", "categoria": "Higiene"},
    {"descripcion": "Jabón líquido antibacterial 500ml", "hs6_correcto": "340130", "categoria": "Limpieza"},
    {"descripcion": "Detergente en polvo para ropa 1kg", "hs6_correcto": "340220", "categoria": "Limpieza"},
    {"descripcion": "Esponja de cocina doble capa", "hs6_correcto": "392410", "categoria": "Hogar"},
    {"descripcion": "Olla de acero inoxidable 20cm", "hs6_correcto": "732393", "categoria": "Cocina"},
    {"descripcion": "Sartén antiadherente aluminio 24cm", "hs6_correcto": "761510", "categoria": "Cocina"},
    {"descripcion": "Plato de cerámica blanco 25cm", "hs6_correcto": "691110", "categoria": "Cocina"},
    {"descripcion": "Vaso de vidrio templado 300ml", "hs6_correcto": "701349", "categoria": "Cocina"},
    {"descripcion": "Cuchillo de cocina acero inoxidable", "hs6_correcto": "821192", "categoria": "Cocina"},
    {"descripcion": "Tijeras multiusos 20cm", "hs6_correcto": "821300", "categoria": "Hogar"},
    {"descripcion": "Papel higiénico doble hoja 12 rollos", "hs6_correcto": "481810", "categoria": "Hogar"},
    {"descripcion": "Toallas de papel 6 rollos", "hs6_correcto": "481820", "categoria": "Hogar"},
    {"descripcion": "Botella deportiva plástico 750ml", "hs6_correcto": "392330", "categoria": "Deportes"},
    {"descripcion": "Balón de baloncesto tamaño 7", "hs6_correcto": "950662", "categoria": "Deportes"},
    {"descripcion": "Rodillera deportiva neopreno", "hs6_correcto": "630790", "categoria": "Deportes"},
    {"descripcion": "Linterna LED mano, batería AA", "hs6_correcto": "851310", "categoria": "Iluminación"},
    {"descripcion": "Bombillo LED E27 12W", "hs6_correcto": "854370", "categoria": "Iluminación"},
    {"descripcion": "Cortina de baño PVC 180x200cm", "hs6_correcto": "392490", "categoria": "Baño"},
    {"descripcion": "Tapete de baño antideslizante", "hs6_correcto": "570500", "categoria": "Baño"},
    {"descripcion": "Estante metálico organizador", "hs6_correcto": "732399", "categoria": "Hogar"},
    {"descripcion": "Caja plástica organizadora 20L", "hs6_correcto": "392310", "categoria": "Hogar"},
    {"descripcion": "Paraguas plegable tela poliéster", "hs6_correcto": "660191", "categoria": "Accesorios"},
    {"descripcion": "Mochila nylon 20L, cremalleras", "hs6_correcto": "420292", "categoria": "Accesorios"},
    {"descripcion": "Cinturón sintético hebilla metálica", "hs6_correcto": "420321", "categoria": "Ropa/Accesorios"},
    {"descripcion": "Pulsera acero inoxidable", "hs6_correcto": "711711", "categoria": "Accesorios"},
    {"descripcion": "Sombrero de paja natural", "hs6_correcto": "650400", "categoria": "Ropa/Accesorios"},
    {"descripcion": "Jarrón decorativo vidrio 30cm", "hs6_correcto": "701399", "categoria": "Decoración"},
    {"descripcion": "Portarretratos madera 20x25cm", "hs6_correcto": "441400", "categoria": "Decoración"},
    {"descripcion": "Pintura en aerosol color negro 400ml", "hs6_correcto": "320820", "categoria": "Pinturas"},
    {"descripcion": "Adhesivo instantáneo cianoacrilato", "hs6_correcto": "350610", "categoria": "Adhesivos"},
    {"descripcion": "Cinta adhesiva transparente 50m", "hs6_correcto": "391910", "categoria": "Oficina"},
    {"descripcion": "Grapadora metálica de escritorio", "hs6_correcto": "847290", "categoria": "Oficina"},
    {"descripcion": "Perforadora de papel 2 huecos", "hs6_correcto": "847290", "categoria": "Oficina"},
    {"descripcion": "Carpetas plásticas tamaño carta", "hs6_correcto": "482030", "categoria": "Oficina"},
    {"descripcion": "Lupa de mano 3x", "hs6_correcto": "901380", "categoria": "Precisión"},
    {"descripcion": "Termo acero inoxidable 1L", "hs6_correcto": "732393", "categoria": "Hogar"},
    {"descripcion": "Cuerda de salto algodón", "hs6_correcto": "560749", "categoria": "Deportes"},
    {"descripcion": "Espátula de cocina silicona", "hs6_correcto": "392410", "categoria": "Cocina"},
    {"descripcion": "Colador metálico de malla fina", "hs6_correcto": "732410", "categoria": "Cocina"},
    {"descripcion": "Bandeja horneado aluminio", "hs6_correcto": "761510", "categoria": "Cocina"},
    {"descripcion": "Cierre (cremallera) nylon 40cm", "hs6_correcto": "960720", "categoria": "Mercería"},
    {"descripcion": "Agujas de coser acero", "hs6_correcto": "731990", "categoria": "Mercería"},
    {"descripcion": "Hilo poliéster 100m", "hs6_correcto": "550810", "categoria": "Mercería"},
    {"descripcion": "Lámpara de escritorio LED", "hs6_correcto": "940520", "categoria": "Iluminación"},
    {"descripcion": "Mesa plegable de plástico", "hs6_correcto": "940370", "categoria": "Muebles"},
    {"descripcion": "Silla para comedor madera", "hs6_correcto": "940161", "categoria": "Muebles"},
    {"descripcion": "Caja de herramientas metálica", "hs6_correcto": "732690", "categoria": "Herramientas"},
    {"descripcion": "Llave inglesa ajustable 8\"", "hs6_correcto": "820412", "categoria": "Herramientas"},
    {"descripcion": "Pegamento escolar barra 20g", "hs6_correcto": "350610", "categoria": "Oficina"},
]


def get_session() -> requests.Session:
    """Crear sesión HTTP con encabezados apropiados."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


def login(session: requests.Session) -> None:
    """Realizar login y almacenar el token en los encabezados."""
    response = session.post(
        f"{BASE_URL}/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        timeout=15,
    )
    if response.status_code != 200:
        raise RuntimeError(f"Login fallido: {response.status_code} - {response.text}")
    data = response.json()
    token = data.get("details", {}).get("token")
    if not token:
        raise RuntimeError("La respuesta de login no contiene token JWT.")
    session.headers.update({"Authorization": f"Bearer {token}"})


def create_case(session: requests.Session, title: str, description: str) -> int:
    """Crear un caso y devolver su ID."""
    response = session.post(
        f"{BASE_URL}/cases",
        json={"product_title": title, "product_desc": description},
        timeout=15,
    )
    if response.status_code != 201:
        raise RuntimeError(f"No se pudo crear el caso: {response.status_code} - {response.text}")
    return response.json().get("details", {}).get("case_id")


def classify_case(session: requests.Session, case_id: int) -> Dict[str, Any]:
    """Ejecutar la clasificación para un caso."""
    response = session.post(f"{BASE_URL}/api/v1/classify/{case_id}", json={}, timeout=30)
    data = response.json()
    if response.status_code != 200:
        raise RuntimeError(f"Error clasificando caso {case_id}: {response.status_code} - {data}")
    return data.get("details", data)


def ensure_outputs_dir() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


def run_massive_test() -> Dict[str, Any]:
    session = get_session()
    login(session)

    results: List[Dict[str, Any]] = []
    errors = 0

    for idx, (title, description) in enumerate(PRODUCT_DESCRIPTIONS, start=1):
        print(f"[{idx:02d}/50] Clasificando: {description[:60]}...")
        try:
            case_id = create_case(session, title, description)
            start_t = time.perf_counter()
            classify = classify_case(session, case_id)
            elapsed = time.perf_counter() - start_t

            rationale = classify.get("rationale", {}) or {}
            results.append(
                {
                    "index": idx,
                    "case_id": case_id,
                    "description": description,
                    "hs": classify.get("national_code") or classify.get("hs"),
                    "title": classify.get("title"),
                    "confidence": float(classify.get("confidence", 0.0) or 0.0),
                    "chapter_coherence": rationale.get("chapter_coherence"),
                    "suspect_code": rationale.get("suspect_code"),
                    "requires_review": rationale.get("requires_review"),
                    "response_time": elapsed,
                    "rationale": rationale,
                }
            )
        except Exception as exc:
            errors += 1
            results.append(
                {
                    "index": idx,
                    "case_id": None,
                    "description": description,
                    "hs": None,
                    "title": None,
                    "confidence": 0.0,
                    "chapter_coherence": "ERROR",
                    "suspect_code": None,
                    "requires_review": True,
                    "response_time": None,
                    "error": str(exc),
                }
            )
            print(f"  [ADVERTENCIA] Error clasificando: {exc}")

    summary = build_summary(results, errors)
    ensure_outputs_dir()
    save_reports(results, summary)
    print_summary(summary)
    return summary


def build_summary(results: List[Dict[str, Any]], errors: int) -> Dict[str, Any]:
    total = len(results)
    success_items = [r for r in results if r.get("hs")]
    confidences = [r["confidence"] for r in success_items if r["confidence"] is not None]
    response_times = [r["response_time"] for r in success_items if r["response_time"] is not None]
    suspect_count = sum(1 for r in success_items if r.get("suspect_code"))
    review_count = sum(1 for r in success_items if r.get("requires_review"))

    hs_counter = Counter(r["hs"] for r in success_items if r.get("hs"))

    avg_confidence = statistics.mean(confidences) if confidences else 0.0
    min_confidence = min(confidences) if confidences else 0.0
    max_confidence = max(confidences) if confidences else 0.0
    avg_response = statistics.mean(response_times) if response_times else 0.0

    suspicious_ratio = suspect_count / total if total else 0.0
    review_ratio = review_count / total if total else 0.0

    top_hs = [{"hs": hs, "count": count} for hs, count in hs_counter.most_common(5)]

    suspect_counts = {
        hs: count for hs, count in hs_counter.items() if hs in {
            "8471300000", "1905000000", "0901110000", "7001000000",
            "7207110000", "8711100000", "2201100000"
        }
    }

    summary = {
        "generated_at": datetime.utcnow().isoformat(),
        "summary": {
            "total_products": total,
            "success_count": len(success_items),
            "errors": errors,
            "avg_confidence": round(avg_confidence, 4),
            "min_confidence": round(min_confidence, 4),
            "max_confidence": round(max_confidence, 4),
            "suspicious_ratio": round(suspicious_ratio, 4),
            "review_ratio": round(review_ratio, 4),
            "avg_response_time": round(avg_response, 4),
            "top_hs_codes": top_hs,
            "suspect_counts": suspect_counts,
        },
        "cases": results,
    }
    return summary


def save_reports(results: List[Dict[str, Any]], summary: Dict[str, Any]) -> None:
    REPORT_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    # CSV de apoyo (opcional)
    try:
        import csv

        with CSV_PATH.open("w", encoding="utf-8", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(
                [
                    "index",
                    "case_id",
                    "description",
                    "hs",
                    "confidence",
                    "chapter_coherence",
                    "suspect_code",
                    "requires_review",
                    "response_time",
                    "error",
                ]
            )
            for row in results:
                writer.writerow(
                    [
                        row.get("index"),
                        row.get("case_id"),
                        row.get("description"),
                        row.get("hs"),
                        row.get("confidence"),
                        row.get("chapter_coherence"),
                        row.get("suspect_code"),
                        row.get("requires_review"),
                        row.get("response_time"),
                        row.get("error"),
                    ]
                )
    except Exception as exc:
        print(f"[ADVERTENCIA] No se pudo generar CSV: {exc}")


def print_summary(summary: Dict[str, Any]) -> None:
    data = summary["summary"]
    print("\n=== Resumen Test Masivo (50 productos) ===")
    print(f"Total productos       : {data['total_products']}")
    print(f"Clasificaciones OK    : {data['success_count']}")
    print(f"Errores               : {data['errors']}")
    print(f"Confianza promedio    : {data['avg_confidence']:.3f}")
    print(f"Confianza mínima      : {data['min_confidence']:.3f}")
    print(f"Confianza máxima      : {data['max_confidence']:.3f}")
    print(f"Casos sospechosos (%) : {data['suspicious_ratio']*100:.1f}%")
    print(f"Requieren revisión (%) : {data['review_ratio']*100:.1f}%")
    print(f"Tiempo resp. promedio : {data['avg_response_time']:.3f} s")
    print("Top 5 códigos HS      :")
    for item in data["top_hs_codes"]:
        print(f"  - {item['hs']}: {item['count']} casos")
    print(f"\nReporte JSON guardado en: {REPORT_PATH}")
    if CSV_PATH.exists():
        print(f"Reporte CSV guardado en : {CSV_PATH}")


def normalize_hs6(value: Any) -> str | None:
    """Normaliza un código HS a sus primeros 6 dígitos numéricos."""
    if not value:
        return None
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if not digits:
        return None
    return digits[:6]


def build_trace_excerpt(rationale: Dict[str, Any]) -> str:
    """Genera una cadena corta con la decisión y banderas relevantes."""
    if not isinstance(rationale, dict):
        return "Sin rationale"
    parts: List[str] = []
    decision = rationale.get("decision")
    if decision:
        parts.append(decision)
    chapter = rationale.get("chapter_coherence")
    if chapter:
        parts.append(f"chapter={chapter}")
    validations = rationale.get("validations")
    if validations:
        parts.append("validations=" + ", ".join(validations))
    review_notes = rationale.get("review_notes")
    if review_notes:
        parts.append("review_notes=" + ", ".join(review_notes))
    return " | ".join(parts) if parts else "Sin trazas"


def evaluate_datasets(
    session: requests.Session,
    dataset_groups: List[Tuple[str, List[Dict[str, str]]]],
    label: str,
) -> Dict[str, Any]:
    """Ejecuta la evaluación con ground truth para los grupos especificados."""
    total_items = 0
    correct = 0
    confidences: List[float] = []
    errores: List[Dict[str, Any]] = []
    aciertos: List[Dict[str, Any]] = []
    chapter_summary: Dict[str, Dict[str, Any]] = {}
    category_summary: Dict[str, Dict[str, Any]] = {}
    monopolies_counter: Counter[str] = Counter()

    for group_name, products in dataset_groups:
        for idx, product in enumerate(products, start=1):
            total_items += 1
            descripcion = product["descripcion"]
            hs6_correcto = normalize_hs6(product["hs6_correcto"])
            categoria = product["categoria"]
            expected_chapter = hs6_correcto[:2] if hs6_correcto else "--"
            title = f"{group_name} #{idx}"
            confidence = 0.0
            hs6_predicho = None
            trace_resumido = "Sin datos"
            diferencia_capitulo = ""

            try:
                case_id = create_case(session, title, descripcion)
                classify = classify_case(session, case_id)
                rationale = classify.get("rationale", {}) or {}
                hs6_predicho = normalize_hs6(
                    classify.get("hs6")
                    or classify.get("national_code")
                    or classify.get("hs")
                )
                confidence = float(classify.get("confidence", 0.0) or 0.0)
                trace_resumido = build_trace_excerpt(rationale)
            except Exception as exc:
                trace_resumido = f"ERROR: {exc}"

            confidences.append(confidence)
            predicted_chapter = hs6_predicho[:2] if hs6_predicho else "--"
            diferencia_capitulo = f"{expected_chapter} vs {predicted_chapter}"
            is_correct = bool(hs6_predicho and hs6_predicho == hs6_correcto)

            chapter_entry = chapter_summary.setdefault(
                expected_chapter,
                {"chapter": expected_chapter, "total": 0, "aciertos": 0, "errores": 0, "predicciones": Counter()},
            )
            chapter_entry["total"] += 1
            chapter_entry["predicciones"][predicted_chapter] += 1
            if is_correct:
                chapter_entry["aciertos"] += 1
            else:
                chapter_entry["errores"] += 1

            category_entry = category_summary.setdefault(
                categoria, {"categoria": categoria, "total": 0, "aciertos": 0, "errores": 0}
            )
            category_entry["total"] += 1
            if is_correct:
                category_entry["aciertos"] += 1
            else:
                category_entry["errores"] += 1

            if is_correct:
                correct += 1
                aciertos.append(
                    {
                        "descripcion": descripcion,
                        "hs6_correcto": hs6_correcto,
                        "hs6_predicho": hs6_predicho,
                        "confidence": round(confidence, 4),
                        "categoria": categoria,
                    }
                )
            else:
                if hs6_predicho:
                    monopolies_counter[hs6_predicho] += 1
                errores.append(
                    {
                        "descripcion": descripcion,
                        "hs6_correcto": hs6_correcto,
                        "hs6_predicho": hs6_predicho or "SIN_PREDICCION",
                        "confidence": round(confidence, 4),
                        "diferencia_capitulo": diferencia_capitulo,
                        "trace_resumido": trace_resumido,
                        "categoria": categoria,
                    }
                )

    avg_confidence = statistics.mean(confidences) if confidences else 0.0
    resumen_por_capitulo = []
    for data in chapter_summary.values():
        preds = [
            {"chapter": chapter, "count": count}
            for chapter, count in data["predicciones"].most_common()
        ]
        resumen_por_capitulo.append(
            {
                "chapter": data["chapter"],
                "total": data["total"],
                "aciertos": data["aciertos"],
                "errores": data["errores"],
                "predicciones": preds,
            }
        )
    resumen_por_capitulo.sort(key=lambda x: x["chapter"])

    fallos_por_categoria = []
    for data in category_summary.values():
        accuracy = data["aciertos"] / data["total"] if data["total"] else 0.0
        fallos_por_categoria.append(
            {
                "categoria": data["categoria"],
                "total": data["total"],
                "errores": data["errores"],
                "aciertos": data["aciertos"],
                "accuracy": round(accuracy, 4),
            }
        )
    fallos_por_categoria.sort(key=lambda x: x["categoria"])

    monopolios_predichos = [
        {"hs6": hs, "errores": count} for hs, count in monopolies_counter.most_common(5)
    ]

    report = {
        "generated_at": datetime.utcnow().isoformat(),
        "total_items": total_items,
        "global_accuracy": round(correct / total_items, 4) if total_items else 0.0,
        "avg_confidence": round(avg_confidence, 4),
        "errores": errores,
        "aciertos": aciertos,
        "resumen_por_capitulo": resumen_por_capitulo,
        "monopolios_predichos": monopolios_predichos,
        "fallos_por_categoria": fallos_por_categoria,
        "label": label,
    }
    return report


def evaluate_custom_products(session: requests.Session) -> Dict[str, Any]:
    datasets = [
        ("Lista principal", CUSTOM_PRODUCTS_PRINCIPAL),
        ("Lista adicional", CUSTOM_PRODUCTS_ADICIONALES),
    ]
    return evaluate_datasets(session, datasets, label="custom_products")


def evaluate_custom_products_v2(session: requests.Session) -> Dict[str, Any]:
    datasets = [("Lista V2", CUSTOM_PRODUCTS_V2)]
    return evaluate_datasets(session, datasets, label="custom_products_v2")


def run_custom_evaluations() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Ejecuta ambas evaluaciones personalizadas reutilizando una sesión."""
    session = get_session()
    login(session)
    report_v1 = evaluate_custom_products(session)
    report_v2 = evaluate_custom_products_v2(session)
    return report_v1, report_v2


def print_custom_suggestions(*reports: Dict[str, Any]) -> None:
    """Imprime sugerencias automáticas basadas en uno o más reportes."""
    suggestions: List[str] = []
    for report in reports:
        if not report:
            continue
        label = report.get("label", "custom_products")
        monopolios = report.get("monopolios_predichos") or []
        if monopolios and monopolios[0]["hs6"] == "847130":
            suggestions.append(f"[{label}] Penalizar HS 847130 cuando las descripciones mencionen textiles, alimentos o cosméticos.")
        for entry in report.get("fallos_por_categoria", []):
            categoria = entry["categoria"].lower()
            if categoria.startswith("textiles") and entry["errores"] >= 2:
                suggestions.append(f"[{label}] Refinar keywords para textiles (capítulos 61/62) y reforzar detección de materiales blandos.")
            if categoria.startswith("alimentos") and entry["errores"] >= 2:
                suggestions.append(f"[{label}] Agregar reglas RGI específicas para alimentos procesados y bebidas.")
            if categoria.startswith("agrícola") and entry["errores"] >= 2:
                suggestions.append(f"[{label}] Afinar reglas para semillas/fertilizantes (capítulos 12/31) y penalizar capítulos metálicos.")
            if categoria.startswith("hogar") and entry["errores"] >= 2:
                suggestions.append(f"[{label}] Crear reglas para menaje de cocina y organización hogar (capítulos 39/69/73/94).")
        for chapter_entry in report.get("resumen_por_capitulo", []):
            chapter = chapter_entry["chapter"]
            if chapter == "33" and chapter_entry["errores"] >= 1:
                suggestions.append(f"[{label}] Añadir fallback específico para perfumes y cosméticos (capítulo 33).")
            if chapter == "90" and chapter_entry["errores"] >= 1:
                suggestions.append(f"[{label}] Agregar reglas RGI para instrumentos de precisión (capítulo 90).")
            if chapter == "95" and chapter_entry["errores"] >= 1:
                suggestions.append(f"[{label}] Fortalecer detección de juguetes/equipos deportivos (capítulo 95).")
            if chapter == "69" and chapter_entry["errores"] >= 1:
                suggestions.append(f"[{label}] Incorporar reglas para recipientes cerámicos y decorativos (capítulo 69).")
    if suggestions:
        print("\nSugerencias automáticas basadas en las evaluaciones personalizadas:")
        for suggestion in suggestions:
            print(f"- {suggestion}")
    else:
        print("\nSugerencias automáticas: No se detectaron patrones críticos.")

if __name__ == "__main__":
    try:
        summary = run_massive_test()
        try:
            custom_report, custom_report_v2 = run_custom_evaluations()
            summary["custom_products"] = custom_report
            summary["custom_products_v2"] = custom_report_v2
            save_reports(summary.get("cases", []), summary)
            for report in (custom_report, custom_report_v2):
                label = report.get("label", "custom_products")
                print(f"\n=== Resumen {label} ===")
                print(f"Total evaluados       : {report['total_items']}")
                print(f"Accuracy global       : {report['global_accuracy']*100:.2f}%")
                print(f"Confianza promedio    : {report['avg_confidence']}")
                print(f"Errores detectados    : {len(report['errores'])}")
            print_custom_suggestions(custom_report, custom_report_v2)
        except Exception as exc:
            print(f"[ADVERTENCIA] Evaluación personalizada falló: {exc}")
        sys.exit(0 if summary["summary"]["errors"] == 0 else 1)
    except Exception as exc:
        print(f"\n[ERROR] Error general en la prueba masiva: {exc}")
        sys.exit(1)

