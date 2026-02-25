"""
Funciones de Limpieza de Texto — FLUJO 3
=========================================
Elimina ruido de Azure Document Intelligence
(marcas de selección, instrucciones del acta, etc.)
"""

import re


def limpiar_texto(texto: str) -> str:
    """Limpia el ruido de Azure y símbolos innecesarios (modo estricto)."""
    ruido = [
        ":unselected:", ":selected:", "selected", "unselected",
        "○", "□", "✓", "—",
        "(Con letra)", "(Con número)", "(Con numera)", "@",
        "Personas que votaron", "Representantes", "Total de personas"
    ]

    resultado = texto
    for r in ruido:
        resultado = resultado.replace(r, "")
    resultado = resultado.strip(" .-_,")

    # Filtro de Instrucciones Largas
    texto_lower = resultado.lower()
    if (texto_lower.startswith("copie") or
        texto_lower.startswith("escriba") or
        "del apartado" in texto_lower or
        "de la hoja" in texto_lower or
        len(resultado) > 60):
        return ""

    return resultado


def limpiar_texto_ligero(texto: str) -> str:
    """
    Limpieza ligera que mantiene el texto con letra pero quita ruido de Azure.
    Usada para la extracción cruda (modo validación con IA).
    """
    ruido_azure = [
        ":unselected:", ":selected:",
        "○", "□", "✓", "—", "@"
    ]

    resultado = texto
    for r in ruido_azure:
        resultado = resultado.replace(r, "")

    return resultado.strip()
