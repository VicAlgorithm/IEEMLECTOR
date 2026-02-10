"""
Operaciones geométricas para FLUJO 1 - Enderezado de documentos.
Contiene las funciones de ordenamiento de puntos, detección de contorno
y corrección de perspectiva.
"""

import cv2
import numpy as np
from typing import Optional


def ordenar_puntos(puntos: np.ndarray) -> np.ndarray:
    """
    Ordena los 4 puntos del documento en el orden:
    [Superior-Izquierda, Superior-Derecha, Inferior-Derecha, Inferior-Izquierda]

    Lógica:
    - La suma (x+y) más pequeña → Superior-Izquierda
    - La suma (x+y) más grande  → Inferior-Derecha
    - La diferencia (y-x) más pequeña → Superior-Derecha
    - La diferencia (y-x) más grande  → Inferior-Izquierda

    Args:
        puntos: Array de 4 puntos (x, y)

    Returns:
        Array ordenado de 4 puntos
    """
    puntos_ordenados = np.zeros((4, 2), dtype=np.float32)

    suma = puntos.sum(axis=1)
    diferencia = np.diff(puntos, axis=1)

    puntos_ordenados[0] = puntos[np.argmin(suma)]       # Superior-Izquierda
    puntos_ordenados[2] = puntos[np.argmax(suma)]       # Inferior-Derecha
    puntos_ordenados[1] = puntos[np.argmin(diferencia)] # Superior-Derecha
    puntos_ordenados[3] = puntos[np.argmax(diferencia)] # Inferior-Izquierda

    print("[INFO] Puntos ordenados correctamente")
    return puntos_ordenados


def encontrar_contorno_documento(imagen_bordes: np.ndarray) -> Optional[np.ndarray]:
    """
    Encuentra el contorno más grande que tenga exactamente 4 puntos (documento).

    Args:
        imagen_bordes: Imagen con bordes detectados

    Returns:
        Contorno aproximado con 4 puntos o None si no se encuentra
    """
    contornos, _ = cv2.findContours(imagen_bordes.copy(),
                                     cv2.RETR_EXTERNAL,
                                     cv2.CHAIN_APPROX_SIMPLE)

    contornos = sorted(contornos, key=cv2.contourArea, reverse=True)
    print(f"[INFO] Se encontraron {len(contornos)} contornos")

    contorno_documento = None

    for i, contorno in enumerate(contornos[:10]):  # Solo los 10 más grandes
        perimetro = cv2.arcLength(contorno, True)
        # Epsilon = 2% del perímetro
        aproximacion = cv2.approxPolyDP(contorno, 0.02 * perimetro, True)

        if len(aproximacion) == 4:
            contorno_documento = aproximacion
            print(f"[INFO] Documento encontrado en contorno #{i+1} con área: {cv2.contourArea(contorno):.0f}")
            break

    if contorno_documento is None:
        print("[ERROR] No se pudo encontrar un contorno con exactamente 4 puntos")
        print("[SUGERENCIA] Intenta con mejor iluminación o fondo más contrastado")

    return contorno_documento


def transformacion_perspectiva(imagen: np.ndarray, puntos: np.ndarray) -> np.ndarray:
    """
    Aplica transformación de perspectiva para enderezar el documento.
    Convierte el documento de una vista inclinada a una vista frontal perfecta.

    Args:
        imagen: Imagen original
        puntos: 4 puntos del documento (sin ordenar)

    Returns:
        Imagen del documento enderezado (vista cenital)
    """
    puntos_ordenados = ordenar_puntos(puntos.reshape(4, 2))
    (sup_izq, sup_der, inf_der, inf_izq) = puntos_ordenados

    # Calcular dimensiones del documento enderezado
    ancho_superior = np.sqrt(((sup_der[0] - sup_izq[0]) ** 2) + ((sup_der[1] - sup_izq[1]) ** 2))
    ancho_inferior = np.sqrt(((inf_der[0] - inf_izq[0]) ** 2) + ((inf_der[1] - inf_izq[1]) ** 2))
    ancho_maximo = max(int(ancho_superior), int(ancho_inferior))

    alto_izquierdo = np.sqrt(((sup_izq[0] - inf_izq[0]) ** 2) + ((sup_izq[1] - inf_izq[1]) ** 2))
    alto_derecho = np.sqrt(((sup_der[0] - inf_der[0]) ** 2) + ((sup_der[1] - inf_der[1]) ** 2))
    alto_maximo = max(int(alto_izquierdo), int(alto_derecho))

    # Coordenadas de destino para la vista frontal
    puntos_destino = np.array([
        [0, 0],
        [ancho_maximo - 1, 0],
        [ancho_maximo - 1, alto_maximo - 1],
        [0, alto_maximo - 1]
    ], dtype=np.float32)

    matriz = cv2.getPerspectiveTransform(puntos_ordenados, puntos_destino)
    documento_enderezado = cv2.warpPerspective(imagen, matriz, (ancho_maximo, alto_maximo))

    print(f"[INFO] Transformación de perspectiva aplicada")
    print(f"[INFO] Dimensiones del documento enderezado: {ancho_maximo}x{alto_maximo}")

    return documento_enderezado
