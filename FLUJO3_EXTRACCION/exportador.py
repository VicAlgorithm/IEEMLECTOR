"""
Exportador TOON — FLUJO 3
===========================
Orquesta la exportación de datos extraídos de Azure
en formato TOON (ID : VALOR).

Dos modos:
  - Con validador IA: extrae pares crudos → pre-valida localmente
                      → 1 llamada OpenAI (solo los no resueltos) → guarda
  - Sin validador:    extrae solo dígitos con regex → guarda
"""

import os
import re
import sys
import time
from typing import List, Dict, Any, Optional

from extractores import extraer_pares_tabla_1, extraer_pares_tabla_2, extraer_pares_tabla_3
from exportador_regex import procesar_tabla_1, procesar_tabla_2, procesar_tabla_3, formatear_tabla_generica

# ──────────────────────────────────────────────────────────────────────────────
# Importar el ConvertidorTextoNumeros (FLUJO 4 — módulo local, sin API)
# ──────────────────────────────────────────────────────────────────────────────
_CONVERTIDOR_DISPONIBLE = False
try:
    # Asegurarse de que la carpeta FLUJO4_VALIDACION esté en el path
    _flujo4_path = os.path.join(os.path.dirname(__file__), '..', 'FLUJO4_VALIDACION')
    _flujo4_path = os.path.normpath(_flujo4_path)
    if _flujo4_path not in sys.path:
        sys.path.insert(0, _flujo4_path)
    from convertidor_texto_numeros import ConvertidorTextoNumeros
    _CONVERTIDOR_DISPONIBLE = True
except ImportError:
    pass  # Seguirá funcionando, pero sin pre-validación local


# Umbral mínimo de confianza para aceptar un resultado local sin recurrir a OpenAI
_CONFIANZA_MINIMA = 0.75


