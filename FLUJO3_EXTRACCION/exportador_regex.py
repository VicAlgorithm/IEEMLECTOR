"""
Procesamiento con Regex — FLUJO 3 (modo sin IA)
=================================================
Extrae datos de las tablas usando solo regex y patrones.
Este es el modo original que no requiere Azure OpenAI.
Solo extrae dígitos (ignora texto con letra).
"""

import re
from typing import List, Dict
from limpieza import limpiar_texto


def procesar_tabla_1(tabla_azure) -> str:
    """
    Procesa la TABLA 1 (Boletas, Personas, Representantes, Total).
    Divide la tabla verticalmente en 4 secciones y extrae dígitos.
    """
    if not tabla_azure.bounding_regions:
        return ""

    poly = tabla_azure.bounding_regions[0].polygon
    y_min = min(poly[1], poly[3], poly[5], poly[7])
    y_max = max(poly[1], poly[3], poly[5], poly[7])
    alto_total = y_max - y_min

    print(f"\n[DEBUG TABLA 1] Columnas detectadas por Azure: {tabla_azure.column_count}")

    # 4 secciones (25% cada una)
    secciones = []
    for i in range(4):
        inicio = y_min + (alto_total * (i / 4))
        fin = y_min + (alto_total * ((i + 1) / 4))
        secciones.append({"inicio": inicio, "fin": fin, "texto_izq": "", "texto_der": ""})

    # Clasificar celdas en secciones
    for cell in tabla_azure.cells:
        contenido_raw = cell.content.replace('\n', ' ')
        print(f"[DEBUG CELDA] Fila: {cell.row_index}, Col: {cell.column_index}, Texto: '{contenido_raw}'")

        if not cell.bounding_regions:
            continue
        c_poly = cell.bounding_regions[0].polygon
        c_ymin = min(c_poly[1], c_poly[3], c_poly[5], c_poly[7])
        c_ymax = max(c_poly[1], c_poly[3], c_poly[5], c_poly[7])
        c_y_center = (c_ymin + c_ymax) / 2

        idx_seccion = -1
        for i, sec in enumerate(secciones):
            if sec["inicio"] <= c_y_center < sec["fin"]:
                idx_seccion = i
                break

        if idx_seccion == -1:
            continue

        texto = limpiar_texto(cell.content)
        if not texto:
            continue

        idx_col = cell.column_index
        texto_limpio = texto.strip()

        if idx_col == 0:
            numeros = re.findall(r'\b(9[4-8])\b', texto_limpio)
            if numeros:
                secciones[idx_seccion]["texto_izq"] = numeros[0]

        elif idx_col >= 1:
            texto_valor = re.sub(r'\(\s*Con\s*n[úu]mero\s*\)', '', texto_limpio, flags=re.IGNORECASE)
            texto_valor = re.sub(r'\(\s*\d+\s*\)', '', texto_valor)

            nums = re.findall(r'\d+', texto_valor)
            if nums:
                secciones[idx_seccion]["texto_der"] = nums[-1]

    # Formatear salida
    lineas = []
    ids_esperados = ["94", "96", "97", "98"]

    for i, sec in enumerate(secciones):
        concepto = sec["texto_izq"].strip()
        valor = sec["texto_der"].strip()

        if concepto and valor:
            lineas.append(f"{concepto} : {valor}")
        elif valor and i < len(ids_esperados):
            lineas.append(f"{ids_esperados[i]} : {valor}")

    return "\n".join(lineas)


