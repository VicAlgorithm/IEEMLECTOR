"""
Exportador TOON — FLUJO 3
===========================
Orquesta la exportación de datos extraídos de Azure
en formato TOON (ID : VALOR).

Dos modos:
  - Con validador IA: extrae pares crudos → 1 llamada OpenAI → guarda
  - Sin validador:    extrae solo dígitos con regex → guarda
"""

import os
import re
import time
from typing import List, Dict, Any, Optional

from extractores import extraer_pares_tabla_1, extraer_pares_tabla_2, extraer_pares_tabla_3
from exportador_regex import procesar_tabla_1, procesar_tabla_2, procesar_tabla_3, formatear_tabla_generica


class ToonExporter:
    """Exporta datos de Azure AI a formato TOON (ID : VALOR)."""

    def guardar_toon(self, resultado_azure, ruta_salida_base: str,
                     nombre_documento: str, validador=None):
        """
        Punto de entrada principal.
        
        Si hay validador (FLUJO 4) → extracción cruda + 1 llamada OpenAI.
        Si no → extracción con regex (comportamiento original).
        
        Returns:
            dict con tiempos/tokens si hay validador, bool si no.
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

    # ══════════════════════════════════════════════════════════════════════
    # MODO CON IA: Extracción cruda + 1 llamada OpenAI
    # ══════════════════════════════════════════════════════════════════════

    def _guardar_con_validacion(self, resultado_azure, ruta_salida_base: str,
                                 nombre_documento: str, validador) -> dict:
        """
        Flujo optimizado:
          1. Extraer pares crudos de TODAS las tablas (local, 0 llamadas API)
          2. UNA SOLA llamada a Azure OpenAI con todos los pares juntos
          3. Separar resultados por tabla y guardar
        """
        print("\n[INFO] ══════════════════════════════════════════════════════")
        print("[INFO]  MODO: Extracción con Validación Inteligente (IA)")
        print("[INFO]  1 llamada Document Intelligence + 1 llamada OpenAI")
        print("[INFO] ══════════════════════════════════════════════════════")

        resultado = {
            "exito": False,
            "tiempo_extraccion_cruda": 0.0,
            "tiempo_validacion_ia": 0.0,
            "tiempo_lectura_cruda": 0.0,
            "tokens": {"prompt": 0, "respuesta": 0, "total": 0},
        }

        extractores = [extraer_pares_tabla_1, extraer_pares_tabla_2, extraer_pares_tabla_3]
        num_tablas = min(len(resultado_azure.tables), 3)
        todos_los_pares = []
        pares_por_tabla = {}

        # ── PASO 1: Extraer pares crudos (LOCAL) ──
        t0 = time.time()
        for i in range(num_tablas):
            tabla = resultado_azure.tables[i]
            pares = extractores[i](tabla) if i < len(extractores) else []
            todos_los_pares.append(pares)
            if pares:
                pares_por_tabla[i + 1] = pares
                print(f"[INFO] Tabla {i + 1}: {len(pares)} pares crudos extraídos")
            else:
                print(f"[ADVERTENCIA] Tabla {i + 1}: Sin pares crudos")
        resultado["tiempo_extraccion_cruda"] = time.time() - t0

        if not pares_por_tabla:
            print("[ERROR] No se extrajeron pares de ninguna tabla.")
            return resultado

        total_entradas = sum(len(p) for p in pares_por_tabla.values())
        print(f"\n[INFO] Total: {total_entradas} entradas de {len(pares_por_tabla)} tablas")

        # ── PASO 2: UNA SOLA llamada a Azure OpenAI ──
        t0 = time.time()
        respuesta_ia = validador.validar_documento(pares_por_tabla)
        resultado["tiempo_validacion_ia"] = time.time() - t0
        resultado["tokens"] = respuesta_ia.get("tokens", resultado["tokens"])

        if not respuesta_ia.get("exito"):
            print("[ERROR] La validación con Azure OpenAI falló.")
            return resultado

        # ── PASO 3: Formatear y guardar ──
        resultados_por_tabla = respuesta_ia.get("resultados_por_tabla", {})
        contenido_total = []
        todos_los_resultados = []

        for i in range(num_tablas):
            resultados_ia = resultados_por_tabla.get(i + 1, [])
            todos_los_resultados.append(resultados_ia)

            if resultados_ia:
                lineas = []
                for r in resultados_ia:
                    id_campo = str(r.get("id", "")).strip()
                    valor = r.get("valor")
                    if id_campo and valor is not None:
                        lineas.append(f"{id_campo} : {valor}")

                if lineas:
                    contenido_total.append(f"--- DATOS EXTRAÍDOS TABLA {i + 1} (Validado por IA) ---")
                    contenido_total.append("\n".join(lineas))
                    contenido_total.append("\n")

        if not contenido_total:
            return resultado

        # Guardar archivo de datos validados
        ruta_final = f"{ruta_salida_base}.txt"
        try:
            with open(ruta_final, "w", encoding="utf-8") as f:
                f.write("\n".join(contenido_total))
            print(f"\n[INFO] Datos validados exportados a: {ruta_final}")
            resultado["exito"] = True
        except Exception as e:
            print(f"[ERROR] No se pudo guardar el archivo: {str(e)}")

        # Generar lectura cruda
        t0 = time.time()
        self._generar_lectura_cruda(
            resultado_azure, ruta_salida_base, num_tablas,
            todos_los_pares, todos_los_resultados
        )
        resultado["tiempo_lectura_cruda"] = time.time() - t0

        return resultado

    # ══════════════════════════════════════════════════════════════════════
    # MODO SIN IA: Solo regex
    # ══════════════════════════════════════════════════════════════════════

    def _guardar_sin_validacion(self, resultado_azure, ruta_salida_base: str,
                                 nombre_documento: str) -> bool:
        """Guarda datos usando solo regex (sin IA)."""
        print("\n[INFO] ══════════════════════════════════════════════════════")
        print("[INFO]  MODO: Extracción con Regex (sin validación IA)")
        print("[INFO] ══════════════════════════════════════════════════════")

        procesadores = [procesar_tabla_1, procesar_tabla_2, procesar_tabla_3]
        num_tablas = min(len(resultado_azure.tables), 3)
        contenido_total = []

        for i in range(num_tablas):
            tabla = resultado_azure.tables[i]

            if i < len(procesadores):
                contenido = procesadores[i](tabla)
            else:
                contenido = formatear_tabla_generica(tabla)

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
            print(f"[INFO] Todos los datos exportados a: {ruta_final}")
            return True
        except Exception as e:
            print(f"[ERROR] No se pudo guardar: {str(e)}")
            return False

    # ══════════════════════════════════════════════════════════════════════
    # LECTURA CRUDA (diagnóstico)
    # ══════════════════════════════════════════════════════════════════════

    def _generar_lectura_cruda(self, resultado_azure, ruta_salida_base: str,
                                num_tablas: int, todos_los_pares: list,
                                todos_los_resultados: list):
        """
        Genera archivo de lectura cruda: qué leyó y qué decidió.
        """
        ruta_cruda = f"{ruta_salida_base}_lectura_cruda.txt"
        lineas = []

        nombres_tablas = [
            "TABLA 1 — Boletas, Personas, Representantes, Total",
            "TABLA 2 — Resultados por Partido",
            "TABLA 3 — Total de Votos Sacados"
        ]

        for i in range(num_tablas):
            resultados_ia = todos_los_resultados[i] if i < len(todos_los_resultados) else []

            nombre = nombres_tablas[i] if i < len(nombres_tablas) else f"TABLA {i + 1}"
            lineas.append(f"{'═' * 50}")
            lineas.append(f" {nombre}")
            lineas.append(f"{'═' * 50}")

            if not resultados_ia:
                lineas.append("  (Sin datos)")
                lineas.append("")
                continue

            for r in resultados_ia:
                id_campo = str(r.get("id", "")).strip()
                valor = r.get("valor")
                confianza = r.get("confianza", "?")
                razon = r.get("razonamiento", "")

                emoji = {"alta": "✅", "media": "⚠️", "baja": "❌"}.get(confianza, "❓")

                if valor is not None:
                    lineas.append(f"  {id_campo:2s}  {emoji} {valor}")
                else:
                    lineas.append(f"  {id_campo:2s}  ❌ NULO")

                if razon:
                    lineas.append(f"       {razon}")

            lineas.append("")

        # Guardar
        try:
            with open(ruta_cruda, "w", encoding="utf-8") as f:
                f.write("\n".join(lineas))
            print(f"[INFO] Lectura cruda exportada a: {ruta_cruda}")
        except Exception as e:
            print(f"[ERROR] No se pudo guardar lectura cruda: {str(e)}")
