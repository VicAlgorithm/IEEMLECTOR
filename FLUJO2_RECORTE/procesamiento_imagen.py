"""
Procesamiento de imágenes para FLUJO 2 - Extracción de tablas.
Contiene las funciones de cálculo de bounding box, recorte, guardado
y visualización de imágenes.
"""

import cv2
import numpy as np
import os
from typing import Tuple, Optional


def calcular_bounding_box(polygon: list) -> Tuple[int, int, int, int]:
    """
    Calcula el bounding box rectangular a partir de un polígono.

    El polígono viene en formato [x1, y1, x2, y2, x3, y3, x4, y4]

    Args:
        polygon: Lista de coordenadas del polígono

    Returns:
        Tupla (x_min, y_min, x_max, y_max)
    """
    coords_x = [polygon[i] for i in range(0, len(polygon), 2)]
    coords_y = [polygon[i] for i in range(1, len(polygon), 2)]

    x_min = int(min(coords_x))
    y_min = int(min(coords_y))
    x_max = int(max(coords_x))
    y_max = int(max(coords_y))

    print(f"\n[INFO] Bounding Box calculado:")
    print(f"  - x_min: {x_min}, y_min: {y_min}")
    print(f"  - x_max: {x_max}, y_max: {y_max}")
    print(f"  - Ancho: {x_max - x_min} px, Alto: {y_max - y_min} px")

    return x_min, y_min, x_max, y_max


def recortar_imagen(ruta_imagen: str, x_min: int, y_min: int,
                    x_max: int, y_max: int) -> Optional[np.ndarray]:
    """
    Recorta la región de la tabla de la imagen usando OpenCV.

    Args:
        ruta_imagen: Ruta a la imagen original
        x_min, y_min, x_max, y_max: Coordenadas del bounding box

    Returns:
        Imagen recortada como array de NumPy o None si falla
    """
    print("\n[INFO] Recortando imagen con OpenCV...")

    imagen = cv2.imread(ruta_imagen)

    if imagen is None:
        print(f"[ERROR] No se pudo cargar la imagen: {ruta_imagen}")
        return None

    alto_original, ancho_original = imagen.shape[:2]
    print(f"[INFO] Dimensiones de imagen original: {ancho_original}x{alto_original}")

    # Validar coordenadas dentro de los límites
    x_min = max(0, x_min)
    y_min = max(0, y_min)
    x_max = min(ancho_original, x_max)
    y_max = min(alto_original, y_max)

    imagen_recortada = imagen[y_min:y_max, x_min:x_max]

    alto_recorte, ancho_recorte = imagen_recortada.shape[:2]
    print(f"[INFO] Recorte completado: {ancho_recorte}x{alto_recorte}")

    return imagen_recortada


def guardar_imagen(imagen: np.ndarray, carpeta_salida: str,
                   nombre_archivo: str = "tabla_extraida.jpg") -> str:
    """
    Guarda la imagen recortada en la carpeta de salida.

    Args:
        imagen: Imagen recortada
        carpeta_salida: Carpeta donde guardar
        nombre_archivo: Nombre del archivo de salida

    Returns:
        Ruta completa del archivo guardado
    """
    os.makedirs(carpeta_salida, exist_ok=True)

    ruta_salida = os.path.join(carpeta_salida, nombre_archivo)
    cv2.imwrite(ruta_salida, imagen)

    print(f"\n[INFO] Imagen guardada en: {os.path.abspath(ruta_salida)}")

    return ruta_salida


def mostrar_imagen(imagen: np.ndarray, titulo: str = "Tabla Extraída"):
    """
    Muestra la imagen en una ventana de OpenCV.

    Args:
        imagen: Imagen a mostrar
        titulo: Título de la ventana
    """
    print(f"\n[INFO] Mostrando imagen: {titulo}")
    print("[INFO] Presiona cualquier tecla para cerrar la ventana...")

    cv2.imshow(titulo, imagen)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
