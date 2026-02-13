"""
Procesador de Documentos - Pipeline Completo
==============================================
Procesa imágenes de documentos en dos flujos:
1. FLUJO 1: Endereza y escanea el documento (efecto CamScanner)
2. FLUJO 2: Extrae y recorta tablas usando Azure AI

Autor: Sistema de Procesamiento de Documentos
Librerías: OpenCV, Azure AI Document Intelligence
"""

import os
import sys
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Agregar las carpetas de los flujos al path para importar módulos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'FLUJO1_ENDEREZADO'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'FLUJO2_RECORTE'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'FLUJO3_EXTRACCION'))

# Importar módulos de los flujos
from document_scanner import escanear_documento
from table_extractor import TableExtractor, cargar_credenciales
from data_extractor import ToonExporter

import cv2


class ProcesadorDocumentos:
    """
    Clase principal para procesar documentos completos.
    Combina el enderezado, extracción de tablas y exportación TOON.
    """

    def __init__(self, azure_endpoint: Optional[str] = None, azure_api_key: Optional[str] = None):
        """
        Inicializa el procesador de documentos.
        """
        self.carpeta_resultados_base = "resultados"

        # Cargar credenciales de Azure
        if azure_endpoint and azure_api_key:
            self.azure_endpoint = azure_endpoint
            self.azure_api_key = azure_api_key
        else:
            self.azure_endpoint, self.azure_api_key = cargar_credenciales()

        # Inicializar extractor de tablas
        self.extractor_tablas = None
        if self.azure_endpoint and self.azure_api_key:
            self.extractor_tablas = TableExtractor(
                endpoint=self.azure_endpoint,
                api_key=self.azure_api_key
            )
            print("[INFO] Procesador inicializado con Azure AI")
        else:
            print("[ADVERTENCIA] Sin credenciales de Azure - Solo se ejecutará FLUJO 1")

        # Inicializar exportador TOON
        self.exportador_toon = ToonExporter()

    def procesar_imagen(self, ruta_imagen: str, ejecutar_flujo1: bool = True,
                       ejecutar_flujo2: bool = True, mostrar_resultados: bool = False) -> dict:
        """
        Procesa una imagen ejecutando los 3 flujos: Enderezado, Recorte y Extracción TOON.
        """
        resultados = {
            'flujo1_completado': False,
            'flujo2_completado': False,
            'flujo3_completado': False,
            'imagen_enderezada': None,
            'tablas_extraidas': [],
            'archivo_toon': None
        }

        # Obtener nombre base para la carpeta de resultados única
        nombre_base = Path(ruta_imagen).stem
        carpeta_resultados_unica = os.path.join(self.carpeta_resultados_base, nombre_base)
        carpeta_proceso = os.path.join(carpeta_resultados_unica, "proceso")

        print("\n" + "="*80)
        print("INICIANDO PROCESAMIENTO MULTI-FLUJO DE DOCUMENTO")
        print("="*80)
        print(f"\n[INFO] Imagen: {ruta_imagen}")
        print(f"[INFO] Destino: {carpeta_resultados_unica}")

        # Verificar que el archivo existe
        if not os.path.exists(ruta_imagen):
            print(f"\n[ERROR] El archivo no existe: {ruta_imagen}")
            return resultados

        os.makedirs(carpeta_resultados_unica, exist_ok=True)
        os.makedirs(carpeta_proceso, exist_ok=True)

        # ========================================================================
        # FLUJO 1: ENDEREZADO DEL DOCUMENTO
        # ========================================================================
        imagen_para_flujo2 = ruta_imagen

        if ejecutar_flujo1:
            print("\n" + "-"*80)
            print("EJECUTANDO FLUJO 1: ENDEREZADO Y ESCANEO")
            print("-"*80)

            documento_escaneado = escanear_documento(
                ruta_imagen=ruta_imagen,
                mostrar_pasos=mostrar_resultados,
                guardar_proceso=True,
                carpeta_proceso=carpeta_proceso,
                modo_efecto="original"  # Mantener color para que Flujo 2 pueda filtrar
            )

            if documento_escaneado is not None:
                ruta_enderezada = os.path.join(carpeta_resultados_unica, f"{nombre_base}_enderezado.jpg")
                cv2.imwrite(ruta_enderezada, documento_escaneado, [int(cv2.IMWRITE_JPEG_QUALITY), 85])

                resultados['flujo1_completado'] = True
                resultados['imagen_enderezada'] = ruta_enderezada
                imagen_para_flujo2 = ruta_enderezada
                print(f"[ÉXITO] Documento enderezado guardado.")
            else:
                print("[FALLO] No se pudo enderezar el documento.")

        # ========================================================================
        # FLUJO 2 Y 3: RECORTE Y EXTRACCIÓN TOON (Requieren Azure)
        # ========================================================================
        if ejecutar_flujo2:
            print("\n" + "-"*80)
            print("EJECUTANDO FLUJO 2 Y 3: RECORTE Y EXTRACCIÓN DE DATOS")
            print("-"*80)

            if self.extractor_tablas is None:
                print("[ERROR] Se requieren credenciales de Azure para Flujos 2 y 3.")
            else:
                # Flujo 2: Recorte
                nombre_img_tabla = f"{nombre_base}_tabla_extraida.jpg"
                analyze_result = self.extractor_tablas.procesar(
                    ruta_imagen=imagen_para_flujo2,
                    carpeta_salida=carpeta_resultados_unica,
                    nombre_salida=nombre_img_tabla,
                    mostrar=mostrar_resultados
                )

                if analyze_result:
                    resultados['flujo2_completado'] = True
                    resultados['tablas_extraidas'].append(os.path.join(carpeta_resultados_unica, nombre_img_tabla))
                    
                    # Flujo 3: Extracción TOON (Usando el resultado de Azure ya obtenido)
                    ruta_toon_base = os.path.join(carpeta_resultados_unica, f"{nombre_base}_datos")
                    exito_toon = self.exportador_toon.guardar_toon(
                        resultado_azure=analyze_result,
                        ruta_salida_base=ruta_toon_base,
                        nombre_documento=nombre_base
                    )
                    
                    if exito_toon:
                        resultados['flujo3_completado'] = True
                        resultados['archivo_toon'] = f"{ruta_toon_base}_tabla_1.txt (y otros)"

        # ========================================================================
        # RESUMEN FINAL
        # ========================================================================
        print("\n" + "="*80)
        print("RESUMEN DEL PROCESAMIENTO")
        print("="*80)
        print(f"  FLUJO 1 (Enderezado):     {'COMPLETADO' if resultados['flujo1_completado'] else 'FALLIDO'}")
        print(f"  FLUJO 2 (Recorte Tablas): {'COMPLETADO' if resultados['flujo2_completado'] else 'FALLIDO'}")
        print(f"  FLUJO 3 (Extraccion TOON): {'COMPLETADO' if resultados['flujo3_completado'] else 'FALLIDO'}")

        if resultados['archivo_toon']:
            print(f"\n  Datos extraidos (TOON): {resultados['archivo_toon']}")

        print(f"\n  Resultados en: {os.path.abspath(carpeta_resultados_unica)}")
        print("="*80 + "\n")

        return resultados


