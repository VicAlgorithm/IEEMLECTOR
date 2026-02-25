"""
Convertidor de Texto a Números — Algoritmo de Detección Local
==============================================================
Convierte números escritos con palabras en español (0-999) a enteros.

Tres niveles de conversión:
  1. EXACTA:  Normaliza el texto (minúsculas, sin acentos) y busca coincidencias
  2. DIFUSA:  Usa distancia Levenshtein para texto con errores de OCR/ortografía
  3. HUELLA:  Usa longitud + primera letra + última letra como "fingerprint"

Rango soportado: 0 a 999 (números electorales mexicanos)

Reglas de composición en español:
  - Unidades:   cero(0), uno(1), ..., nueve(9)
  - Especiales: diez(10), once(11), ..., quince(15)
  - Dieciséis a diecinueve: palabra única
  - Veinte a veintinueve:   palabra única
  - Treinta a noventa y nueve: "treinta y uno", "cuarenta y dos"
  - Cien (100 solo) / Ciento (100 + algo)
  - Doscientos a novecientos: palabra única para centena
  - Compuestos: centena + (decena/especial) + ("y" +) unidad
    Ejemplo: "cuatrocientos veintiuno" = 400 + 21 = 421
    Ejemplo: "doscientos treinta y seis" = 200 + 36 = 236
"""

import re
import unicodedata
from typing import Optional, Tuple, List, Dict


