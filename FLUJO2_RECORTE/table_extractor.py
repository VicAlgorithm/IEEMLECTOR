"""
Pipeline principal de extracción de tablas - FLUJO 2
=====================================================
Coordina el proceso completo de detección y recorte de tablas con Azure AI.

Módulos utilizados:
  - credenciales.py        → cargar_credenciales
  - analisis_azure.py      → analizar_documento, extraer_primera_tabla
  - procesamiento_imagen.py → calcular_bounding_box, recortar_imagen,
                               guardar_imagen, mostrar_imagen
"""

import os
import sys
from typing import Optional
from pathlib import Path

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

from credenciales import cargar_credenciales
from analisis_azure import analizar_documento, extraer_primera_tabla
from procesamiento_imagen import (calcular_bounding_box, recortar_imagen,
                                   guardar_imagen, mostrar_imagen)


class TableExtractor:
    """
    Extrae y recorta tablas de documentos usando Azure AI Document Intelligence.

    Uso básico:
        extractor = TableExtractor(endpoint, api_key)
        extractor.procesar("imagen.jpg", carpeta_salida="recortes/")
    """

    def __init__(self, endpoint: str, api_key: str):
        """
        Inicializa el cliente de Azure AI Document Intelligence.

        Args:
            endpoint: URL del endpoint de Azure AI
            api_key:  Clave de API de Azure AI
        """
        self.endpoint = endpoint
        self.api_key = api_key
        self.client = DocumentIntelligenceClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(api_key)
        )
        print(f"[INFO] Cliente de Azure AI inicializado")
        print(f"[INFO] Endpoint: {endpoint}")

    def procesar(self, ruta_imagen: str, carpeta_salida: str = "../recortes",
                 nombre_salida: Optional[str] = None, mostrar: bool = True) -> bool:
        """
        Pipeline completo: analiza el documento, extrae la tabla y la guarda.

        Pasos:
        1. Envía la imagen a Azure AI (analisis_azure.py)
        2. Extrae el polígono de la primera tabla (analisis_azure.py)
        3. Calcula el bounding box rectangular (procesamiento_imagen.py)
        4. Recorta la región de la tabla (procesamiento_imagen.py)
        5. Guarda el recorte en disco (procesamiento_imagen.py)
        6. Muestra el resultado en pantalla (procesamiento_imagen.py) [opcional]

        Args:
            ruta_imagen:    Ruta a la imagen de entrada
            carpeta_salida: Carpeta donde guardar el resultado
            nombre_salida:  Nombre del archivo de salida (se genera automáticamente si es None)
            mostrar:        Si True, muestra la imagen resultante en pantalla

        Returns:
            True si el proceso fue exitoso, False en caso contrario
        """
        # 1. Analizar documento con Azure AI
        resultado = analizar_documento(self.client, ruta_imagen)
        if resultado is None:
            print("\n[FALLO] No se pudo analizar el documento")
            return False

        # 2. Extraer polígono de la primera tabla
        polygon = extraer_primera_tabla(resultado)
        if polygon is None:
            print("\n[FALLO] No se pudo extraer la tabla")
            return False

        # 3. Calcular bounding box
        x_min, y_min, x_max, y_max = calcular_bounding_box(polygon)

        # 4. Recortar imagen
        imagen_recortada = recortar_imagen(ruta_imagen, x_min, y_min, x_max, y_max)
        if imagen_recortada is None:
            print("\n[FALLO] No se pudo recortar la imagen")
            return False

        # 5. Guardar resultado
        if nombre_salida is None:
            nombre_base = Path(ruta_imagen).stem
            nombre_salida = f"{nombre_base}_tabla_extraida.jpg"
        guardar_imagen(imagen_recortada, carpeta_salida, nombre_salida)

        # 6. Mostrar imagen (opcional)
        if mostrar:
            mostrar_imagen(imagen_recortada)

        print("\n" + "="*70)
        print("PROCESO COMPLETADO EXITOSAMENTE")
        print("="*70 + "\n")

        return True


def main():
    """
    Punto de entrada para ejecutar el script desde línea de comandos.
    Uso: python table_extractor.py <ruta_imagen> [nombre_salida]
    """
    if len(sys.argv) < 2:
        print("="*70)
        print("Script de Extracción de Tablas con Azure AI Document Intelligence")
        print("="*70)
        print("\nUso: python table_extractor.py <ruta_imagen> [nombre_salida]")
        print("\nEjemplos:")
        print("  python table_extractor.py documento.jpg")
        print("  python table_extractor.py acta.png tabla_resultados.jpg")
        print("\nConfiguración:")
        print("  Crea un archivo .env con tus credenciales de Azure:")
        print("    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=tu_endpoint")
        print("    AZURE_DOCUMENT_INTELLIGENCE_KEY=tu_api_key")
        sys.exit(1)

    ruta_entrada = sys.argv[1]
    nombre_salida = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(ruta_entrada):
        print(f"[ERROR] El archivo no existe: {ruta_entrada}")
        sys.exit(1)

    endpoint, api_key = cargar_credenciales()
    if not endpoint or not api_key:
        sys.exit(1)

    extractor = TableExtractor(endpoint=endpoint, api_key=api_key)
    exito = extractor.procesar(
        ruta_imagen=ruta_entrada,
        carpeta_salida="../recortes",
        nombre_salida=nombre_salida,
        mostrar=True
    )

    if not exito:
        print("\n[FALLO] El proceso no se completó correctamente")
        sys.exit(1)


if __name__ == "__main__":
    main()
