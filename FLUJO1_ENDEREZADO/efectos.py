"""
Efectos visuales para FLUJO 1 - Enderezado de documentos.
Aplica el efecto escáner profesional al documento enderezado.
"""

import cv2
import numpy as np


def aplicar_efecto_escaner(imagen: np.ndarray) -> np.ndarray:
    """
    Aplica el efecto escáner profesional al documento enderezado.

    Usa umbralización adaptativa para:
    - Convertir el fondo en blanco puro
    - Hacer el texto negro nítido
    - Eliminar sombras y variaciones de iluminación

    Args:
        imagen: Documento enderezado en color o escala de grises

    Returns:
        Imagen con efecto escáner (blanco y negro nítido)
    """
    # Convertir a escala de grises si está en color
    if len(imagen.shape) == 3:
        gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
    else:
        gris = imagen

    # Umbralización adaptativa gaussiana
    # Tamaño de bloque: 11 (debe ser impar), Constante C: 10
    imagen_escaneada = cv2.adaptiveThreshold(
        gris,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11,
        10
    )

    print("[INFO] Efecto escáner aplicado con umbralización adaptativa")

    return imagen_escaneada
