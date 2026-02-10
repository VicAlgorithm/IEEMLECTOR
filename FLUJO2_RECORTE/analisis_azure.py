"""
Análisis de documentos con Azure AI para FLUJO 2 - Extracción de tablas.
Contiene las funciones de análisis y extracción de datos de tablas.
"""

from typing import Optional, List
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult


def analizar_documento(client: DocumentIntelligenceClient, ruta_imagen: str) -> Optional[AnalyzeResult]:
    """
    Envía la imagen a Azure AI Document Intelligence para análisis.

    Args:
        client: Cliente inicializado de Azure AI
        ruta_imagen: Ruta al archivo de imagen

    Returns:
        Resultado del análisis o None si falla
    """
    print("\n" + "="*70)
    print("INICIANDO ANÁLISIS CON AZURE AI DOCUMENT INTELLIGENCE")
    print("="*70 + "\n")

    try:
        with open(ruta_imagen, "rb") as f:
            imagen_bytes = f.read()

        print(f"[INFO] Imagen cargada: {ruta_imagen}")
        print(f"[INFO] Tamaño del archivo: {len(imagen_bytes)} bytes")
        print("[INFO] Enviando imagen a Azure AI...")
        print("[INFO] Modelo: prebuilt-layout")

        poller = client.begin_analyze_document(
            model_id="prebuilt-layout",
            body=imagen_bytes,
            content_type="application/octet-stream"
        )

        print("[INFO] Esperando respuesta de Azure AI...")
        resultado = poller.result()

        print("[INFO] Análisis completado exitosamente")

        if hasattr(resultado, 'tables') and resultado.tables:
            print(f"[INFO] Tablas detectadas: {len(resultado.tables)}")
        else:
            print("[ADVERTENCIA] No se detectaron tablas en el documento")

        return resultado

    except Exception as e:
        print(f"[ERROR] Error al analizar documento con Azure AI: {str(e)}")
        return None


def extraer_primera_tabla(resultado: AnalyzeResult) -> Optional[List[float]]:
    """
    Extrae el polígono de la primera tabla detectada.

    Args:
        resultado: Resultado del análisis de Azure AI

    Returns:
        Lista de coordenadas del polígono [x1, y1, x2, y2, x3, y3, x4, y4] o None
    """
    if not hasattr(resultado, 'tables') or not resultado.tables:
        print("[ERROR] No se encontraron tablas en el resultado")
        return None

    primera_tabla = resultado.tables[0]
    print(f"\n[INFO] Procesando primera tabla:")
    print(f"  - Filas: {primera_tabla.row_count}")
    print(f"  - Columnas: {primera_tabla.column_count}")

    if not hasattr(primera_tabla, 'bounding_regions') or not primera_tabla.bounding_regions:
        print("[ERROR] La tabla no tiene información de bounding_regions")
        return None

    primera_region = primera_tabla.bounding_regions[0]

    if not hasattr(primera_region, 'polygon') or not primera_region.polygon:
        print("[ERROR] La región no tiene información de polígono")
        return None

    polygon = primera_region.polygon
    print(f"[INFO] Polígono extraído: {polygon}")

    return polygon
