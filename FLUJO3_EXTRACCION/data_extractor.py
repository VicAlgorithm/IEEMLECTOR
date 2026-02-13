"""
Exportador de datos en formato TOON - FLUJO 3
=============================================
Transforma los datos extraídos por Azure AI en un formato TOON
simplificado y legible para humanos.
"""

import os
from typing import List, Dict, Any

class ToonExporter:
    """
    Clase para convertir resultados de Azure AI a formato simple A : B.
    """

    @staticmethod
    def limpiar_texto(texto: str) -> str:
        """Limpia el ruido de Azure y símbolos innecesarios."""
        # Eliminar etiquetas de selección de Azure y otros ruidos comunes
        ruido = [":unselected:", ":selected:", "selected", "unselected", "○", "□", "✓", "—"]
        resultado = texto
        for r in ruido:
            resultado = resultado.replace(r, "")
        
        # Limpiar espacios extra y puntuación huérfana
        resultado = resultado.strip(" .-_,")
        return resultado

    @staticmethod
    def formatear_tabla_simple(tabla_azure) -> str:
        """
        Convierte la primera tabla a formato A : B (Clave : Valor).
        Intenta ser inteligente al elegir qué es A y qué es B.
        """
        lineas = []
        
        # Organizar celdas por fila
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
            
            # Limpiar todos los contenidos de la fila primero
            contenidos_limpios = {col: ToonExporter.limpiar_texto(c) 
                                 for col, c in fila.items() if ToonExporter.limpiar_texto(c)}
            
            if not contenidos_limpios:
                continue
                
            indices = sorted(contenidos_limpios.keys())
            
            if len(indices) >= 2:
                # Caso ideal: Primera columna con texto y última columna con texto
                # (A menudo la columna 0 tiene el ID P1, P2 y la última el valor numérico)
                col_a = indices[0]
                col_b = indices[-1]
                
                # Si la primera columna real es un ID corto (P1, PAN, etc.) es ideal para A
                # Si la última columna es el número final, es ideal para B
                lineas.append(f"{contenidos_limpios[col_a]} : {contenidos_limpios[col_b]}")
            elif len(indices) == 1:
                # Solo detectamos un dato en toda la fila
                # Podría ser un valor sin etiqueta o una etiqueta sin valor
                val = contenidos_limpios[indices[0]]
                if indices[0] < tabla_azure.column_count / 2:
                    lineas.append(f"{val} : ")
                else:
                    lineas.append(f" : {val}")

        return "\n".join(lineas)

    def guardar_toon(self, resultado_azure, ruta_salida_base: str, nombre_documento: str):
        """
        Guarda las primeras 3 tablas detectadas en archivos separados.
        """
        if not hasattr(resultado_azure, 'tables') or not resultado_azure.tables:
            print("[INFO] No se encontraron tablas para exportar en el resultado de Azure.")
            return False

        exito_alguna = False
        directorio = os.path.dirname(ruta_salida_base)
        nombre_base = os.path.splitext(os.path.basename(ruta_salida_base))[0]

        # Procesar hasta las primeras 3 tablas
        num_tablas = min(len(resultado_azure.tables), 3)
        
        for i in range(num_tablas):
            tabla = resultado_azure.tables[i]
            contenido = self.formatear_tabla_simple(tabla)
            
            # Crear nombre de archivo para esta tabla
            # Ejemplo: resultados/A1/A1_datos_tabla_1.txt
            ruta_tabla = os.path.join(directorio, f"{nombre_base}_tabla_{i+1}.txt")
            
            try:
                with open(ruta_tabla, "w", encoding="utf-8") as f:
                    f.write(f"--- DATOS EXTRAÍDOS TABLA {i+1} ---\n")
                    f.write(contenido)
                print(f"[INFO] Tabla {i+1} exportada a: {ruta_tabla}")
                exito_alguna = True
            except Exception as e:
                print(f"[ERROR] No se pudo guardar la tabla {i+1}: {str(e)}")

        return exito_alguna
