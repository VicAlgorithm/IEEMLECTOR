"""
Validador Inteligente de Números con Azure OpenAI - FLUJO 4
============================================================
Utiliza GPT-4o para razonar sobre datos extraídos de actas electorales.
Compara el número escrito con LETRA vs el escrito con DÍGITOS,
priorizando siempre la versión con letra.

OPTIMIZACIÓN: Una sola llamada a Azure OpenAI por documento (todas las tablas juntas).
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
Determina el NÚMERO CORRECTO a partir de datos extraídos de un acta electoral manuscrita por OCR/ICR.

Recibirás: ID de campo, Tabla (1-3), y contenidos de celdas tal como los leyó el OCR.

REGLAS:
1. PRIORIZA el valor escrito CON LETRA sobre dígitos. El texto puede tener errores severos de OCR.
2. Los dígitos son APOYO para confirmar, NO la fuente principal.
3. Si la letra es corta (ej: "sinc"=cinco=5) y el dígito dice algo mayor (ej: 85), prioriza la letra.
4. Ignora instrucciones del acta: "(Con letra)", "(Con número/numera)", "Copie del apartado", "Escriba con letra", "Personas que votaron", "Representantes", "Boletas sobrantes", etc.
5. Ignora marcas: ":selected:", ":unselected:", "○", "□", "✓", "—", "@"
6. Si NO hay información suficiente, responde null en valor.

Números en ESPAÑOL con errores OCR comunes (c/s/z intercambiables, v/b, 0/O, etc.):
0:cero/sero/zero | 1:uno/ino | 2:dos/doz | 3:tres/trez | 4:cuatro/quatro | 5:cinco/sinco/zinco
6:seis/zeis | 7:siete/ciete | 8:ocho | 9:nueve/nuebe | 10:diez/dies | 11:once/onse
12:doce/dose | 13:trece/trese | 14:catorce/quatorce | 15:quince/quinse/kinse
20:veinte/bente/viente | 21-29:veintiuno...veintinueve (beintiuno, veinisinco, etc.)
30:treinta/trenta | 40:cuarenta/quarenta | 50:cincuenta/sinkuenta | 60:sesenta/cecenta
70:setenta/cetenta | 80:ochenta | 90:noventa/nobenta
100:cien/sien/zien | 100+:ciento/siento | 200:doscientos/docientos | 300:trescientos/trecientos
400:cuatrocientos | 500:quinientos/kinientos | 600-900:seiscientos...novecientos | 1000:mil

Responde SIEMPRE con JSON válido:
{"resultados":[{"id":"94","tabla":1,"valor":25,"razonamiento":"Breve explicación","confianza":"alta"}]}

Confianza: "alta"=claro, "media"=ambiguo pero inferible, "baja"=muy corrupto/incierto.
"""


