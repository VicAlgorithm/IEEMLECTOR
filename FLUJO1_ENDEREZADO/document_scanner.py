"""
Pipeline principal de escaneo de documentos - FLUJO 1
======================================================
Coordina el proceso completo de enderezado con efecto CamScanner.

Módulos utilizados:
  - utils.py          → crear_carpetas_salida
  - preprocesamiento.py → redimensionar_imagen, preprocesar_imagen, detectar_bordes
  - geometria.py      → encontrar_contorno_documento, transformacion_perspectiva
  - efectos.py        → aplicar_efecto_escaner
"""

import cv2
import os
import sys
from typing import Optional

from utils import crear_carpetas_salida
from preprocesamiento import redimensionar_imagen, preprocesar_imagen, detectar_bordes
from geometria import encontrar_contorno_documento, transformacion_perspectiva
from efectos import aplicar_efecto_escaner


def escanear_documento(ruta_imagen: str, mostrar_pasos: bool = False,
                       guardar_proceso: bool = False,
                       carpeta_proceso: str = "proceso") -> Optional[object]:
    """
    Ejecuta el pipeline completo de escaneo de documentos.

    Pasos:
    1. Carga la imagen original
    2. Redimensiona para procesamiento rápido
    3. Preprocesa (grises + desenfoque)
    4. Detecta bordes (Canny)
    5. Encuentra contorno del documento
    6. Escala puntos a resolución original
    7. Aplica transformación de perspectiva
    8. Aplica efecto escáner

    Args:
        ruta_imagen:     Ruta al archivo de imagen
        mostrar_pasos:   Si True, muestra imágenes intermedias en pantalla
        guardar_proceso: Si True, guarda las imágenes de cada paso
        carpeta_proceso: Carpeta donde guardar las imágenes del proceso

    Returns:
        Imagen del documento escaneado (numpy array) o None si falla
    """
    print("\n" + "="*70)
    print("INICIANDO PROCESO DE ESCANEO DE DOCUMENTO")
    print("="*70 + "\n")

    # 1. Cargar imagen original
    imagen_original = cv2.imread(ruta_imagen)
    if imagen_original is None:
        print(f"[ERROR] No se pudo cargar la imagen: {ruta_imagen}")
        return None
    print(f"[INFO] Imagen cargada exitosamente: {ruta_imagen}")

    # 2. Redimensionar para procesamiento rápido
    imagen_procesamiento, ratio = redimensionar_imagen(imagen_original, ancho_objetivo=500)

    # 3. Preprocesamiento (grises + filtro gaussiano)
    imagen_gris = preprocesar_imagen(imagen_procesamiento)
    if mostrar_pasos:
        cv2.imshow("1. Preprocesamiento - Escala de Grises", imagen_gris)
    if guardar_proceso:
        ruta = os.path.join(carpeta_proceso, "1_escala_grises.jpg")
        cv2.imwrite(ruta, imagen_gris)
        print(f"[GUARDADO] {ruta}")

    # 4. Detección de bordes
    bordes = detectar_bordes(imagen_gris)
    if mostrar_pasos:
        cv2.imshow("2. Detección de Bordes - Canny", bordes)
    if guardar_proceso:
        ruta = os.path.join(carpeta_proceso, "2_deteccion_bordes.jpg")
        cv2.imwrite(ruta, bordes)
        print(f"[GUARDADO] {ruta}")

    # 5. Encontrar contorno del documento
    contorno_documento = encontrar_contorno_documento(bordes)
    if contorno_documento is None:
        print("\n[FALLO] No se detectaron 4 puntos claros del documento")
        print("[SOLUCIÓN] Recomendaciones:")
        print("  - Asegúrate de que el documento tenga un borde claro y contrastado")
        print("  - Mejora la iluminación de la fotografía")
        print("  - Usa un fondo de color diferente al documento")
        print("  - Asegúrate de que los 4 bordes del documento sean visibles")
        if mostrar_pasos:
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        return None

    if mostrar_pasos or guardar_proceso:
        imagen_con_contorno = imagen_procesamiento.copy()
        cv2.drawContours(imagen_con_contorno, [contorno_documento], -1, (0, 255, 0), 2)
        if mostrar_pasos:
            cv2.imshow("3. Contorno del Documento Detectado", imagen_con_contorno)
        if guardar_proceso:
            ruta = os.path.join(carpeta_proceso, "3_contorno_detectado.jpg")
            cv2.imwrite(ruta, imagen_con_contorno)
            print(f"[GUARDADO] {ruta}")

    # 6. Escalar puntos a la imagen original (alta resolución)
    puntos_originales = contorno_documento.reshape(4, 2) * ratio

    # 7. Corrección de perspectiva sobre la imagen original
    documento_enderezado = transformacion_perspectiva(imagen_original, puntos_originales)
    if mostrar_pasos:
        cv2.imshow("4. Documento Enderezado", documento_enderezado)
    if guardar_proceso:
        ruta = os.path.join(carpeta_proceso, "4_documento_enderezado.jpg")
        cv2.imwrite(ruta, documento_enderezado)
        print(f"[GUARDADO] {ruta}")

    # 8. Efecto escáner
    documento_escaneado = aplicar_efecto_escaner(documento_enderezado)
    if mostrar_pasos:
        cv2.imshow("5. Resultado Final - Efecto Escáner", documento_escaneado)
    if guardar_proceso:
        ruta = os.path.join(carpeta_proceso, "5_resultado_final_escaner.jpg")
        cv2.imwrite(ruta, documento_escaneado)
        print(f"[GUARDADO] {ruta}")

    print("\n" + "="*70)
    print("PROCESO COMPLETADO EXITOSAMENTE")
    print("="*70 + "\n")

    if mostrar_pasos:
        print("[INFO] Presiona cualquier tecla para cerrar las ventanas...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    return documento_escaneado


def main():
    """
    Punto de entrada para ejecutar el script desde línea de comandos.
    Uso: python document_scanner.py <ruta_imagen> [nombre_salida]
    """
    if len(sys.argv) < 2:
        print("Uso: python document_scanner.py <ruta_imagen> [nombre_salida]")
        print("\nEjemplo:")
        print("  python document_scanner.py documento.jpg")
        print("  python document_scanner.py documento.jpg mi_documento.jpg")
        sys.exit(1)

    ruta_entrada = sys.argv[1]
    nombre_salida = sys.argv[2] if len(sys.argv) > 2 else "documento_escaneado.jpg"

    carpeta_proceso, carpeta_resultados = crear_carpetas_salida()

    resultado = escanear_documento(ruta_entrada,
                                   mostrar_pasos=True,
                                   guardar_proceso=True,
                                   carpeta_proceso=carpeta_proceso)

    if resultado is not None:
        ruta_salida = os.path.join(carpeta_resultados, nombre_salida)
        cv2.imwrite(ruta_salida, resultado)
        print(f"\n[ÉXITO] Documento escaneado guardado en: {ruta_salida}")
    else:
        print("\n[FALLO] El proceso no se completó correctamente")
        sys.exit(1)


if __name__ == "__main__":
    main()
