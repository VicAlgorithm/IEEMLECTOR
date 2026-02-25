"""
Extractores de Pares Crudos — FLUJO 3
======================================
Extrae datos crudos (ID + contenidos) de las tablas de Azure
para enviarlos al validador de IA (FLUJO 4).

Cada extractor retorna una lista de dicts:
  [{"id": "94", "contenidos": ["Setecientos", "700", ...]}, ...]
"""

import re
from typing import List, Dict
from limpieza import limpiar_texto_ligero


def extraer_pares_tabla_1(tabla_azure) -> List[Dict]:
    """
    Extrae pares crudos de la Tabla 1 (Boletas, Personas, Representantes, Total).
    Divide la tabla en 4 secciones verticales por coordenadas Y.
    """
    if not tabla_azure.bounding_regions:
        return []

    poly = tabla_azure.bounding_regions[0].polygon
    y_min = min(poly[1], poly[3], poly[5], poly[7])
    y_max = max(poly[1], poly[3], poly[5], poly[7])
    alto_total = y_max - y_min

    # 4 secciones verticales (25% cada una)
    secciones = []
    for i in range(4):
        inicio = y_min + (alto_total * (i / 4))
        fin = y_min + (alto_total * ((i + 1) / 4))
        secciones.append({
            "inicio": inicio, "fin": fin,
            "id": "", "contenidos": []
        })

    ids_esperados = ["94", "96", "97", "98"]

    for cell in tabla_azure.cells:
        if not cell.bounding_regions:
            continue

        # Calcular centro Y de la celda
        c_poly = cell.bounding_regions[0].polygon
        c_ymin = min(c_poly[1], c_poly[3], c_poly[5], c_poly[7])
        c_ymax = max(c_poly[1], c_poly[3], c_poly[5], c_poly[7])
        c_y_center = (c_ymin + c_ymax) / 2

        # Determinar a qué sección pertenece
        idx_seccion = -1
        for i, sec in enumerate(secciones):
            if sec["inicio"] <= c_y_center < sec["fin"]:
                idx_seccion = i
                break

        if idx_seccion == -1:
            continue

        contenido = cell.content.replace('\n', ' ').strip()
        if not contenido:
            continue

        contenido_limpio = limpiar_texto_ligero(contenido)
        if not contenido_limpio:
            continue

        # Si es columna 0, intentar extraer ID numérico
        if cell.column_index == 0:
            numeros = re.findall(r'\b(9[4-8])\b', contenido_limpio)
            if numeros:
                secciones[idx_seccion]["id"] = numeros[0]

        # Agregar contenido a la sección (TODAS las columnas)
        secciones[idx_seccion]["contenidos"].append(contenido_limpio)

    # Construir pares de salida
    pares = []
    for i, sec in enumerate(secciones):
        id_campo = sec["id"] if sec["id"] else (
            ids_esperados[i] if i < len(ids_esperados) else f"T1_{i}"
        )
        if sec["contenidos"]:
            pares.append({
                "id": id_campo,
                "contenidos": sec["contenidos"]
            })

    return pares


def extraer_pares_tabla_2(tabla_azure) -> List[Dict]:
    """
    Extrae pares crudos de la Tabla 2 (Resultados por Partido).
    Organiza celdas por fila y aplica corrección OCR para IDs.
    """
    celdas_por_fila = {}
    for cell in tabla_azure.cells:
        r = cell.row_index
        if r not in celdas_por_fila:
            celdas_por_fila[r] = {}
        celdas_por_fila[r][cell.column_index] = cell.content

    pares = []

    for r in sorted(celdas_por_fila.keys()):
        fila = celdas_por_fila[r]
        if not fila:
            continue

        contenidos = []
        id_campo = ""

        for col in sorted(fila.keys()):
            texto = limpiar_texto_ligero(fila[col])
            if texto:
                contenidos.append(texto)

                # Intentar extraer ID de las primeras columnas
                if col < tabla_azure.column_count / 2 and not id_campo:
                    # Corrección OCR: letras confundidas con dígitos
                    texto_corregido = texto
                    ocr_fixes = {'O': '0', 'o': '0', 'S': '5', 's': '5',
                                 'I': '1', 'l': '1', 'Z': '2', 'z': '2',
                                 'B': '8', 'G': '6', 'g': '9'}
                    for letra, digito in ocr_fixes.items():
                        texto_corregido = texto_corregido.replace(letra, digito)

                    numeros = re.findall(r'\d+', texto_corregido)
                    if numeros:
                        id_campo = numeros[0].zfill(2)

        if id_campo and contenidos:
            pares.append({
                "id": id_campo,
                "contenidos": contenidos
            })

    return pares


def extraer_pares_tabla_3(tabla_azure) -> List[Dict]:
    """
    Extrae pares crudos de la Tabla 3 (Total de Votos Sacados).
    Siempre retorna ID "99" con todos los contenidos.
    """
    contenidos = []

    for cell in tabla_azure.cells:
        texto = limpiar_texto_ligero(cell.content)
        if texto:
            contenidos.append(texto)

    if contenidos:
        return [{"id": "99", "contenidos": contenidos}]

    return []