def procesar_tabla_2(tabla_azure) -> str:
    """
    Procesa la TABLA 2 (Resultados por Partido).
    Solo extrae dígitos de cada fila.
    """
    lineas = []

    celdas_por_fila = {}
    for cell in tabla_azure.cells:
        r = cell.row_index
        if r not in celdas_por_fila:
            celdas_por_fila[r] = {}
        celdas_por_fila[r][cell.column_index] = cell.content

    for r in sorted(celdas_por_fila.keys()):
        fila = celdas_por_fila[r]
        if not fila:
            continue

        contenidos_limpios = {col: limpiar_texto(c)
                             for col, c in fila.items() if limpiar_texto(c)}

        if not contenidos_limpios:
            continue

        indices = sorted(contenidos_limpios.keys())
        columnas_totales = tabla_azure.column_count

        texto_izq = ""
        texto_der = ""

        for col in indices:
            if col < columnas_totales / 2:
                val = contenidos_limpios[col]
                if val:
                    numeros = re.findall(r'\d+', val)
                    if numeros:
                        texto_izq = numeros[0]
                    break

        candidate_val_col = indices[-1]
        if candidate_val_col >= columnas_totales / 2:
            texto_der = contenidos_limpios[candidate_val_col]
            if texto_der:
                votos_nums = re.findall(r'\d+', texto_der)
                if votos_nums:
                    texto_der = votos_nums[-1]
                else:
                    texto_der = ""

        if texto_izq and texto_der:
            lineas.append(f"{texto_izq} : {texto_der}")

    return "\n".join(lineas)


def procesar_tabla_3(tabla_azure) -> str:
    """
    Procesa la TABLA 3 (Total de Votos Sacados).
    Solo extrae dígitos.
    """
    datos_por_fila = {}

    for cell in tabla_azure.cells:
        texto = limpiar_texto(cell.content).strip()
        if not texto:
            continue

        r = cell.row_index
        if r not in datos_por_fila:
            datos_por_fila[r] = {"id": "", "valor": ""}

        idx_col = cell.column_index

        if idx_col == 0:
            if "99" in texto:
                datos_por_fila[r]["id"] = "99"

        elif idx_col == 2:
            val = texto.replace("(Con número)", "").strip()
            if any(c.isdigit() for c in val):
                nums = re.findall(r'\d+', val)
                if nums:
                    datos_por_fila[r]["valor"] = nums[-1]

    # Buscar par exacto "99" + valor
    for r, datos in datos_por_fila.items():
        if datos["id"] == "99" and datos["valor"]:
            return f"99 : {datos['valor']}"

    # Fallback: buscar candidatos numéricos
    candidatos = []
    for cell in tabla_azure.cells:
        texto = limpiar_texto(cell.content).strip()
        texto = texto.replace("(Con número)", "").replace("(Con letra)", "")

        nums = re.findall(r'\d+', texto)
        if nums:
            valor = nums[-1]
            candidatos.append((cell.column_index, valor))

    if candidatos:
        candidatos.sort(key=lambda x: x[0], reverse=True)
        valor_encontrado = candidatos[0][1]
        return f"99 : {valor_encontrado}"

    return ""


def formatear_tabla_generica(tabla_azure) -> str:
    """
    Lógica original de extracción genérica A : B.
    Utilizada como fallback para tablas extra.
    """
    lineas = []

    celdas_por_fila = {}
    for cell in tabla_azure.cells:
        r = cell.row_index
        if r not in celdas_por_fila:
            celdas_por_fila[r] = {}
        celdas_por_fila[r][cell.column_index] = cell.content

    ultima_clave_valida = ""

    for r in sorted(celdas_por_fila.keys()):
        fila = celdas_por_fila[r]
        if not fila:
            continue

        contenidos_limpios = {col: limpiar_texto(c)
                             for col, c in fila.items() if limpiar_texto(c)}

        if not contenidos_limpios:
            continue

        indices = sorted(contenidos_limpios.keys())
        columnas_totales = tabla_azure.column_count

        texto_izq = ""
        texto_der = ""

        for col in indices:
            if col < columnas_totales / 2:
                val = contenidos_limpios[col]
                if val:
                    texto_izq = val
                    break

        candidate_val_col = indices[-1]
        if candidate_val_col >= columnas_totales / 2:
            texto_der = contenidos_limpios[candidate_val_col]

        if texto_izq:
            ultima_clave_valida = texto_izq

        if texto_der:
            if len(texto_der) < 1 or texto_der.lower() in ["=", "+"]:
                continue
            if ultima_clave_valida:
                lineas.append(f"{ultima_clave_valida} : {texto_der}")
            else:
                lineas.append(f" : {texto_der}")

    return "\n".join(lineas)
