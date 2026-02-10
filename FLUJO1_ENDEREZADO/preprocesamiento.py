"""
Preprocesamiento de imagen para FLUJO 1 - Enderezado de documentos.
Contiene las funciones de redimensionado, conversión a grises y detección de bordes.
"""

import cv2
import numpy as np
from typing import Tuple


def redimensionar_imagen(imagen: np.ndarray, ancho_objetivo: int = 500) -> Tuple[np.ndarray, float]:
    """
    Redimensiona la imagen manteniendo la proporción (aspect ratio).

    Args:
        imagen: Imagen original en formato numpy array
        ancho_objetivo: Ancho al que se redimensionará la imagen para procesamiento rápido

    Returns:
        Tupla (imagen_redimensionada, ratio) donde ratio sirve para
        mapear coordenadas de vuelta a la imagen original.
    """
    alto_original, ancho_original = imagen.shape[:2]
    ratio = ancho_original / float(ancho_objetivo)
    nuevo_ancho = ancho_objetivo
    nuevo_alto = int(alto_original / ratio)

    imagen_redimensionada = cv2.resize(imagen, (nuevo_ancho, nuevo_alto),
                                       interpolation=cv2.INTER_AREA)

    print(f"[INFO] Imagen redimensionada de {ancho_original}x{alto_original} a {nuevo_ancho}x{nuevo_alto}")
    print(f"[INFO] Ratio de escala: {ratio:.2f}")

    return imagen_redimensionada, ratio


def preprocesar_imagen(imagen: np.ndarray) -> np.ndarray:
    """
    Preprocesa la imagen para mejorar la detección de bordes.

    Pasos:
    1. Conversión a escala de grises
    2. Aplicación de filtro Gaussiano para reducir ruido

    Args:
        imagen: Imagen en color (BGR)

    Returns:
        Imagen en escala de grises suavizada
    """
    gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
    print("[INFO] Imagen convertida a escala de grises")

    # Kernel 5x5: buen balance entre reducción de ruido y preservación de bordes
    gris_suavizado = cv2.GaussianBlur(gris, (5, 5), 0)
    print("[INFO] Filtro Gaussiano aplicado (kernel 5x5)")

    return gris_suavizado


def detectar_bordes(imagen_gris: np.ndarray) -> np.ndarray:
    """
    Detecta los bordes en la imagen usando el algoritmo de Canny.

    Args:
        imagen_gris: Imagen en escala de grises preprocesada

    Returns:
        Mapa de bordes binario
    """
    # Umbral inferior: 75, Umbral superior: 200
    bordes = cv2.Canny(imagen_gris, 75, 200)
    print("[INFO] Detección de bordes Canny completada")

    return bordes
