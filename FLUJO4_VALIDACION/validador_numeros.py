"""
Validador Inteligente de Números con Azure OpenAI - FLUJO 4
============================================================
Utiliza GPT-4o para razonar sobre datos extraídos de actas electorales.
Compara el número escrito con LETRA vs el escrito con DÍGITOS,
priorizando siempre la versión con letra.

Autor: Sistema de Procesamiento de Documentos
Librería: openai (Azure OpenAI Service)
"""

import json
from typing import List, Dict, Optional

# Manejo seguro de importaciones
OPENAI_AVAILABLE = False
try:
    from openai import AzureOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    print("[ADVERTENCIA] Librería 'openai' no encontrada. FLUJO 4 no estará disponible.")
    print("  Instala con: pip install openai")


# ============================================================================
# PROMPT DEL SISTEMA - Reglas de Razonamiento para GPT-4o
# ============================================================================
SYSTEM_PROMPT = """Eres un validador experto de datos electorales mexicanos.
Tu tarea es determinar el NÚMERO CORRECTO a partir de datos extraídos de un acta electoral manuscrita.

Para cada entrada recibirás:
- Un ID de campo (ej: "94", "00", "99")
- Los contenidos de TODAS las celdas de esa fila/sección, tal como fueron leídos por OCR/ICR

REGLAS ESTRICTAS:

1. SIEMPRE prioriza el valor escrito CON LETRA (palabras) sobre el escrito con dígitos.

2. El texto con letra puede tener FALTAS DE ORTOGRAFÍA severas (es manuscrito y el OCR puede fallar).
   Ejemplos: "veinisinco" = "veinticinco" = 25, "sinc" = "cinco" = 5

3. El número en dígitos sirve como APOYO para confirmar, pero NO es la fuente principal.

4. Si la letra dice algo como "sinc" y el dígito dice "85":
   - "sinc" tiene pocas letras, parece "cinco" = 5
   - "85" contiene un 5, pero "ochenta y cinco" tendría muchas más letras escritas
   - Resultado: 5

5. Si la letra dice "Cien" y el dígito "100", ambos coinciden → Resultado: 100

6. Ignora textos que sean instrucciones del acta como "(Con letra)", "(Con número)",
   "Copie del apartado", "Escriba con letra", "Personas que votaron", "Representantes",
   "Boletas sobrantes", "Total de personas", etc.

7. Ignora marcas de selección: ":selected:", ":unselected:", "○", "□", "✓", "—", "@"

8. Si NO hay suficiente información para determinar el número, responde con null en el valor.

9. La letra "(Con numera)" es un error de OCR de "(Con número)".

10. A veces el texto viene mezclado con basura del OCR. Extrae solo lo relevante.

IMPORTANTE: Los números escritos con letra están en ESPAÑOL MEXICANO.
Ejemplos de equivalencias con posibles errores de escritura/OCR:
- "sero", "cero", "zero", "0ero" → 0
- "uno", "ino", "unp" → 1
- "dos", "doz", "d0s" → 2
- "tres", "trez", "tr3s" → 3
- "cuatro", "quatro", "cuatr0" → 4
- "sinco", "cinco", "zinco", "cinc0" → 5
- "seis", "zeis" → 6
- "siete", "ciete" → 7
- "ocho", "och0" → 8
- "nueve", "nuebe", "nuev3" → 9
- "dies", "diez", "d1ez" → 10
- "once", "onse", "0nce" → 11
- "doce", "dose", "d0ce" → 12
- "trece", "trese" → 13
- "catorce", "quatorce" → 14
- "quince", "quinse", "kinse" → 15
- "veinte", "bente", "beinte", "viente" → 20
- "veintiuno", "beintiuno" → 21
- "veinticinco", "veinisinco", "beinticinco" → 25
- "treinta", "trenta", "trienta" → 30
- "cuarenta", "quarenta" → 40
- "cincuenta", "sinkuenta" → 50
- "sesenta", "cecenta" → 60
- "setenta", "cetenta" → 70
- "ochenta", "ochenta" → 80
- "noventa", "nobenta" → 90
- "sien", "cien", "zien" → 100
- "ciento", "siento" → 100+
- "docientos", "doscientos", "dosientos" → 200
- "trecientos", "trescientos" → 300
- "cuatrocientos", "quatrocientos" → 400
- "quinientos", "kinientos" → 500
- "mil", "mill" → 1000

Responde SIEMPRE con un JSON válido con esta estructura EXACTA:
{
  "resultados": [
    {
      "id": "94",
      "valor": 25,
      "razonamiento": "Leí 'veinisinco' que se parece a 'veinticinco' = 25. El dígito dice 25, coincide.",
      "confianza": "alta"
    }
  ]
}

Los niveles de confianza son: "alta", "media", "baja"
- alta: letra y dígito coinciden claramente, o la letra es clara aunque el dígito difiera
- media: letra es ambigua pero se puede inferir con el dígito como apoyo
- baja: gran discrepancia o texto muy corrupto, la decisión es incierta
"""


