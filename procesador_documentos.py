"""
Procesador de Documentos - Pipeline Completo
==============================================
Procesa imágenes de documentos en cuatro flujos:
1. FLUJO 1: Endereza y escanea el documento (efecto CamScanner)
2. FLUJO 2: Extrae y recorta tablas usando Azure AI
3. FLUJO 3: Exporta datos en formato TOON
4. FLUJO 4: Valida números con Azure OpenAI (letra vs dígitos)

Autor: Sistema de Procesamiento de Documentos
Librerías: OpenCV, Azure AI Document Intelligence, Azure OpenAI
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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'FLUJO4_VALIDACION'))

# Importar módulos de los flujos
from document_scanner import escanear_documento
from table_extractor import TableExtractor, cargar_credenciales
from data_extractor import ToonExporter
from credenciales import cargar_credenciales_openai

# Importación condicional de FLUJO 4
FLUJO4_DISPONIBLE = False
try:
    from validador_numeros import ValidadorNumeros, OPENAI_AVAILABLE
    if OPENAI_AVAILABLE:
        FLUJO4_DISPONIBLE = True
except ImportError:
    print("[INFO] FLUJO 4 (Validación IA) no disponible. Instala: pip install openai")

import cv2


class ProcesadorDocumentos:
    """
    Clase principal para procesar documentos completos.
    Combina el enderezado, extracción de tablas, exportación TOON y validación IA.
    """

    def __init__(self, azure_endpoint: Optional[str] = None,
                 azure_api_key: Optional[str] = None,
                 usar_validacion_ia: bool = True):
        """
        Inicializa el procesador de documentos.

        Args:
            azure_endpoint: Endpoint de Azure Document Intelligence (opcional, se lee de .env)
            azure_api_key:  API key de Azure Document Intelligence (opcional, se lee de .env)
            usar_validacion_ia: Si True, intenta inicializar el validador de FLUJO 4
        """
        self.carpeta_resultados_base = "resultados"

        # ── Credenciales Azure Document Intelligence (FLUJO 2) ──
        if azure_endpoint and azure_api_key:
            self.azure_endpoint = azure_endpoint
            self.azure_api_key = azure_api_key
        else:
            self.azure_endpoint, self.azure_api_key = cargar_credenciales()

        # ── Inicializar extractor de tablas (FLUJO 2) ──
        self.extractor_tablas = None
        if self.azure_endpoint and self.azure_api_key:
            self.extractor_tablas = TableExtractor(
                endpoint=self.azure_endpoint,
                api_key=self.azure_api_key
            )
            print("[INFO] FLUJO 2: Extractor de tablas inicializado con Azure AI")
        else:
            print("[ADVERTENCIA] Sin credenciales de Azure — Solo se ejecutará FLUJO 1")

        # ── Inicializar exportador TOON (FLUJO 3) ──
        self.exportador_toon = ToonExporter()

        # ── Inicializar validador IA (FLUJO 4) ──
        self.validador = None
        if usar_validacion_ia and FLUJO4_DISPONIBLE:
            openai_endpoint, openai_key, openai_deployment = cargar_credenciales_openai()
            if openai_endpoint and openai_key:
                try:
                    self.validador = ValidadorNumeros(
                        endpoint=openai_endpoint,
                        api_key=openai_key,
                        deployment=openai_deployment or "gpt-4o"
                    )
                    print("[INFO] FLUJO 4: Validador IA inicializado con Azure OpenAI")
                except Exception as e:
                    print(f"[ADVERTENCIA] No se pudo inicializar FLUJO 4: {str(e)}")
                    self.validador = None
            else:
                print("[INFO] FLUJO 4: Deshabilitado (sin credenciales de Azure OpenAI)")
        elif not usar_validacion_ia:
            print("[INFO] FLUJO 4: Deshabilitado por configuración del usuario")

    def procesar_imagen(self, ruta_imagen: str, ejecutar_flujo1: bool = True,
                       ejecutar_flujo2: bool = True, mostrar_resultados: bool = False) -> dict:
        """
        Procesa una imagen ejecutando los 4 flujos:
        1. Enderezado
        2. Recorte de tablas
        3. Extracción TOON
        4. Validación IA (si está habilitado)
        """
        resultados = {
            'flujo1_completado': False,
            'flujo2_completado': False,
            'flujo3_completado': False,
            'flujo4_usado': self.validador is not None,
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
        print(f"[INFO] Validación IA: {'ACTIVADA ✅' if self.validador else 'DESACTIVADA (solo regex)'}")

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
                modo_efecto="original"
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
        # FLUJO 2, 3 y 4: RECORTE, EXTRACCIÓN Y VALIDACIÓN
        # ========================================================================
        if ejecutar_flujo2:
            print("\n" + "-"*80)
            if self.validador:
                print("EJECUTANDO FLUJOS 2, 3 Y 4: RECORTE, EXTRACCIÓN Y VALIDACIÓN IA")
            else:
                print("EJECUTANDO FLUJOS 2 Y 3: RECORTE Y EXTRACCIÓN DE DATOS")
            print("-"*80)

            if self.extractor_tablas is None:
                print("[ERROR] Se requieren credenciales de Azure para Flujos 2, 3 y 4.")
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
                    resultados['tablas_extraidas'].append(
                        os.path.join(carpeta_resultados_unica, nombre_img_tabla)
                    )

                    # Flujo 3 + 4: Extracción TOON (con o sin validación IA)
                    ruta_toon_base = os.path.join(carpeta_resultados_unica, f"{nombre_base}_datos")
                    exito_toon = self.exportador_toon.guardar_toon(
                        resultado_azure=analyze_result,
                        ruta_salida_base=ruta_toon_base,
                        nombre_documento=nombre_base,
                        validador=self.validador  # None si no hay FLUJO 4
                    )

                    if exito_toon:
                        resultados['flujo3_completado'] = True
                        resultados['archivo_toon'] = f"{ruta_toon_base}.txt"

        # ========================================================================
        # RESUMEN FINAL
        # ========================================================================
        print("\n" + "="*80)
        print("RESUMEN DEL PROCESAMIENTO")
        print("="*80)
        print(f"  FLUJO 1 (Enderezado):        {'✅ COMPLETADO' if resultados['flujo1_completado'] else '❌ FALLIDO'}")
        print(f"  FLUJO 2 (Recorte Tablas):    {'✅ COMPLETADO' if resultados['flujo2_completado'] else '❌ FALLIDO'}")
        print(f"  FLUJO 3 (Extracción TOON):   {'✅ COMPLETADO' if resultados['flujo3_completado'] else '❌ FALLIDO'}")
        print(f"  FLUJO 4 (Validación IA):     {'✅ ACTIVADO' if resultados['flujo4_usado'] else '⬜ NO USADO'}")

        if resultados['archivo_toon']:
            print(f"\n  Datos extraídos (TOON): {resultados['archivo_toon']}")

        print(f"\n  Resultados en: {os.path.abspath(carpeta_resultados_unica)}")
        print("="*80 + "\n")

        return resultados


def main():
    """
    Función principal para ejecutar el script desde línea de comandos.
    """
    if len(sys.argv) < 2:
        print("="*80)
        print("Procesador de Documentos - Pipeline Completo (4 Flujos)")
        print("="*80)
        print("\nUso: python procesador_documentos.py <ruta_imagen> [opciones]")
        print("\nArgumentos:")
        print("  <ruta_imagen>    Ruta a la imagen del documento a procesar")
        print("\nOpciones:")
        print("  --solo-flujo1    Ejecuta solo el enderezado del documento")
        print("  --solo-flujo2    Ejecuta solo la extracción de tablas")
        print("  --sin-ia         Deshabilita la validación IA (FLUJO 4)")
        print("  --mostrar        Muestra las imágenes durante el proceso")
        print("\nEjemplos:")
        print("  python procesador_documentos.py documento.jpg")
        print("  python procesador_documentos.py acta.png --mostrar")
        print("  python procesador_documentos.py foto.jpg --solo-flujo1")
        print("  python procesador_documentos.py acta.jpg --sin-ia")
        print("\nFlujos:")
        print("  FLUJO 1: Enderezado del documento (OpenCV)")
        print("  FLUJO 2: Recorte de tablas (Azure Document Intelligence)")
        print("  FLUJO 3: Extracción de datos en formato TOON")
        print("  FLUJO 4: Validación inteligente letra vs dígitos (Azure OpenAI)")
        print("\nConfiguración (.env):")
        print("  AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=tu_endpoint")
        print("  AZURE_DOCUMENT_INTELLIGENCE_KEY=tu_api_key")
        print("  AZURE_OPENAI_ENDPOINT=tu_endpoint_openai")
        print("  AZURE_OPENAI_KEY=tu_api_key_openai")
        print("  AZURE_OPENAI_DEPLOYMENT=gpt-4o")
        print("="*80)
        sys.exit(1)

    # Parsear argumentos
    ruta_imagen = sys.argv[1]
    solo_flujo1 = '--solo-flujo1' in sys.argv
    solo_flujo2 = '--solo-flujo2' in sys.argv
    sin_ia = '--sin-ia' in sys.argv
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
    procesador = ProcesadorDocumentos(usar_validacion_ia=not sin_ia)

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
