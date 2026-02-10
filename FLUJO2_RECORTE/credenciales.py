"""
Gestión de credenciales de Azure AI para FLUJO 2 - Extracción de tablas.
Carga las credenciales desde variables de entorno o archivo .env.
"""

import os
from typing import Tuple, Optional
from dotenv import load_dotenv


def cargar_credenciales() -> Tuple[Optional[str], Optional[str]]:
    """
    Carga las credenciales de Azure desde variables de entorno.

    Returns:
        Tupla (endpoint, api_key). Retorna (None, None) si no se encuentran.
    """
    load_dotenv()

    endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    api_key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

    if not endpoint or not api_key:
        print("[ERROR] No se encontraron las credenciales de Azure")
        print("\nConfiguración requerida:")
        print("  Opción 1: Crear archivo .env con:")
        print("    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=tu_endpoint")
        print("    AZURE_DOCUMENT_INTELLIGENCE_KEY=tu_api_key")
        print("\n  Opción 2: Establecer variables de entorno del sistema")
        return None, None

    return endpoint, api_key
