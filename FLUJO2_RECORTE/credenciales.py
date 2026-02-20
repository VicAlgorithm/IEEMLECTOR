"""
Gestión de credenciales de Azure - FLUJO 2 y FLUJO 4
=====================================================
Carga las credenciales desde variables de entorno o archivo .env.

Soporta:
  - Azure AI Document Intelligence (FLUJO 2)
  - Azure OpenAI Service (FLUJO 4)
"""

import os
from typing import Tuple, Optional
from dotenv import load_dotenv


def cargar_credenciales() -> Tuple[Optional[str], Optional[str]]:
    """
    Carga las credenciales de Azure Document Intelligence desde variables de entorno.

    Returns:
        Tupla (endpoint, api_key). Retorna (None, None) si no se encuentran.
    """
    # Cargar .env desde el directorio donde está este script
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    load_dotenv(env_path)

    endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    api_key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

    if not endpoint or not api_key:
        print("[ERROR] No se encontraron las credenciales de Azure Document Intelligence")
        print("\nConfiguración requerida:")
        print("  Opción 1: Crear archivo .env con:")
        print("    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=tu_endpoint")
        print("    AZURE_DOCUMENT_INTELLIGENCE_KEY=tu_api_key")
        print("\n  Opción 2: Establecer variables de entorno del sistema")
        return None, None

    return endpoint, api_key


def cargar_credenciales_openai() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Carga las credenciales de Azure OpenAI desde variables de entorno.

    Returns:
        Tupla (endpoint, api_key, deployment). Retorna (None, None, None) si no se encuentran.
    """
    # Cargar .env desde el directorio donde está este script
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    load_dotenv(env_path)

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_KEY")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

    if not endpoint or not api_key:
        print("[INFO] No se encontraron credenciales de Azure OpenAI (FLUJO 4 deshabilitado)")
        print("  Para habilitar validación con IA, agrega a tu .env:")
        print("    AZURE_OPENAI_ENDPOINT=https://tu-recurso.openai.azure.com/")
        print("    AZURE_OPENAI_KEY=tu_api_key")
        print("    AZURE_OPENAI_DEPLOYMENT=gpt-4o  (opcional, por defecto gpt-4o)")
        return None, None, None

    return endpoint, api_key, deployment
