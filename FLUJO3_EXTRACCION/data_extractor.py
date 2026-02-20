"""
Exportador de datos en formato TOON - FLUJO 3
=============================================
Transforma los datos extraídos por Azure AI en un formato TOON
simplificado y legible para humanos.

Soporta dos modos de operación:
  - Sin validador: Extracción basada en regex (comportamiento original)
  - Con validador: Extracción cruda + validación inteligente con Azure OpenAI (FLUJO 4)
"""

import os
import re
from typing import List, Dict, Any, Optional


class ToonExporter:
    """
    Clase para convertir resultados de Azure AI a formato simple A : B.
    Soporta validación inteligente con Azure OpenAI cuando se proporciona un validador.
    """

    # ========================================================================
    # MÉTODOS DE LIMPIEZA DE TEXTO
    # ========================================================================

    @staticmethod
    def limpiar_texto(texto: str) -> str:
        """Limpia el ruido de Azure y símbolos innecesarios (modo estricto)."""
        ruido = [
            ":unselected:", ":selected:", "selected", "unselected",
            "○", "□", "✓", "—",
            "(Con letra)", "(Con número)", "(Con numera)", "@",
            "Personas que votaron", "Representantes", "Total de personas"
        ]

        resultado = texto
        for r in ruido:
            resultado = resultado.replace(r, "")
        resultado = resultado.strip(" .-_,")

        # Filtro de Instrucciones Largas
        texto_lower = resultado.lower()
        if (texto_lower.startswith("copie") or
            texto_lower.startswith("escriba") or
            "del apartado" in texto_lower or
            "de la hoja" in texto_lower or
            len(resultado) > 60):
            return ""

        return resultado

    @staticmethod
    def limpiar_texto_ligero(texto: str) -> str:
        """
        Limpieza ligera que mantiene el texto con letra pero quita ruido de Azure.
        Usada para la extracción cruda (modo validación con IA).
        """
        ruido_azure = [
            ":unselected:", ":selected:",
            "○", "□", "✓", "—", "@"
        ]

        resultado = texto
        for r in ruido_azure:
            resultado = resultado.replace(r, "")

        return resultado.strip()

    # ========================================================================
    # MÉTODOS DE EXTRACCIÓN CRUDA (Para validación con IA - FLUJO 4)
    # ========================================================================

    @staticmethod
    def extraer_pares_tabla_1(tabla_azure) -> List[Dict]:
        """
        Extrae pares crudos de la Tabla 1 (Boletas, Personas, Representantes, Total).
        Captura TODOS los contenidos de cada celda para enviar al validador IA.

        Returns:
            Lista de dicts: [{"id": "94", "contenidos": ["veinisinco", "25", ...]}, ...]
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

            # Limpieza ligera (mantiene texto con letra)
            contenido_limpio = ToonExporter.limpiar_texto_ligero(contenido)
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

    @staticmethod
    def extraer_pares_tabla_2(tabla_azure) -> List[Dict]:
        """
        Extrae pares crudos de la Tabla 2 (Resultados por Partido).
        Captura TODOS los contenidos de cada fila.

        Returns:
            Lista de dicts: [{"id": "00", "contenidos": ["PAN", "veintiquatro", "24"]}, ...]
        """
        # Organizar celdas por fila
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

            # Recopilar contenidos limpios de la fila
            contenidos = []
            id_campo = ""

            for col in sorted(fila.keys()):
                texto = ToonExporter.limpiar_texto_ligero(fila[col])
                if texto:
                    contenidos.append(texto)

                    # Intentar extraer ID de las primeras columnas
                    if col < tabla_azure.column_count / 2 and not id_campo:
                        # Corrección OCR: letras comúnmente confundidas con dígitos
                        texto_corregido = texto
                        ocr_fixes = {'O': '0', 'o': '0', 'S': '5', 's': '5',
                                     'I': '1', 'l': '1', 'Z': '2', 'z': '2',
                                     'B': '8', 'G': '6', 'g': '9'}
                        for letra, digito in ocr_fixes.items():
                            texto_corregido = texto_corregido.replace(letra, digito)

                        numeros = re.findall(r'\d+', texto_corregido)
                        if numeros:
                            id_campo = numeros[0].zfill(2)  # Pad a 2 dígitos: "5" → "05"

            if id_campo and contenidos:
                pares.append({
                    "id": id_campo,
                    "contenidos": contenidos
                })

        return pares

    @staticmethod
    def extraer_pares_tabla_3(tabla_azure) -> List[Dict]:
        """
        Extrae pares crudos de la Tabla 3 (Total de Votos Sacados).
        Captura TODOS los contenidos de todas las celdas.

        Returns:
            Lista de dicts: [{"id": "99", "contenidos": ["ciento diez", "110", ...]}, ...]
        """
        contenidos = []

        for cell in tabla_azure.cells:
            texto = ToonExporter.limpiar_texto_ligero(cell.content)
            if texto:
                contenidos.append(texto)

        if contenidos:
            return [{"id": "99", "contenidos": contenidos}]

        return []

    # ========================================================================
    # MÉTODOS DE PROCESAMIENTO ORIGINAL (Sin validación IA - solo regex)
    # ========================================================================

    @staticmethod
    def procesar_tabla_1(tabla_azure) -> str:
        """
        Procesa la TABLA 1 (Boletas, Personas, Representantes, Total).
        Divide la tabla verticalmente en 4 secciones iguales y extrae el contenido de cada una.
        MODO: Solo dígitos (sin validación IA).
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

            texto = ToonExporter.limpiar_texto(cell.content)
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

    @staticmethod
    def procesar_tabla_2(tabla_azure) -> str:
        """
        Procesa la TABLA 2 (Resultados por Partido).
        MODO: Solo dígitos (sin validación IA).
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

            contenidos_limpios = {col: ToonExporter.limpiar_texto(c)
                                 for col, c in fila.items() if ToonExporter.limpiar_texto(c)}

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

    @staticmethod
    def procesar_tabla_3(tabla_azure) -> str:
        """
        Procesa la TABLA 3 (Total de Votos Sacados).
        MODO: Solo dígitos (sin validación IA).
        """
        datos_por_fila = {}

        for cell in tabla_azure.cells:
            texto = ToonExporter.limpiar_texto(cell.content).strip()
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
            texto = ToonExporter.limpiar_texto(cell.content).strip()
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

    @staticmethod
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

            contenidos_limpios = {col: ToonExporter.limpiar_texto(c)
                                 for col, c in fila.items() if ToonExporter.limpiar_texto(c)}

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

    # ========================================================================
    # MÉTODO PRINCIPAL DE GUARDADO
    # ========================================================================

    def guardar_toon(self, resultado_azure, ruta_salida_base: str,
                     nombre_documento: str, validador=None):
        """
        Guarda las primeras 3 tablas en formato TOON.

        Si se proporciona un validador (FLUJO 4), usa extracción cruda + validación IA.
        Si no, usa la extracción basada en regex (comportamiento original).

        Args:
            resultado_azure:   Objeto AnalyzeResult de Azure AI
            ruta_salida_base:  Ruta base para el archivo de salida (sin extensión)
            nombre_documento:  Nombre del documento procesado
            validador:         (Opcional) Instancia de ValidadorNumeros de FLUJO 4
        """
        if not hasattr(resultado_azure, 'tables') or not resultado_azure.tables:
            print("[INFO] No se encontraron tablas para exportar en el resultado de Azure.")
            return False

        if validador:
            return self._guardar_con_validacion(
                resultado_azure, ruta_salida_base, nombre_documento, validador
            )
        else:
            return self._guardar_sin_validacion(
                resultado_azure, ruta_salida_base, nombre_documento
            )

    def _guardar_con_validacion(self, resultado_azure, ruta_salida_base: str,
                                 nombre_documento: str, validador) -> bool:
        """
        Guarda datos validados por IA (FLUJO 4).
        Extrae datos crudos de cada tabla y los envía al validador para razonamiento.
        También genera un archivo de lectura cruda para diagnóstico.
        """
        print("\n[INFO] ══════════════════════════════════════════════════════")
        print("[INFO]  MODO: Extracción con Validación Inteligente (IA)")
        print("[INFO] ══════════════════════════════════════════════════════")

        # Extractores crudos para cada tabla
        extractores = [
            self.extraer_pares_tabla_1,
            self.extraer_pares_tabla_2,
            self.extraer_pares_tabla_3
        ]

        num_tablas = min(len(resultado_azure.tables), 3)
        contenido_total = []
        exito_alguna = False

        for i in range(num_tablas):
            tabla = resultado_azure.tables[i]

            # Extraer pares crudos
            if i < len(extractores):
                pares = extractores[i](tabla)
            else:
                pares = []

            if pares:
                # Enviar al validador IA
                contenido_validado = validador.validar_tabla(f"Tabla {i + 1}", pares)

                if contenido_validado.strip():
                    contenido_total.append(f"--- DATOS EXTRAÍDOS TABLA {i + 1} (Validado por IA) ---")
                    contenido_total.append(contenido_validado)
                    contenido_total.append("\n")
                    exito_alguna = True
                else:
                    print(f"[ADVERTENCIA] Tabla {i + 1}: El validador no retornó datos.")
            else:
                print(f"[ADVERTENCIA] Tabla {i + 1}: No se pudieron extraer pares crudos.")

        if not contenido_total:
            return False

        # Guardar archivo de datos validados
        ruta_final = f"{ruta_salida_base}.txt"

        try:
            with open(ruta_final, "w", encoding="utf-8") as f:
                f.write("\n".join(contenido_total))
            print(f"\n[INFO] Datos validados exportados a: {ruta_final}")
            exito_alguna = True
        except Exception as e:
            print(f"[ERROR] No se pudo guardar el archivo: {str(e)}")

        # Generar archivo de lectura cruda (diagnóstico)
        self._generar_lectura_cruda(resultado_azure, ruta_salida_base, num_tablas)

        return exito_alguna

    def _generar_lectura_cruda(self, resultado_azure, ruta_salida_base: str,
                                num_tablas: int):
        """
        Genera un archivo de diagnóstico mostrando EXACTAMENTE lo que Azure leyó.
        Incluye todas las celdas, filas descartadas y el motivo del descarte.
        """
        ruta_cruda = f"{ruta_salida_base}_lectura_cruda.txt"
        lineas = []

        lineas.append("=" * 70)
        lineas.append("LECTURA CRUDA DE AZURE DOCUMENT INTELLIGENCE")
        lineas.append("Este archivo muestra EXACTAMENTE lo que Azure leyó del documento.")
        lineas.append("Sirve para diagnosticar filas faltantes o errores de lectura.")
        lineas.append("=" * 70)

        ids_esperados_tabla2 = {"00", "01", "02", "03", "04", "05", "06",
                                "07", "08", "09", "10", "11", "91", "92", "93"}

        for i in range(num_tablas):
            tabla = resultado_azure.tables[i]

            lineas.append(f"\n{'─' * 70}")
            lineas.append(f" TABLA {i + 1}")
            lineas.append(f" Filas: {tabla.row_count} | Columnas: {tabla.column_count}")
            lineas.append(f" Total de celdas: {len(tabla.cells)}")
            lineas.append(f"{'─' * 70}")

            # Organizar celdas por fila
            celdas_por_fila = {}
            for cell in tabla.cells:
                r = cell.row_index
                if r not in celdas_por_fila:
                    celdas_por_fila[r] = {}
                celdas_por_fila[r][cell.column_index] = cell.content

            for r in sorted(celdas_por_fila.keys()):
                fila = celdas_por_fila[r]
                lineas.append(f"\n  ┌─ Fila {r}")

                contenidos_fila = []
                tiene_id = False
                id_detectado = ""

                for col in sorted(fila.keys()):
                    texto_raw = fila[col].replace('\n', ' ').strip()
                    contenidos_fila.append(f"    │ Col {col}: '{texto_raw}'")

                    # Intentar detectar ID (misma lógica que extraer_pares_tabla_2)
                    if col == 0 and not tiene_id:
                        texto_corregido = texto_raw
                        ocr_fixes = {'O': '0', 'o': '0', 'S': '5', 's': '5',
                                     'I': '1', 'l': '1', 'Z': '2', 'z': '2',
                                     'B': '8', 'G': '6', 'g': '9'}
                        for letra, digito in ocr_fixes.items():
                            texto_corregido = texto_corregido.replace(letra, digito)
                        numeros = re.findall(r'\d+', texto_corregido)
                        if numeros:
                            id_detectado = numeros[0].zfill(2)
                            tiene_id = True

                for c in contenidos_fila:
                    lineas.append(c)

                # Mostrar estado de la fila
                if i == 1:  # Tabla 2 - mostrar análisis detallado
                    if tiene_id:
                        if id_detectado != fila.get(0, '').strip():
                            lineas.append(f"    │ ⚠️  OCR corregido: '{fila.get(0, '')}' → ID '{id_detectado}'")
                        lineas.append(f"    └─ ✅ ID detectado: {id_detectado}")
                    else:
                        contenido_col0 = fila.get(0, '(vacía)')
                        lineas.append(f"    └─ ❌ DESCARTADA — No se pudo extraer ID de Col 0: '{contenido_col0}'")

            # Para Tabla 2: mostrar IDs faltantes
            if i == 1:
                ids_encontrados = set()
                for r in sorted(celdas_por_fila.keys()):
                    fila = celdas_por_fila[r]
                    if 0 in fila:
                        texto_corregido = fila[0].strip()
                        ocr_fixes = {'O': '0', 'o': '0', 'S': '5', 's': '5',
                                     'I': '1', 'l': '1', 'Z': '2', 'z': '2',
                                     'B': '8', 'G': '6', 'g': '9'}
                        for letra, digito in ocr_fixes.items():
                            texto_corregido = texto_corregido.replace(letra, digito)
                        numeros = re.findall(r'\d+', texto_corregido)
                        if numeros:
                            ids_encontrados.add(numeros[0].zfill(2))

                ids_faltantes = ids_esperados_tabla2 - ids_encontrados
                if ids_faltantes:
                    lineas.append(f"\n  ⚠️  IDs ESPERADOS NO ENCONTRADOS: {sorted(ids_faltantes)}")
                    lineas.append(f"     Azure no detectó estas filas en la imagen.")
                else:
                    lineas.append(f"\n  ✅ TODOS los IDs esperados fueron detectados (00-11, 91-93)")

        # Guardar archivo
        try:
            with open(ruta_cruda, "w", encoding="utf-8") as f:
                f.write("\n".join(lineas))
            print(f"[INFO] Lectura cruda exportada a: {ruta_cruda}")
        except Exception as e:
            print(f"[ERROR] No se pudo guardar lectura cruda: {str(e)}")

    def _guardar_sin_validacion(self, resultado_azure, ruta_salida_base: str,
                                 nombre_documento: str) -> bool:
        """
        Guarda datos usando solo regex (comportamiento original, sin IA).
        """
        print("\n[INFO] ══════════════════════════════════════════════════════")
        print("[INFO]  MODO: Extracción con Regex (sin validación IA)")
        print("[INFO] ══════════════════════════════════════════════════════")

        exito_alguna = False
        directorio = os.path.dirname(ruta_salida_base)
        nombre_base = os.path.splitext(os.path.basename(ruta_salida_base))[0]

        # Procesadores originales basados en regex
        procesadores = [
            self.procesar_tabla_1,
            self.procesar_tabla_2,
            self.procesar_tabla_3
        ]

        num_tablas = min(len(resultado_azure.tables), 3)
        contenido_total = []

        for i in range(num_tablas):
            tabla = resultado_azure.tables[i]

            if i < len(procesadores):
                contenido = procesadores[i](tabla)
            else:
                contenido = self.formatear_tabla_generica(tabla)

            if contenido.strip():
                contenido_total.append(f"--- DATOS EXTRAÍDOS TABLA {i + 1} ---")
                contenido_total.append(contenido)
                contenido_total.append("\n")

        if not contenido_total:
            return False

        ruta_final = f"{ruta_salida_base}.txt"

        try:
            with open(ruta_final, "w", encoding="utf-8") as f:
                f.write("\n".join(contenido_total))
            print(f"[INFO] Todos los datos exportados a un solo archivo: {ruta_final}")
            exito_alguna = True
        except Exception as e:
            print(f"[ERROR] No se pudo guardar el archivo consolidado: {str(e)}")

        return exito_alguna
