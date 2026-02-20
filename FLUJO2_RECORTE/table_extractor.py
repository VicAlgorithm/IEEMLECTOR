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

# Manejo seguro de importaciones de Azure
AZURE_AVAILABLE = False
try:
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.core.credentials import AzureKeyCredential
    AZURE_AVAILABLE = True
except ImportError:
    print("[ADVERTENCIA] Librerías de Azure no encontradas. FLUJO 2 no estará disponible.")

from credenciales import cargar_credenciales
# Importar analisis_azure solo si Azure está disponible o manejarlo internamente
try:
    from analisis_azure import analizar_documento, extraer_tablas_interes
except ImportError:
    pass # Se manejará en el método procesar

from procesamiento_imagen import (calcular_bounding_box, recortar_imagen,
                                   guardar_imagen, mostrar_imagen)

# Importar efectos del Flujo 1
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from FLUJO1_ENDEREZADO.efectos import aplicar_efecto_escaner
except ImportError:
    print("[ADVERTENCIA] No se pudo importar FLUJO1_ENDEREZADO.efectos. Los filtros no estarán disponibles.")
    def aplicar_efecto_escaner(img, modo): return img


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
        if not AZURE_AVAILABLE:
            print("[ERROR] No se pueden inicializar las credenciales de Azure porque faltan las librerías.")
            print("Instala las dependencias: pip install azure-ai-documentintelligence azure-core")
            self.client = None
            return

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
        Pipeline completo: analiza el documento, extrae las tablas y las guarda.

        Pasos:
        1. Envía la imagen a Azure AI (analisis_azure.py)
        2. Extrae los polígonos de las tablas de interés (analisis_azure.py)
        3. Para cada tabla:
            a. Calcula el bounding box rectangular
            b. Recorta la región de la tabla
            c. Guarda el recorte en disco
            d. Muestra el resultado (opcional)

        Args:
            ruta_imagen:    Ruta a la imagen de entrada
            carpeta_salida: Carpeta donde guardar el resultado
            nombre_salida:  Nombre base del archivo de salida
            mostrar:        Si True, muestra la imagen resultante en pantalla

        Returns:
            True si al menos una tabla fue procesada exitosamente
        """
        # 1. Analizar documento con Azure AI
        if self.client is None:
            print("[ERROR] Cliente de Azure no inicializado due a falta de librerías o error.")
            return False

        resultado = analizar_documento(self.client, ruta_imagen)
        if resultado is None:
            print("\n[FALLO] No se pudo analizar el documento")
            return False

        # 2. Extraer polígonos de las tablas de interés
        # Se busca incluir el encabezado "TOTAL DE VOTOS SACADOS DE LAS URNAS" (Sección verde)
        texto_encabezado = ["TOTAL DE VOTOS SACADOS DE LAS URNAS", "Copie del apartado 7", "7 TOTAL DE VOTOS"]
        polygons = extraer_tablas_interes(resultado, texto_encabezado, filas_tabla2=16)
        
        if not polygons:
            print("\n[FALLO] No se pudieron extraer tablas")
            return False

        print(f"\n[INFO] Procesando {len(polygons)} tablas encontradas...")
        exito_global = False

        # Preparar nombre base
        if nombre_salida is None:
            nombre_base = Path(ruta_imagen).stem
        else:
            nombre_base = Path(nombre_salida).stem

        # Limpieza de archivos previos para esta imagen
        try:
            path_salida = Path(carpeta_salida)
            if path_salida.exists():
                for archivo_previo in path_salida.glob(f"{nombre_base}_tabla_*.jpg"):
                    archivo_previo.unlink()
        except Exception as e:
            print(f"[ADVERTENCIA] No se pudieron limpiar archivos previos: {e}")

        for idx, polygon in enumerate(polygons):
            print(f"\n--- Procesando Tabla #{idx + 1} ---")
            
            # 3. Calcular bounding box
            x_min, y_min, x_max, y_max = calcular_bounding_box(polygon)

            # 4. Recortar imagen
            imagen_recortada = recortar_imagen(ruta_imagen, x_min, y_min, x_max, y_max)
            if imagen_recortada is None:
                print(f"[FALLO] No se pudo recortar la tabla #{idx + 1}")
                continue

            # 5. Solo binarizado (blanco y negro) solicitado por el usuario
            filtros = ["blanco_negro"]
            
            print(f"[INFO] Generando recorte blanco y negro para la tabla #{idx + 1}...")
            
            for modo in filtros:
                # Aplicar el filtro a la imagen recortada
                imagen_filtrada = aplicar_efecto_escaner(imagen_recortada, modo=modo)
                
                # Definir nombre de archivo: nombre_tabla_1.jpg (solo BN)
                sufijo = f"_TABLA_{idx + 1}.jpg"
                nombre_archivo = f"{nombre_base}{sufijo}"
                
                # Guardar resultado
                guardar_imagen(imagen_filtrada, carpeta_salida, nombre_archivo)
                
                # Mostrar si se solicita
                if mostrar:
                    mostrar_imagen(imagen_filtrada, titulo=f"Tabla {idx + 1} - Binarizada")

            exito_global = True

        print("\n" + "="*70)
        if exito_global:
            print("PROCESO COMPLETADO EXITOSAMENTE")
        else:
            print("PROCESO FINALIZADO CON ERRORES")
        print("="*70 + "\n")

        return resultado if exito_global else None


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