class ValidadorNumeros:
    """
    Valida números extraídos de actas electorales usando Azure OpenAI (GPT-4o).
    Compara el texto escrito con letra vs dígitos y razona cuál es correcto.
    
    Uso básico:
        validador = ValidadorNumeros(endpoint, api_key, deployment)
        resultado = validador.validar_pares([
            {"id": "94", "contenidos": ["veinisinco", "25"]},
            {"id": "96", "contenidos": ["noventa", "90"]}
        ])
    """

    def __init__(self, endpoint: str, api_key: str, deployment: str = "gpt-4o"):
        """
        Inicializa el validador con Azure OpenAI.

        Args:
            endpoint:   URL del endpoint de Azure OpenAI (ej: https://tu-recurso.openai.azure.com/)
            api_key:    Clave de API de Azure OpenAI
            deployment: Nombre del deployment del modelo (ej: "gpt-4o", "gpt-4o-mini")
        """
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "La librería 'openai' no está instalada. "
                "Ejecuta: pip install openai"
            )

        self.client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version="2024-10-21"
        )
        self.deployment = deployment
        print(f"[INFO] Validador Azure OpenAI inicializado")
        print(f"[INFO] Endpoint: {endpoint}")
        print(f"[INFO] Deployment: {deployment}")

    def validar_pares(self, pares: List[Dict]) -> List[Dict]:
        """
        Valida una lista de pares extraídos de una tabla.

        Envía todos los pares en UNA SOLA llamada a GPT-4o para eficiencia.

        Args:
            pares: Lista de diccionarios con formato:
                [
                    {"id": "94", "contenidos": ["veinisinco", "25", ...]},
                    {"id": "96", "contenidos": ["noventa", "90", ...]},
                    ...
                ]

        Returns:
            Lista de diccionarios validados:
                [
                    {"id": "94", "valor": 25, "razonamiento": "...", "confianza": "alta"},
                    ...
                ]
        """
        if not pares:
            return []

        # Construir mensaje para GPT-4o
        mensaje_usuario = "Valida los siguientes datos extraídos de un acta electoral:\n\n"

        for i, par in enumerate(pares):
            mensaje_usuario += f"Entrada {i + 1}:\n"
            mensaje_usuario += f"  ID del campo: {par['id']}\n"
            mensaje_usuario += f"  Contenidos leídos de las celdas: {par['contenidos']}\n\n"

        try:
            print(f"[INFO] Enviando {len(pares)} entradas a Azure OpenAI para validación...")

            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": mensaje_usuario}
                ],
                temperature=0.1,  # Baja temperatura para respuestas consistentes
                max_tokens=2000,
                response_format={"type": "json_object"}
            )

            contenido = response.choices[0].message.content
            resultado_json = json.loads(contenido)

            # Extraer la lista de resultados
            resultados = []
            if isinstance(resultado_json, dict):
                # Buscar la lista en cualquier clave (normalmente "resultados")
                for key in resultado_json:
                    if isinstance(resultado_json[key], list):
                        resultados = resultado_json[key]
                        break
            elif isinstance(resultado_json, list):
                resultados = resultado_json

            # Mostrar resultados en consola
            print(f"[INFO] Validación completada: {len(resultados)} resultados")
            for r in resultados:
                confianza = r.get('confianza', '?')
                emoji = "✅" if confianza == "alta" else "⚠️" if confianza == "media" else "❌"
                print(f"  {emoji} ID {r.get('id', '?')}: {r.get('valor', '?')} "
                      f"({confianza}) — {r.get('razonamiento', '')}")

            # Info de tokens usados
            if hasattr(response, 'usage') and response.usage:
                print(f"[INFO] Tokens usados: {response.usage.total_tokens} "
                      f"(prompt: {response.usage.prompt_tokens}, "
                      f"respuesta: {response.usage.completion_tokens})")

            return resultados

        except json.JSONDecodeError as e:
            print(f"[ERROR] No se pudo parsear la respuesta JSON de GPT-4o: {str(e)}")
            print(f"[DEBUG] Respuesta cruda: {contenido[:500]}")
            return []
        except Exception as e:
            print(f"[ERROR] Error al validar con Azure OpenAI: {str(e)}")
            return []

    def validar_tabla(self, nombre_tabla: str, pares: List[Dict]) -> str:
        """
        Valida una tabla completa y retorna el resultado formateado como TOON.

        Args:
            nombre_tabla: Nombre identificador de la tabla (para logs)
            pares:        Lista de pares crudos a validar

        Returns:
            String formateado en TOON: "ID : VALOR\\nID : VALOR\\n..."
        """
        print(f"\n[INFO] --- Validando {nombre_tabla} con Azure OpenAI ---")

        resultados = self.validar_pares(pares)

        lineas = []
        for r in resultados:
            id_campo = str(r.get("id", "")).strip()
            valor = r.get("valor")

            if id_campo and valor is not None:
                lineas.append(f"{id_campo} : {valor}")

        if lineas:
            print(f"[INFO] {nombre_tabla}: {len(lineas)} valores validados")
        else:
            print(f"[ADVERTENCIA] {nombre_tabla}: No se obtuvieron valores validados")

        return "\n".join(lineas)