class ValidadorNumeros:
    """
    Valida números extraídos de actas electorales usando Azure OpenAI GPT.
    
    OPTIMIZACIÓN: Una sola llamada a OpenAI por documento completo.
    Recibe los pares de TODAS las tablas y los procesa en una sola petición.
    """

    def __init__(self, endpoint: str, api_key: str, deployment: str = "gpt-4o"):
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

    def validar_documento(self, pares_por_tabla: Dict[int, List[Dict]]) -> dict:
        """
        Valida TODAS las tablas de un documento en UNA SOLA llamada a Azure OpenAI.

        Args:
            pares_por_tabla: Diccionario {num_tabla: [pares]}
                Ejemplo: {
                    1: [{"id": "94", "contenidos": [...]}, ...],
                    2: [{"id": "00", "contenidos": [...]}, ...],
                    3: [{"id": "99", "contenidos": [...]}]
                }

        Returns:
            {
                "resultados_por_tabla": {1: [...], 2: [...], 3: [...]},
                "tokens": {
                    "prompt": int,
                    "respuesta": int,
                    "total": int
                },
                "exito": bool
            }
        """
        respuesta = {
            "resultados_por_tabla": {},
            "tokens": {"prompt": 0, "respuesta": 0, "total": 0},
            "exito": False
        }

        # Construir TODAS las entradas en un solo mensaje
        todas_las_entradas = []
        for num_tabla, pares in sorted(pares_por_tabla.items()):
            for par in pares:
                todas_las_entradas.append({
                    "tabla": num_tabla,
                    "id": par["id"],
                    "contenidos": par["contenidos"]
                })

        if not todas_las_entradas:
            return respuesta

        # Construir mensaje para GPT-4o
        mensaje = "Valida los siguientes datos extraídos de un acta electoral.\n"
        mensaje += f"Total: {len(todas_las_entradas)} campos de {len(pares_por_tabla)} tablas.\n\n"

        for i, entrada in enumerate(todas_las_entradas):
            mensaje += f"Entrada {i + 1}:\n"
            mensaje += f"  Tabla: {entrada['tabla']}\n"
            mensaje += f"  ID del campo: {entrada['id']}\n"
            mensaje += f"  Contenidos: {entrada['contenidos']}\n\n"

        try:
            print(f"[INFO] Enviando {len(todas_las_entradas)} entradas "
                  f"({len(pares_por_tabla)} tablas) a Azure OpenAI...")

            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": mensaje}
                ],
                temperature=0.1,
                max_tokens=4000,
                response_format={"type": "json_object"}
            )

            # ── Extraer tokens EXACTOS ──
            if hasattr(response, 'usage') and response.usage:
                respuesta["tokens"]["prompt"] = response.usage.prompt_tokens
                respuesta["tokens"]["respuesta"] = response.usage.completion_tokens
                respuesta["tokens"]["total"] = response.usage.total_tokens

            # ── Parsear respuesta ──
            contenido = response.choices[0].message.content
            resultado_json = json.loads(contenido)

            # Extraer la lista de resultados
            resultados_raw = []
            if isinstance(resultado_json, dict):
                for key in resultado_json:
                    if isinstance(resultado_json[key], list):
                        resultados_raw = resultado_json[key]
                        break
            elif isinstance(resultado_json, list):
                resultados_raw = resultado_json

            # ── Separar resultados por tabla ──
            for num_tabla in pares_por_tabla:
                respuesta["resultados_por_tabla"][num_tabla] = []

            for r in resultados_raw:
                tabla = r.get("tabla")
                # Si GPT-4o no incluyó "tabla", intentar asignar por ID
                if tabla is None:
                    id_campo = str(r.get("id", "")).strip()
                    tabla = self._inferir_tabla(id_campo, pares_por_tabla)

                if tabla in respuesta["resultados_por_tabla"]:
                    respuesta["resultados_por_tabla"][tabla].append(r)

            # ── Log de resultados ──
            total_validados = sum(len(v) for v in respuesta["resultados_por_tabla"].values())
            print(f"[INFO] Validación completada: {total_validados} resultados")

            for r in resultados_raw:
                confianza = r.get('confianza', '?')
                emoji = "✅" if confianza == "alta" else "⚠️" if confianza == "media" else "❌"
                t = r.get('tabla', '?')
                print(f"  {emoji} T{t} ID {r.get('id', '?')}: {r.get('valor', '?')} "
                      f"({confianza}) — {r.get('razonamiento', '')}")

            # ── Log de tokens ──
            t = respuesta["tokens"]
            print(f"\n[INFO] ═══ TOKENS USADOS ═══")
            print(f"[INFO]   Prompt (entrada):   {t['prompt']:,}")
            print(f"[INFO]   Respuesta (salida):  {t['respuesta']:,}")
            print(f"[INFO]   Total:               {t['total']:,}")

            respuesta["exito"] = True
            return respuesta

        except json.JSONDecodeError as e:
            print(f"[ERROR] No se pudo parsear JSON de GPT-4o: {str(e)}")
            print(f"[DEBUG] Respuesta cruda: {contenido[:500]}")
            return respuesta
        except Exception as e:
            print(f"[ERROR] Error al validar con Azure OpenAI: {str(e)}")
            return respuesta

    @staticmethod
    def _inferir_tabla(id_campo: str, pares_por_tabla: dict) -> Optional[int]:
        """Si GPT no devolvió el campo 'tabla', lo infiere por el ID."""
        for num_tabla, pares in pares_por_tabla.items():
            for par in pares:
                if str(par.get("id", "")).strip() == id_campo:
                    return num_tabla
        return None