class ConvertidorTextoNumeros:
    """
    Convierte texto en español (0-999) a enteros.
    Soporta conversión exacta, difusa (OCR corrupto) y por huella digital.
    """

    # ══════════════════════════════════════════════════════════════════════
    # DICCIONARIOS DE REFERENCIA
    # ══════════════════════════════════════════════════════════════════════

    # Todas las palabras numéricas base (sin acentos, minúsculas)
    # Cada entrada: palabra → valor numérico
    PALABRAS = {
        # ── Unidades (0-9) ──
        'cero': 0,        # 4 letras
        'uno': 1,         # 3 letras
        'una': 1,         # 3 letras (femenino)
        'dos': 2,         # 3 letras
        'tres': 3,        # 4 letras
        'cuatro': 4,      # 6 letras
        'cinco': 5,       # 5 letras
        'seis': 6,        # 4 letras
        'siete': 7,       # 5 letras
        'ocho': 8,        # 4 letras
        'nueve': 9,       # 5 letras

        # ── Especiales (10-19) ──
        'diez': 10,            # 4 letras
        'once': 11,            # 4 letras
        'doce': 12,            # 4 letras
        'trece': 13,           # 5 letras
        'catorce': 14,         # 7 letras
        'quince': 15,          # 6 letras
        'dieciseis': 16,       # 9 letras
        'diecisiete': 17,      # 10 letras
        'dieciocho': 18,       # 9 letras
        'diecinueve': 19,      # 10 letras

        # ── Veintena (20-29) ──
        'veinte': 20,          # 6 letras
        'veintiuno': 21,       # 9 letras
        'veintiuna': 21,       # 9 letras (femenino)
        'veintidos': 22,       # 9 letras
        'veintitres': 23,      # 10 letras
        'veinticuatro': 24,    # 12 letras
        'veinticinco': 25,     # 11 letras
        'veintiseis': 26,      # 10 letras
        'veintisiete': 27,     # 11 letras
        'veintiocho': 28,      # 10 letras
        'veintinueve': 29,     # 11 letras

        # ── Decenas (30-90) ──
        'treinta': 30,         # 7 letras
        'cuarenta': 40,        # 8 letras
        'cincuenta': 50,       # 9 letras
        'sesenta': 60,         # 7 letras
        'setenta': 70,         # 7 letras
        'ochenta': 80,         # 7 letras
        'noventa': 90,         # 7 letras

        # ── Centenas (100-900) ──
        'cien': 100,           # 4 letras (solo, sin complemento)
        'ciento': 100,         # 6 letras (con complemento)
        'doscientos': 200,     # 10 letras
        'doscientas': 200,     # 10 letras (femenino)
        'trescientos': 300,    # 11 letras
        'trescientas': 300,    # 11 letras
        'cuatrocientos': 400,  # 13 letras
        'cuatrocientas': 400,  # 13 letras
        'quinientos': 500,     # 10 letras
        'quinientas': 500,     # 10 letras
        'seiscientos': 600,    # 11 letras
        'seiscientas': 600,    # 11 letras
        'setecientos': 700,    # 11 letras
        'setecientas': 700,    # 11 letras
        'ochocientos': 800,    # 11 letras
        'ochocientas': 800,    # 11 letras
        'novecientos': 900,    # 11 letras
        'novecientas': 900,    # 11 letras
    }

    # Palabras que son centenas (para detectar estructura)
    _CENTENAS_SET = {
        'cien', 'ciento', 'doscientos', 'doscientas', 'trescientos',
        'trescientas', 'cuatrocientos', 'cuatrocientas', 'quinientos',
        'quinientas', 'seiscientos', 'seiscientas', 'setecientos',
        'setecientas', 'ochocientos', 'ochocientas', 'novecientos',
        'novecientas'
    }

    # ══════════════════════════════════════════════════════════════════════
    # HUELLAS DIGITALES — Longitud + Primera letra + Última letra
    # ══════════════════════════════════════════════════════════════════════
    # Números con patrones únicos de inicio/fin mencionados por el usuario:
    # 1(uno), 7(siete), 8(ocho), 9(nueve), 10(diez), 11(once), 13(trece),
    # 14(catorce), 15(quince), 18(dieciocho), 30(treinta), 40(cuarenta),
    # 50(cincuenta), 80(ochenta), 90(noventa), 100(cien),
    # 400(cuatrocientos), 500(quinientos), 800(ochocientos), 900(novecientos)

    def __init__(self):
        """Construye las tablas de huellas y referencia inversa."""
        # Huella: (longitud, primera_letra, ultima_letra) → [(palabra, valor)]
        self.huellas: Dict[Tuple[int, str, str], List[Tuple[str, int]]] = {}

        # Construir huellas para todas las palabras
        for palabra, valor in self.PALABRAS.items():
            huella = (len(palabra), palabra[0], palabra[-1])
            if huella not in self.huellas:
                self.huellas[huella] = []
            self.huellas[huella].append((palabra, valor))

        # Contar huellas únicas (para diagnóstico)
        self._huellas_unicas = sum(
            1 for v in self.huellas.values() if len(v) == 1
        )

    # ══════════════════════════════════════════════════════════════════════
    # UTILIDADES
    # ══════════════════════════════════════════════════════════════════════

    @staticmethod
    def normalizar(texto: str) -> str:
        """
        Normaliza texto: minúsculas, quita acentos, solo letras y espacios.
        'Veintitrés' → 'veintitres'
        'Seiscientos  treinta' → 'seiscientos treinta'
        """
        texto = texto.lower().strip()
        # Quitar acentos (NFD decompose + filtrar marcas diacríticas)
        texto = unicodedata.normalize('NFD', texto)
        texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
        # Solo letras y espacios
        texto = re.sub(r'[^a-z\s]', '', texto)
        # Normalizar espacios múltiples
        texto = re.sub(r'\s+', ' ', texto).strip()
        return texto

    @staticmethod
    def levenshtein(s1: str, s2: str) -> int:
        """
        Calcula la distancia Levenshtein entre dos strings.
        Implementación sin dependencias externas.
        """
        if len(s1) < len(s2):
            return ConvertidorTextoNumeros.levenshtein(s2, s1)
        if len(s2) == 0:
            return len(s1)

        prev_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            curr_row = [i + 1]
            for j, c2 in enumerate(s2):
                insercion = prev_row[j + 1] + 1
                eliminacion = curr_row[j] + 1
                sustitucion = prev_row[j] + (c1 != c2)
                curr_row.append(min(insercion, eliminacion, sustitucion))
            prev_row = curr_row
        return prev_row[-1]

    # ══════════════════════════════════════════════════════════════════════
    # NIVEL 1: CONVERSIÓN EXACTA (normalizada)
    # ══════════════════════════════════════════════════════════════════════

    def convertir(self, texto: str) -> Optional[int]:
        """
        Intenta convertir texto en español a entero (conversión exacta).
        Normaliza acentos, mayúsculas, etc. pero no tolera errores de ortografía.

        Ejemplos:
            'Quinientos cuarenta y cinco' → 545
            'veintitrés' → 23
            'cien' → 100
            'Ochocientos' → 800

        Returns:
            int si la conversión fue exitosa, None si no pudo convertir.
        """
        normalizado = self.normalizar(texto)
        if not normalizado:
            return None

        # Caso 1: una sola palabra
        if normalizado in self.PALABRAS:
            return self.PALABRAS[normalizado]

        # Caso 2: número compuesto (varias palabras)
        return self._parsear_compuesto(normalizado)

    def _parsear_compuesto(self, texto_normalizado: str) -> Optional[int]:
        """
        Parsea números compuestos como:
          'cuatrocientos veintiuno' → 421
          'doscientos treinta y seis' → 236
          'ciento diez' → 110
          'novecientos noventa y nueve' → 999

        Regla: centena + (decena/especial) + unidad (sumados)
        """
        # Quitar la "y" que conecta decenas con unidades
        palabras = texto_normalizado.replace(' y ', ' ').split()

        if not palabras:
            return None

        total = 0
        encontro_algo = False

        for palabra in palabras:
            if not palabra:
                continue

            if palabra in self.PALABRAS:
                total += self.PALABRAS[palabra]
                encontro_algo = True
            else:
                # Palabra no reconocida → fallo en conversión exacta
                return None

        return total if encontro_algo else None

    # ══════════════════════════════════════════════════════════════════════
    # NIVEL 2: CONVERSIÓN DIFUSA (Levenshtein)
    # ══════════════════════════════════════════════════════════════════════

    def convertir_fuzzy(self, texto: str) -> Tuple[Optional[int], float]:
        """
        Conversión difusa: tolera errores de OCR y ortografía.
        Usa distancia Levenshtein y huellas digitales.

        Ejemplos:
            'Calorce'         → (14, 0.85)  — similar a 'catorce'
            'Quinits'         → (500, 0.60) — detecta por huella
            'treivila y cuatro' → intenta cada palabra por separado

        Returns:
            Tupla (valor, confianza) donde confianza es 0.0 a 1.0
            (None, 0.0) si no puede resolver nada.
        """
        normalizado = self.normalizar(texto)
        if not normalizado:
            return None, 0.0

        # Primero intentar conversión exacta
        resultado_exacto = self.convertir(texto)
        if resultado_exacto is not None:
            return resultado_exacto, 1.0

        # Limpiar "y" de conexión
        palabras = normalizado.replace(' y ', ' ').split()
        palabras = [p for p in palabras if p]

        if not palabras:
            return None, 0.0

        # Caso: una sola palabra
        if len(palabras) == 1:
            return self._fuzzy_palabra(palabras[0])

        # Caso: múltiples palabras → fuzzy cada una y sumar
        total = 0
        confianza_min = 1.0
        encontro_algo = False

        for palabra in palabras:
            # Primero intentar exacto
            if palabra in self.PALABRAS:
                total += self.PALABRAS[palabra]
                encontro_algo = True
                continue

            # Si no, intentar fuzzy
            valor, conf = self._fuzzy_palabra(palabra)
            if valor is not None:
                total += valor
                confianza_min = min(confianza_min, conf)
                encontro_algo = True
            else:
                # No pudo resolver esta palabra → fallo
                return None, 0.0

        if encontro_algo:
            return total, confianza_min
        return None, 0.0

    def _fuzzy_palabra(self, palabra: str) -> Tuple[Optional[int], float]:
        """
        Intenta resolver una sola palabra corrupta.

        Estrategia:
        1. Levenshtein contra TODO el diccionario (mejor match global)
        2. Si empata, usar huella digital para desempatar
        3. Requiere longitud similar (±30%) para evitar falsos positivos
        """
        if not palabra:
            return None, 0.0

        # ── Estrategia principal: Levenshtein contra todo el diccionario ──
        # Filtra candidatos por longitud similar (±30%)
        candidatos = []
        for ref_palabra, ref_valor in self.PALABRAS.items():
            # Filtro de longitud: no comparar palabras con tamaños muy diferentes
            ratio_len = len(palabra) / max(len(ref_palabra), 1)
            if ratio_len < 0.65 or ratio_len > 1.50:
                continue

            dist = self.levenshtein(palabra, ref_palabra)
            candidatos.append((ref_palabra, ref_valor, dist))

        if not candidatos:
            return None, 0.0

        # Ordenar por distancia (menor = mejor)
        candidatos.sort(key=lambda x: x[2])
        mejor = candidatos[0]
        ref_palabra, ref_valor, mejor_dist = mejor

        # Umbral: permitir hasta 35% de diferencia
        umbral = max(2, int(len(ref_palabra) * 0.35))
        if mejor_dist > umbral:
            # ── Fallback: huella digital ──
            if len(palabra) >= 2:
                huella = (len(palabra), palabra[0], palabra[-1])
                if huella in self.huellas:
                    h_candidatos = self.huellas[huella]
                    if len(h_candidatos) == 1:
                        return h_candidatos[0][1], 0.65
            return None, 0.0

        # Calcular confianza basada en proporción de caracteres correctos
        conf = max(0.50, 1.0 - (mejor_dist / max(len(ref_palabra), 1)))

        # Bonus si la huella coincide (misma longitud + primera/última letra)
        if (len(palabra) == len(ref_palabra) and
            palabra[0] == ref_palabra[0] and
            palabra[-1] == ref_palabra[-1]):
            conf = min(1.0, conf + 0.10)

        return ref_valor, conf

    # ══════════════════════════════════════════════════════════════════════
    # NIVEL 3: DETECCIÓN POR HUELLA (solo longitud + primera/última)
    # ══════════════════════════════════════════════════════════════════════

    def detectar_por_huella(self, texto: str) -> List[Tuple[int, float]]:
        """
        Detecta posibles valores usando SOLO la huella digital.
        Útil cuando el texto está muy corrupto pero se conserva
        la longitud y las letras de inicio/fin.

        Returns:
            Lista de (valor, confianza) ordenada de mayor a menor confianza.
        """
        normalizado = self.normalizar(texto)
        if not normalizado or len(normalizado) < 2:
            return []

        # Para texto de una sola palabra
        palabras = normalizado.replace(' y ', ' ').split()
        palabras = [p for p in palabras if p and len(p) >= 2]

        if len(palabras) == 1:
            palabra = palabras[0]
            huella = (len(palabra), palabra[0], palabra[-1])

            if huella in self.huellas:
                return [
                    (valor, 0.65) for _, valor in self.huellas[huella]
                ]

            # Buscar huellas cercanas (±1 longitud, misma primera/última)
            resultados = []
            for delta in [-1, 1]:
                huella_cercana = (len(palabra) + delta, palabra[0], palabra[-1])
                if huella_cercana in self.huellas:
                    for _, valor in self.huellas[huella_cercana]:
                        resultados.append((valor, 0.50))
            return resultados

        return []

    # ══════════════════════════════════════════════════════════════════════
    # MÉTODO PRINCIPAL: VALIDAR CAMPO COMPLETO
    # ══════════════════════════════════════════════════════════════════════

    def validar_campo(self, texto_letra: str, texto_digito: str) -> dict:
        """
        Valida un campo electoral completo usando el sistema de prioridades:

        Prioridad 1: Conversión exacta del texto → comparar con dígito
        Prioridad 2: Conversión difusa del texto → comparar con dígito
        Prioridad 3: Retorna lo que pudo con nivel de confianza

        NOTA: Las prioridades que requieren Azure OpenAI se manejan en el
        orquestador (validador_numeros.py), no aquí.

        Args:
            texto_letra:  Lo que Azure leyó como texto ("Quinientos cuarenta y cinco")
            texto_digito: Lo que Azure leyó como dígito ("545")

        Returns:
            {
                'valor': int or None,
                'confianza': float (0.0-1.0),
                'metodo': str,
                'detalle': str
            }
        """
        resultado = {
            'valor': None,
            'confianza': 0.0,
            'metodo': 'sin_resultado',
            'detalle': ''
        }

        # Extraer el dígito como entero
        digito_int = self._extraer_digito(texto_digito)

        # ── PRIORIDAD 1: Conversión exacta del texto ──
        texto_int = self.convertir(texto_letra)

        if texto_int is not None:
            if digito_int is not None and texto_int == digito_int:
                resultado['valor'] = texto_int
                resultado['confianza'] = 1.0
                resultado['metodo'] = 'texto_exacto_coincide'
                resultado['detalle'] = (
                    f"Texto '{texto_letra}' = {texto_int}, "
                    f"dígito '{texto_digito}' = {digito_int}. Coinciden."
                )
            else:
                # Texto se convirtió pero no coincide con dígito → texto tiene prioridad
                resultado['valor'] = texto_int
                resultado['confianza'] = 1.0
                resultado['metodo'] = 'texto_exacto_prioridad'
                detalle = f"Texto '{texto_letra}' = {texto_int}."
                if digito_int is not None:
                    detalle += f" Dígito dice {digito_int}, pero texto tiene prioridad."
                resultado['detalle'] = detalle
            return resultado

        # ── PRIORIDAD 2: Conversión difusa del texto ──
        fuzzy_int, fuzzy_conf = self.convertir_fuzzy(texto_letra)

        if fuzzy_int is not None and fuzzy_conf >= 0.60:
            if digito_int is not None and fuzzy_int == digito_int:
                resultado['valor'] = fuzzy_int
                resultado['confianza'] = min(fuzzy_conf, 0.95)
                resultado['metodo'] = 'fuzzy_coincide'
                resultado['detalle'] = (
                    f"Texto corrupto '{texto_letra}' ≈ {fuzzy_int} "
                    f"(confianza {fuzzy_conf:.0%}), dígito confirma."
                )
            else:
                resultado['valor'] = fuzzy_int
                resultado['confianza'] = min(fuzzy_conf, 0.85)
                resultado['metodo'] = 'fuzzy_prioridad'
                detalle = (
                    f"Texto corrupto '{texto_letra}' ≈ {fuzzy_int} "
                    f"(confianza {fuzzy_conf:.0%})."
                )
                if digito_int is not None:
                    detalle += f" Dígito dice {digito_int}."
                resultado['detalle'] = detalle
            return resultado

        # ── PRIORIDAD 3: No se pudo convertir el texto ──
        # Retornar lo que tenemos para que el orquestador use OpenAI o dígito
        resultado['metodo'] = 'necesita_ia'
        resultado['detalle'] = (
            f"No se pudo convertir '{texto_letra}'. "
            f"Dígito disponible: '{texto_digito}'"
        )
        if digito_int is not None:
            resultado['valor'] = digito_int
            resultado['confianza'] = 0.0  # Será actualizada por el orquestador

        return resultado

    @staticmethod
    def _extraer_digito(texto_digito: str) -> Optional[int]:
        """Extrae un entero del texto de dígito, limpiando caracteres extra."""
        if not texto_digito:
            return None
        # Limpiar: quitar todo excepto dígitos
        solo_nums = re.sub(r'[^0-9]', '', str(texto_digito))
        if solo_nums:
            return int(solo_nums)
        return None

    # ══════════════════════════════════════════════════════════════════════
    # DIAGNÓSTICO
    # ══════════════════════════════════════════════════════════════════════

    def info(self) -> str:
        """Retorna información del convertidor para diagnóstico."""
        total_palabras = len(self.PALABRAS)
        total_huellas = len(self.huellas)
        return (
            f"ConvertidorTextoNumeros: {total_palabras} palabras, "
            f"{total_huellas} huellas ({self._huellas_unicas} únicas)"
        )


# ══════════════════════════════════════════════════════════════════════════
# PRUEBAS DE VERIFICACIÓN
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    conv = ConvertidorTextoNumeros()
    print(conv.info())
    print("Ejecuta 'python test_convertidor.py' para las pruebas completas.")