class ToonExporter:
    """Exporta datos de Azure AI a formato TOON (ID : VALOR)."""

    def guardar_toon(self, resultado_azure, ruta_salida_base: str,
                     nombre_documento: str, validador=None):
        """
        Punto de entrada principal.

        Si hay validador (FLUJO 4) → extracción cruda + pre-validación local
                                     + 1 llamada OpenAI (solo campos no resueltos).
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
    # MODO CON IA: Extracción cruda + pre-validación local + OpenAI residual
    # ══════════════════════════════════════════════════════════════════════

    def _guardar_con_validacion(self, resultado_azure, ruta_salida_base: str,
                                 nombre_documento: str, validador) -> dict:
        """
        Flujo optimizado:
          1. Extraer pares crudos de TODAS las tablas (local, 0 llamadas API)
          1.5 Pre-validar localmente con ConvertidorTextoNumeros (sin API)
          2. UNA SOLA llamada a Azure OpenAI con los pares NO resueltos localmente
          3. Combinar resultados locales + IA y guardar
        """
        print("\n[INFO] ══════════════════════════════════════════════════════")
        print("[INFO]  MODO: Extracción con Validación Inteligente (IA)")
        print("[INFO]  1 llamada Document Intelligence + pre-validación local + 1 llamada OpenAI")
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

        # ── PASO 1.5: Pre-validación LOCAL con ConvertidorTextoNumeros ──
        # Resuelve localmente los pares que puede, sin gastar tokens de OpenAI
        resultados_locales_por_tabla = {}  # {num_tabla: {id_campo: resultado_dict}}
        pares_para_ia_por_tabla = {}       # Solo los que no se pudieron resolver

        if _CONVERTIDOR_DISPONIBLE:
            convertidor = ConvertidorTextoNumeros()
            total_resueltos_local = 0
            total_para_ia = 0

            print(f"\n[INFO] ── Pre-validación local (ConvertidorTextoNumeros) ──")

            for num_tabla, pares in sorted(pares_por_tabla.items()):
                resultados_locales_por_tabla[num_tabla] = {}
                pares_para_ia_por_tabla[num_tabla] = []

                for par in pares:
                    id_campo = par["id"]
                    contenidos = par["contenidos"]

                    # Detectar qué contenido es texto-letra y cuál es dígito
                    texto_letra, texto_digito = _separar_letra_y_digito(contenidos)

                    resuelto = False
                    if texto_letra:
                        res = convertidor.validar_campo(texto_letra, texto_digito or "")
                        metodo = res.get("metodo", "")
                        confianza = res.get("confianza", 0.0)
                        valor = res.get("valor")

                        # Aceptar resultado local si la confianza es suficiente
                        # y no requiere IA (metodo != 'necesita_ia')
                        if (metodo != "necesita_ia" and
                                metodo != "sin_resultado" and
                                confianza >= _CONFIANZA_MINIMA and
                                valor is not None):
                            resultados_locales_por_tabla[num_tabla][id_campo] = {
                                "id": id_campo,
                                "tabla": num_tabla,
                                "valor": valor,
                                "confianza": "alta" if confianza >= 0.95 else "media",
                                "razonamiento": f"[LOCAL] {res.get('detalle', metodo)}"
                            }
                            resuelto = True
                            total_resueltos_local += 1
                            emoji = "✅" if confianza >= 0.95 else "⚠️"
                            print(f"  {emoji} T{num_tabla} ID {id_campo}: {valor} "
                                  f"[local/{metodo}] — '{texto_letra}'")

                    if not resuelto:
                        pares_para_ia_por_tabla[num_tabla].append(par)
                        total_para_ia += 1

                # Limpiar tabla si no quedaron pares para IA
                if not pares_para_ia_por_tabla[num_tabla]:
                    del pares_para_ia_por_tabla[num_tabla]

            print(f"\n[INFO] Pre-validación local: "
                  f"{total_resueltos_local} campo(s) resueltos sin IA, "
                  f"{total_para_ia} campo(s) pendientes para OpenAI")
        else:
            # Sin convertidor: todos van a OpenAI
            pares_para_ia_por_tabla = pares_por_tabla
            resultados_locales_por_tabla = {t: {} for t in pares_por_tabla}
            print("[INFO] ConvertidorTextoNumeros no disponible — todos los campos irán a OpenAI")

        # ── PASO 2: UNA SOLA llamada a Azure OpenAI (solo campos no resueltos) ──
        resultados_ia_por_tabla = {t: [] for t in pares_por_tabla}

        if pares_para_ia_por_tabla:
            total_entradas_ia = sum(len(p) for p in pares_para_ia_por_tabla.values())
            t0 = time.time()
            respuesta_ia = validador.validar_documento(pares_para_ia_por_tabla)
            resultado["tiempo_validacion_ia"] = time.time() - t0
            resultado["tokens"] = respuesta_ia.get("tokens", resultado["tokens"])

            if not respuesta_ia.get("exito"):
                print("[ERROR] La validación con Azure OpenAI falló.")
                # Aun así, guardar lo resuelto localmente si hay algo
                if any(resultados_locales_por_tabla.values()):
                    print("[INFO] Guardando resultados locales parciales...")
                else:
                    return resultado

            resultados_ia_por_tabla = respuesta_ia.get("resultados_por_tabla",
                                                        {t: [] for t in pares_por_tabla})
        else:
            print("[INFO] Todos los campos resueltos localmente — no se llama a Azure OpenAI")
            resultado["tiempo_validacion_ia"] = 0.0

        # ── PASO 3: Combinar resultados locales + IA y guardar ──
        contenido_total = []
        todos_los_resultados = []  # Para lectura cruda (orden por tabla)

        for i in range(num_tablas):
            num_tabla = i + 1
            locales = resultados_locales_por_tabla.get(num_tabla, {})
            ia_lista = resultados_ia_por_tabla.get(num_tabla, [])

            # Unificar: los de IA como dict por id para deduplicar
            ia_por_id = {str(r.get("id", "")).strip(): r for r in ia_lista}

            # Orden de IDs: primero los del par original para mantener secuencia
            pares_originales = pares_por_tabla.get(num_tabla, [])
            ids_orden = [par["id"] for par in pares_originales]

            lineas = []
            resultados_tabla_combinados = []
            for id_campo in ids_orden:
                # Prioridad: local → IA
                if id_campo in locales:
                    r = locales[id_campo]
                else:
                    r = ia_por_id.get(id_campo)

                if r and r.get("valor") is not None:
                    lineas.append(f"{id_campo} : {r['valor']}")
                    resultados_tabla_combinados.append(r)

            # Agregar también resultados de IA que vengan con IDs no en orden original
            for id_ia, r in ia_por_id.items():
                if id_ia not in ids_orden and r.get("valor") is not None:
                    lineas.append(f"{id_ia} : {r['valor']}")
                    resultados_tabla_combinados.append(r)

            todos_los_resultados.append(resultados_tabla_combinados)

            if lineas:
                origen = "(Validado local + IA)" if locales and ia_lista else \
                         "(Validado por IA)" if ia_lista else \
                         "(Validado localmente)"
                contenido_total.append(f"--- DATOS EXTRAÍDOS TABLA {num_tabla} {origen} ---")
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
            resultados_combinados = todos_los_resultados[i] if i < len(todos_los_resultados) else []

            nombre = nombres_tablas[i] if i < len(nombres_tablas) else f"TABLA {i + 1}"
            lineas.append(f"{'═' * 50}")
            lineas.append(f" {nombre}")
            lineas.append(f"{'═' * 50}")

            if not resultados_combinados:
                lineas.append("  (Sin datos)")
                lineas.append("")
                continue

            for r in resultados_combinados:
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


# ══════════════════════════════════════════════════════════════════════════════
# UTILIDAD: Separar texto-letra y texto-dígito de la lista de contenidos
# ══════════════════════════════════════════════════════════════════════════════

def _separar_letra_y_digito(contenidos: List[str]):
    """
    Analiza la lista de contenidos de un par crudo e identifica:
      - texto_letra:  el elemento más largo que contenga letras del alfabeto
      - texto_digito: el primer elemento que sea solo dígitos (o mayormente dígitos)

    Retorna (texto_letra, texto_digito). Cualquiera puede ser None si no se encuentra.
    """
    texto_letra = None
    texto_digito = None

    for contenido in contenidos:
        c = contenido.strip()
        if not c:
            continue

        # Detectar si es un número puro (solo dígitos, posiblemente con espacios/puntos)
        solo_nums = re.sub(r'[^0-9]', '', c)
        solo_letras = re.sub(r'[^a-záéíóúüñA-ZÁÉÍÓÚÜÑ]', '', c)

        es_digito_puro = bool(solo_nums) and len(solo_nums) >= len(c) * 0.7

        if es_digito_puro and texto_digito is None:
            texto_digito = c

        elif solo_letras and len(solo_letras) >= 3:
            # Preferir el texto más largo que contenga letras
            if texto_letra is None or len(c) > len(texto_letra):
                texto_letra = c

    return texto_letra, texto_digito
