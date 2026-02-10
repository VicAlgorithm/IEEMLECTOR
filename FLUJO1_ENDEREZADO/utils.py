"""
Utilidades generales para FLUJO 1 - Enderezado de documentos.
Gestiona la creación de carpetas de salida.
"""

import os
from typing import Tuple


def crear_carpetas_salida() -> Tuple[str, str]:
    """
    Crea las carpetas necesarias para guardar las imágenes.

    Returns:
        Tupla con las rutas de las carpetas (proceso, resultados)
    """
    carpeta_proceso = os.path.join("..", "proceso")
    carpeta_resultados = os.path.join("..", "proceso")

    os.makedirs(carpeta_proceso, exist_ok=True)

    print(f"[INFO] Carpeta de proceso: {os.path.abspath(carpeta_proceso)}")
    print(f"[INFO] Carpeta de resultados: {os.path.abspath(carpeta_resultados)}")

    return carpeta_proceso, carpeta_resultados
