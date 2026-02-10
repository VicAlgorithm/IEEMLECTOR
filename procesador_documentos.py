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

# Importar módulos de los flujos
from document_scanner import escanear_documento
from table_extractor import TableExtractor, cargar_credenciales

import cv2


class ProcesadorDocumentos:
    """
    Clase principal para procesar documentos completos.
    Combina el enderezado y la extracción de tablas.
    """

    def __init__(self, azure_endpoint: Optional[str] = None, azure_api_key: Optional[str] = None):
        """
        Inicializa el procesador de documentos.

        Args:
            azure_endpoint: Endpoint de Azure AI (opcional, se puede cargar de .env)
            azure_api_key: API Key de Azure AI (opcional, se puede cargar de .env)
        """
        self.carpeta_proceso = "proceso"
        self.carpeta_recortes = "recortes"

        # Cargar credenciales de Azure
        if azure_endpoint and azure_api_key:
            self.azure_endpoint = azure_endpoint
            self.azure_api_key = azure_api_key
        else:
            self.azure_endpoint, self.azure_api_key = cargar_credenciales()

        # Inicializar extractor de tablas si hay credenciales
        self.extractor_tablas = None
        if self.azure_endpoint and self.azure_api_key:
            self.extractor_tablas = TableExtractor(
                endpoint=self.azure_endpoint,
                api_key=self.azure_api_key
            )
            print("[INFO] Procesador inicializado con Azure AI Document Intelligence")
        else:
            print("[ADVERTENCIA] Sin credenciales de Azure - Solo se ejecutará FLUJO 1")

    def procesar_imagen(self, ruta_imagen: str, ejecutar_flujo1: bool = True,
                       ejecutar_flujo2: bool = True, mostrar_resultados: bool = False) -> dict:
        """
        Procesa una imagen ejecutando los flujos especificados.

        Args:
            ruta_imagen: Ruta a la imagen de entrada
            ejecutar_flujo1: Si True, ejecuta el enderezado del documento
            ejecutar_flujo2: Si True, ejecuta la extracción de tablas
            mostrar_resultados: Si True, muestra las imágenes resultantes

        Returns:
            Diccionario con los resultados del procesamiento:
            {
                'flujo1_completado': bool,
                'flujo2_completado': bool,
                'imagen_enderezada': str (ruta),
                'tablas_extraidas': list[str] (rutas)
            }
        """
        resultados = {
            'flujo1_completado': False,
            'flujo2_completado': False,
            'imagen_enderezada': None,
            'tablas_extraidas': []
        }

        print("\n" + "="*80)
        print("INICIANDO PROCESAMIENTO DE DOCUMENTO")
        print("="*80)
        print(f"\n[INFO] Imagen de entrada: {ruta_imagen}")
        print(f"[INFO] FLUJO 1 (Enderezado): {'ACTIVADO' if ejecutar_flujo1 else 'DESACTIVADO'}")
        print(f"[INFO] FLUJO 2 (Extracción): {'ACTIVADO' if ejecutar_flujo2 else 'DESACTIVADO'}")

        # Verificar que el archivo existe
        if not os.path.exists(ruta_imagen):
            print(f"\n[ERROR] El archivo no existe: {ruta_imagen}")
            return resultados

        # Crear carpetas de salida
        os.makedirs(self.carpeta_proceso, exist_ok=True)
        os.makedirs(self.carpeta_recortes, exist_ok=True)

        # ========================================================================
        # FLUJO 1: ENDEREZADO DEL DOCUMENTO
        # ========================================================================
        imagen_para_flujo2 = ruta_imagen  # Por defecto usar la imagen original

        if ejecutar_flujo1:
            print("\n" + "-"*80)
            print("EJECUTANDO FLUJO 1: ENDEREZADO Y ESCANEO DE DOCUMENTO")
            print("-"*80 + "\n")

            # Ejecutar escaneo de documento
            documento_escaneado = escanear_documento(
                ruta_imagen=ruta_imagen,
                mostrar_pasos=mostrar_resultados,
                guardar_proceso=True,
                carpeta_proceso=self.carpeta_proceso
            )

            if documento_escaneado is not None:
                # Guardar documento enderezado
                nombre_base = Path(ruta_imagen).stem
                ruta_enderezada = os.path.join(self.carpeta_proceso, f"{nombre_base}_enderezado.jpg")
                cv2.imwrite(ruta_enderezada, documento_escaneado)

                resultados['flujo1_completado'] = True
                resultados['imagen_enderezada'] = ruta_enderezada
                imagen_para_flujo2 = ruta_enderezada  # Usar imagen enderezada para flujo 2

                print(f"\n[ÉXITO FLUJO 1] Documento enderezado guardado en: {ruta_enderezada}")
            else:
                print("\n[FALLO FLUJO 1] No se pudo enderezar el documento")
                print("[INFO] Se usará la imagen original para FLUJO 2")
        else:
            print("\n[INFO] FLUJO 1 omitido - usando imagen original")

        # ========================================================================
        # FLUJO 2: EXTRACCIÓN DE TABLAS
        # ========================================================================
        if ejecutar_flujo2:
            print("\n" + "-"*80)
            print("EJECUTANDO FLUJO 2: EXTRACCIÓN DE TABLAS CON AZURE AI")
            print("-"*80 + "\n")

            if self.extractor_tablas is None:
                print("[ERROR] No se puede ejecutar FLUJO 2 sin credenciales de Azure")
                print("[SOLUCIÓN] Configura las variables de entorno o archivo .env")
            else:
                # Ejecutar extracción de tablas
                nombre_base = Path(imagen_para_flujo2).stem
                nombre_salida = f"{nombre_base}_tabla_extraida.jpg"

                exito = self.extractor_tablas.procesar(
                    ruta_imagen=imagen_para_flujo2,
                    carpeta_salida=self.carpeta_recortes,
                    nombre_salida=nombre_salida,
                    mostrar=mostrar_resultados
                )

                if exito:
                    ruta_tabla = os.path.join(self.carpeta_recortes, nombre_salida)
                    resultados['flujo2_completado'] = True
                    resultados['tablas_extraidas'].append(ruta_tabla)
                    print(f"\n[ÉXITO FLUJO 2] Tabla extraída guardada en: {ruta_tabla}")
                else:
                    print("\n[FALLO FLUJO 2] No se pudo extraer la tabla")
        else:
            print("\n[INFO] FLUJO 2 omitido")

        # ========================================================================
        # RESUMEN FINAL
        # ========================================================================
        print("\n" + "="*80)
        print("RESUMEN DEL PROCESAMIENTO")
        print("="*80)
        print(f"\n✓ FLUJO 1 (Enderezado):    {'COMPLETADO' if resultados['flujo1_completado'] else 'NO EJECUTADO/FALLIDO'}")
        print(f"✓ FLUJO 2 (Extracción):    {'COMPLETADO' if resultados['flujo2_completado'] else 'NO EJECUTADO/FALLIDO'}")

        if resultados['imagen_enderezada']:
            print(f"\n📄 Documento enderezado: {resultados['imagen_enderezada']}")

        if resultados['tablas_extraidas']:
            print(f"\n📊 Tablas extraídas:")
            for i, ruta_tabla in enumerate(resultados['tablas_extraidas'], 1):
                print(f"   {i}. {ruta_tabla}")

        print("\n" + "="*80 + "\n")

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
