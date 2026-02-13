"""
Efectos visuales para FLUJO 1 - Enderezado de documentos.
Modos disponibles: blanco_negro, color_suave, gris, original
"""

import cv2
import numpy as np


def aplicar_efecto_escaner(imagen: np.ndarray, modo: str = "blanco_negro") -> np.ndarray:
    """
    Aplica efecto de escaner al documento enderezado.

    Modos:
        blanco_negro:  Umbral adaptativo, texto negro sobre fondo blanco puro.
        color_suave:   CLAHE en espacio LAB, conserva colores (tintas, sellos).
        gris:          CLAHE en escala de grises, buen contraste sin color.
        original:      Sin filtro, imagen tal cual.

    Args:
        imagen: Documento enderezado (BGR o escala de grises)
        modo: Tipo de efecto a aplicar

    Returns:
        Imagen con el efecto aplicado
    """
    if modo == "blanco_negro":
        resultado = _blanco_negro(imagen)
    elif modo == "color_suave":
        resultado = _color_suave(imagen)
    elif modo == "gris":
        resultado = _gris(imagen)
    elif modo == "super_contraste":
        resultado = _super_contraste(imagen)
    elif modo == "original":
        resultado = imagen.copy()
    else:
        print(f"[ADVERTENCIA] Modo '{modo}' no reconocido, usando blanco_negro")
        resultado = _blanco_negro(imagen)

    print(f"[INFO] Efecto escaner aplicado: {modo}")
    return resultado


def _super_contraste(imagen: np.ndarray) -> np.ndarray:
    """
    Filtro de rescate: extrae el texto más oscuro que su fondo inmediato.
    Ideal para lápiz tenue y hojas con sombras de dobleces.
    """
    if len(imagen.shape) == 3:
        gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
    else:
        gris = imagen

    # 1. Extraer solo los detalles oscuros (texto) usando Morphological Top-Hat
    # El kernel de 15x15 busca detalles pequeños como trazos de letras
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    blackhat = cv2.morphologyEx(gris, cv2.MORPH_BLACKHAT, kernel)
    
    # 2. Invertir y normalizar para que el texto sea negro sobre fondo blanco
    res = cv2.bitwise_not(blackhat)
    res = cv2.normalize(res, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)

    # 3. Aplicar CLAHE suave para dar definición sin crear ruido
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    final = clahe.apply(res)
    
    return final


def _blanco_negro(imagen: np.ndarray) -> np.ndarray:
    """Umbral adaptativo: texto negro nitido, fondo blanco puro."""
    if len(imagen.shape) == 3:
        gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
    else:
        gris = imagen

    return cv2.adaptiveThreshold(
        gris, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11, 10
    )


def _color_suave(imagen: np.ndarray) -> np.ndarray:
    """CLAHE en espacio LAB: limpia iluminacion, conserva colores."""
    if len(imagen.shape) < 3:
        imagen = cv2.cvtColor(imagen, cv2.COLOR_GRAY2BGR)

    lab = cv2.cvtColor(imagen, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    l = clahe.apply(l)

    lab = cv2.merge((l, a, b))
    resultado = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    return cv2.convertScaleAbs(resultado, alpha=1.05, beta=5)


def _gris(imagen: np.ndarray) -> np.ndarray:
    """CLAHE en escala de grises: buen contraste sin color."""
    if len(imagen.shape) == 3:
        gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
    else:
        gris = imagen

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gris)