def main():
    """
    Función principal para ejecutar el script desde línea de comandos.
    """
    # Mostrar ayuda si no hay argumentos
    if len(sys.argv) < 2:
        print("="*80)
        print("Procesador de Documentos - Pipeline Completo")
        print("="*80)
        print("\nUso: python procesador_documentos.py <ruta_imagen> [opciones]")
        print("\nArgumentos:")
        print("  <ruta_imagen>    Ruta a la imagen del documento a procesar")
        print("\nOpciones:")
        print("  --solo-flujo1    Ejecuta solo el enderezado del documento")
        print("  --solo-flujo2    Ejecuta solo la extracción de tablas")
        print("  --mostrar        Muestra las imágenes durante el proceso")
        print("\nEjemplos:")
        print("  python procesador_documentos.py documento.jpg")
        print("  python procesador_documentos.py acta.png --mostrar")
        print("  python procesador_documentos.py foto.jpg --solo-flujo1")
        print("\nResultados:")
        print("  - Carpeta 'proceso/':  Imágenes del proceso de enderezado")
        print("  - Carpeta 'recortes/': Tablas extraídas")
        print("\nConfiguración Azure AI:")
        print("  Crea un archivo .env con:")
        print("    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=tu_endpoint")
        print("    AZURE_DOCUMENT_INTELLIGENCE_KEY=tu_api_key")
        print("="*80)
        sys.exit(1)

    # Parsear argumentos
    ruta_imagen = sys.argv[1]
    solo_flujo1 = '--solo-flujo1' in sys.argv
    solo_flujo2 = '--solo-flujo2' in sys.argv
    mostrar = '--mostrar' in sys.argv

    # Determinar qué flujos ejecutar
    if solo_flujo1:
        ejecutar_flujo1 = True
        ejecutar_flujo2 = False
    elif solo_flujo2:
        ejecutar_flujo1 = False
        ejecutar_flujo2 = True
    else:
        ejecutar_flujo1 = True
        ejecutar_flujo2 = True

    # Verificar que el archivo existe
    if not os.path.exists(ruta_imagen):
        print(f"[ERROR] El archivo no existe: {ruta_imagen}")
        sys.exit(1)

    # Crear procesador
    procesador = ProcesadorDocumentos()

    # Procesar imagen
    resultados = procesador.procesar_imagen(
        ruta_imagen=ruta_imagen,
        ejecutar_flujo1=ejecutar_flujo1,
        ejecutar_flujo2=ejecutar_flujo2,
        mostrar_resultados=mostrar
    )

    # Verificar éxito
    if ejecutar_flujo1 and not resultados['flujo1_completado']:
        print("\n[ADVERTENCIA] FLUJO 1 no se completó correctamente")

    if ejecutar_flujo2 and not resultados['flujo2_completado']:
        print("\n[ADVERTENCIA] FLUJO 2 no se completó correctamente")

    # Retornar código de salida
    if (ejecutar_flujo1 and not resultados['flujo1_completado']) or \
       (ejecutar_flujo2 and not resultados['flujo2_completado']):
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
