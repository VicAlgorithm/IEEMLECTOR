"""
Análisis de documentos con Azure AI para FLUJO 2 - Extracción de tablas.
Contiene las funciones de análisis y extracción de datos de tablas.
"""

from typing import Optional, List

try:
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.ai.documentintelligence.models import AnalyzeResult
except ImportError:
    # Definir tipos dummy para evitar errores de referencia si no existe la librería
    DocumentIntelligenceClient = object 
    AnalyzeResult = object


def analizar_documento(client: DocumentIntelligenceClient, ruta_imagen: str) -> Optional[AnalyzeResult]:
    """
    Envía la imagen a Azure AI Document Intelligence para análisis.

    Args:
        client: Cliente inicializado de Azure AI
        ruta_imagen: Ruta al archivo de imagen

    Returns:
        Resultado del análisis o None si falla
    """
    print("\n" + "="*70)
    print("INICIANDO ANÁLISIS CON AZURE AI DOCUMENT INTELLIGENCE")
    print("="*70 + "\n")

    try:
        with open(ruta_imagen, "rb") as f:
            imagen_bytes = f.read()

        print(f"[INFO] Imagen cargada: {ruta_imagen}")
        print(f"[INFO] Tamaño del archivo: {len(imagen_bytes)} bytes")
        print("[INFO] Enviando imagen a Azure AI...")
        print("[INFO] Modelo: prebuilt-layout")

        poller = client.begin_analyze_document(
            model_id="prebuilt-layout",
            body=imagen_bytes,
            content_type="application/octet-stream"
        )

        print("[INFO] Esperando respuesta de Azure AI...")
        resultado = poller.result()

        print("[INFO] Análisis completado exitosamente")

        if hasattr(resultado, 'tables') and resultado.tables:
            print(f"[INFO] Tablas detectadas: {len(resultado.tables)}")
        else:
            print("[ADVERTENCIA] No se detectaron tablas en el documento")

        return resultado

    except Exception as e:
        print(f"[ERROR] Error al analizar documento con Azure AI: {str(e)}")
        return None


def extraer_tablas_interes(resultado: AnalyzeResult, texto_encabezado: Optional[list[str]] = None) -> List[List[float]]:
    """
    Extrae las tablas de interés:
    1. La tabla que coincide con el encabezado (expandida).
    2. La segunda tabla detectada en el documento (si existe).

    Args:
        resultado: Resultado del análisis de Azure AI
        texto_encabezado: Lista de frases a buscar para la primera tabla (ej: ["BOLETAS SOBRANTES"])

    Returns:
        Lista de listas de coordenadas de polígonos [[x1, y1...], [x1, y1...]]
    """
    poligonos_retorno = []

    if not hasattr(resultado, 'tables') or not resultado.tables:
        print("[ERROR] No se encontraron tablas en el resultado")
        return []

    # 1. Agregar las dos primeras tablas tal cual (sin modificación)
    print(f"\n[INFO] --- Recuperando Tablas 1 y 2 (Estándar) ---")
    
    if len(resultado.tables) >= 1:
        if resultado.tables[0].bounding_regions:
            # Obtener polígono original
            poly_t1 = list(resultado.tables[0].bounding_regions[0].polygon)
            
            # EXPANSIÓN MANUAL HACIA LA IZQUIERDA (Solicitud Usuario)
            # Para incluir los números de renglón (94, 96...) que Azure deja fuera.
            # Restamos X píxeles a las coordenadas X (índices 0, 2, 4, 6).
            margen_izq = 70 # Píxeles aprox para capturar los números
            
            # Orden del polígono: [x1, y1, x2, y2, x3, y3, x4, y4]
            # Usualmente: Top-Left, Top-Right, Bottom-Right, Bottom-Left
            # Queremos mover a la izquierda los puntos que tengan la X menor (Top-Left y Bottom-Left).
            
            x_coords = [poly_t1[i] for i in range(0, len(poly_t1), 2)]
            x_min_actual = min(x_coords)
            
            for k in range(0, len(poly_t1), 2):
                if poly_t1[k] <= x_min_actual + 10: # Margen de tolerancia
                    poly_t1[k] = max(0, poly_t1[k] - margen_izq)
            
            poligonos_retorno.append(poly_t1)
            print(f"[INFO] Tabla 1 agregada y expandida {margen_izq}px a la izquierda.")
            
    if len(resultado.tables) >= 2:
        if resultado.tables[1].bounding_regions:
            poligonos_retorno.append(list(resultado.tables[1].bounding_regions[0].polygon))
            print("[INFO] Tabla 2 agregada (índice 1).")

    # 2. Buscar TERCERA tabla basada en encabezado (Sección Verde / Apartado 7)
    print(f"\n[INFO] --- Buscando TABLA 3 (Sección: {texto_encabezado}) ---")
    
    tabla3_polygon = None
    encabezado_region = None
    texto_encontrado = ""
    
    if texto_encabezado and hasattr(resultado, 'paragraphs'):
        # Buscar frases en orden de prioridad (la primera de la lista es la más importante)
        for frase_objetivo in texto_encabezado:
            for paragraph in resultado.paragraphs:
                content = paragraph.content
                if frase_objetivo.lower() in content.lower():
                    if not paragraph.bounding_regions: continue
                    encabezado_region = paragraph.bounding_regions[0].polygon
                    texto_encontrado = content.strip()
                    print(f"[INFO] Encabezado encontrado (Prioridad '{frase_objetivo}'): '{texto_encontrado}'")
                    break
            
            # Si encontramos la frase de mayor prioridad, dejamos de buscar
            if encabezado_region:
                break
    
    major_candidato_tabla = None
    
    if encabezado_region:
        y_min_encabezado = min(encabezado_region[1], encabezado_region[3], encabezado_region[5], encabezado_region[7])
        y_max_encabezado = max(encabezado_region[1], encabezado_region[3], encabezado_region[5], encabezado_region[7])
        x_min_encabezado = min(encabezado_region[0], encabezado_region[2], encabezado_region[4], encabezado_region[6])

        distancia_minima = float('inf')

        for i, tabla in enumerate(resultado.tables):
            if not tabla.bounding_regions: continue
            region_tabla = tabla.bounding_regions[0].polygon
            y_min_tabla = min(region_tabla[1], region_tabla[3], region_tabla[5], region_tabla[7])
            x_min_tabla = min(region_tabla[0], region_tabla[2], region_tabla[4], region_tabla[6])

            # Debe estar debajo del encabezado
            if y_min_tabla >= y_min_encabezado:
                distancia = y_min_tabla - y_max_encabezado
                alineado = abs(x_min_tabla - x_min_encabezado) < 500
                
                if alineado and distancia < distancia_minima:
                    distancia_minima = distancia
                    major_candidato_tabla = region_tabla

    if major_candidato_tabla:
        # Expandir hacia encabezado
        tabla3_polygon = list(major_candidato_tabla)
        y_min_enc = min(encabezado_region[1], encabezado_region[3], encabezado_region[5], encabezado_region[7])
        y_min_actual = min(tabla3_polygon[1], tabla3_polygon[3], tabla3_polygon[5], tabla3_polygon[7])
        
        for k in range(1, len(tabla3_polygon), 2):
            if abs(tabla3_polygon[k] - y_min_actual) < 20:
                tabla3_polygon[k] = y_min_enc
                
        print(f"[INFO] Tabla 3 seleccionada y expandida hasta el encabezado.")
        
        # LÓGICA DE RECORTADO DINÁMICO (Solicitud Usuario)
        # Buscar el texto de corte: "TOTAL DE PERSONAS QUE VOTARON Y EL TOTAL DE VOTOS DE DIPUTACIONES LOCALES SACADOS DE LAS URNAS"
        texto_limite_inferior = [
            "TOTAL DE PERSONAS QUE VOTARON Y EL TOTAL DE VOTOS", 
            "TOTAL DE PERSONAS QUE VOTARON",
            "TOTAL DE VOTOS DE DIPUTACIONES LOCALES"
        ]
        
        y_corte_inferior = None
        
        print(f"[INFO] Buscando límite inferior para Tabla 3: {texto_limite_inferior[0]}...")
        
        if hasattr(resultado, 'paragraphs'):
            for frase_corte in texto_limite_inferior:
                for paragraph in resultado.paragraphs:
                    if frase_corte.lower() in paragraph.content.lower():
                        if paragraph.bounding_regions:
                            region_corte = paragraph.bounding_regions[0].polygon
                            # Tomar el borde SUPERIOR de este texto como el límite INFERIOR de la tabla
                            # polygon = [x1, y1, x2, y2, x3, y3, x4, y4] -> y1, y2 son tops (aprox)
                            y_corte_inferior = min(region_corte[1], region_corte[3], region_corte[5], region_corte[7])
                            print(f"[INFO] Límite inferior encontrado ('{frase_corte}'): Y={y_corte_inferior}")
                            break
                if y_corte_inferior:
                    break
        
        # Calcular límites actuales de la tabla (ya expandida arriba)
        y_coords = [tabla3_polygon[i] for i in range(1, len(tabla3_polygon), 2)]
        y_min_t3 = min(y_coords) # Arriba (encabezado)
        y_max_t3 = max(y_coords) # Abajo (originalmente toda la tabla o sección)
        
        nuevo_y_max = y_max_t3 # Por defecto, sin corte
        
        if y_corte_inferior:
            # Si encontramos el texto, recortamos HASTA ese texto (con un pequeño margen de respiro, ej. -10px)
            nuevo_y_max = y_corte_inferior - 10
            
            # Verificar que el corte tenga sentido (que no esté POR ENCIMA del encabezado)
            if nuevo_y_max <= y_min_t3:
                print("[ADVERTENCIA] El límite inferior encontrado está por encima del encabezado. Ignorando.")
                nuevo_y_max = None
            else:
                print(f"[INFO] Aplicando recorte dinámico a Y={nuevo_y_max:.2f}")

        # Si NO encontramos el texto o el corte fue inválido, usar FALLBACK de 1/3
        if nuevo_y_max is None or nuevo_y_max == y_max_t3:
            print("[INFO] No se encontró límite por texto. Usando estrategia FALLBACK (1/3 superior).")
            alto_total = y_max_t3 - y_min_t3
            nuevo_alto = alto_total / 3
            nuevo_y_max = y_min_t3 + nuevo_alto
            print(f"[INFO] Recorte fallback: Altura {alto_total:.0f} -> {nuevo_alto:.0f}")

        # Aplicar el recorte al polígono
        y_center = (y_min_t3 + y_max_t3) / 2 # Centro original aproximado para distinguir puntos de abajo
        
        # Ajustamos los puntos que estén "abajo" en el polígono original
        # O mejor aún, simplemente forzamos los puntos inferiores a ser nuevo_y_max
        # Asumiendo rectángulo o casi rectángulo:
        # Puntos con Y > y_min_t3 + algo pequeño son los de abajo.
        
        umbral_y = y_min_t3 + (y_max_t3 - y_min_t3) * 0.1 # 10% de altura para distinguir arriba/abajo
        
        puntos_modificados = 0
        for k in range(1, len(tabla3_polygon), 2):
            if tabla3_polygon[k] > umbral_y:
                 # Si este punto Y está significativamente abajo del top, lo movemos al nuevo fondo
                 # Pero SOLO si el nuevo fondo es MENOR (más arriba) que el punto actual
                 # (Para recortar, nunca para expandir hacia abajo mas alla del original, aunque aqui expandimos logica)
                 tabla3_polygon[k] = nuevo_y_max
                 puntos_modificados += 1
                 
        print(f"[INFO] Tabla 3 recortada. Límite Y inferior establecido en: {nuevo_y_max:.2f}")
        poligonos_retorno.append(tabla3_polygon)
        
    elif encabezado_region:
        # ESTRATEGIA FALLBACK: Crear tabla sintética basada en el encabezado
        print("[ADVERTENCIA] No se encontró una tabla Azure alineada al encabezado.")
        print("[INFO] Generando TABLA SINTÉTICA (Recorte Manual) a partir del encabezado...")
        
        # Obtener coordenadas del encabezado
        y_min_enc = min(encabezado_region[1], encabezado_region[3], encabezado_region[5], encabezado_region[7])
        x_min_enc = min(encabezado_region[0], encabezado_region[2], encabezado_region[4], encabezado_region[6])
        x_max_enc = max(encabezado_region[0], encabezado_region[2], encabezado_region[4], encabezado_region[6])
        
        # Determinar ancho del recorte:
        # Intentar usar el ancho de la Tabla 1 (índice 0) si está disponible y es razonable,
        # ya que la Sección 7 suele estar en la misma columna que la Tabla 1.
        x_min_final = x_min_enc - 10 # Margen por defecto
        x_max_final = x_max_enc + 10
        
        if len(poligonos_retorno) > 0:
            # Usar coordenadas de la primera tabla como referencia de columna
            poly_t1 = poligonos_retorno[0]
            x_values_t1 = [poly_t1[i] for i in range(0, len(poly_t1), 2)]
            x_min_t1 = min(x_values_t1)
            x_max_t1 = max(x_values_t1)
            
            # Verificar si el encabezado está alineado horizontalmente con T1 (aprox)
            if abs(x_min_enc - x_min_t1) < 200: 
                x_min_final = x_min_t1
                x_max_final = x_max_t1
                print("[INFO] Usando ancho de Tabla 1 para la tabla sintética.")
        
        # Definir altura fija estimada pequeña (solo la sección 7)
        # Como pidieron "la primer parte de 3 divisiones", usaremos una altura estándar pequeña.
        # 150px suele ser suficiente para 1 renglón + encabezado.
        altura_estimada = 150 
        y_max_final = y_min_enc + altura_estimada
        
        # Construir polígono rectangular [x1, y1, x2, y1, x2, y2, x1, y2]
        synthetic_polygon = [
            x_min_final, y_min_enc,
            x_max_final, y_min_enc,
            x_max_final, y_max_final,
            x_min_final, y_max_final
        ]
        
        poligonos_retorno.append(synthetic_polygon)
        print(f"[INFO] Tabla 3 sintética agregada (Altura fija pequeña). Y: {y_min_enc} a {y_max_final}")

    else:
        print("[ADVERTENCIA] No se encontró el encabezado ni tabla relacionada.")
        # Fallback original: Si existe una 3ra tabla en la lista general, usarla?
        if len(resultado.tables) >= 3:
             print("[INFO] Usando tabla índice 2 como fallback genérico.")
             # Aplicar lógica de 1/3 también al fallback
             poly_fallback = list(resultado.tables[2].bounding_regions[0].polygon)
             
             y_coords_fb = [poly_fallback[i] for i in range(1, len(poly_fallback), 2)]
             y_min_fb = min(y_coords_fb)
             y_max_fb = max(y_coords_fb)
             nuevo_alto_fb = (y_max_fb - y_min_fb) / 3
             nuevo_y_max_fb = y_min_fb + nuevo_alto_fb
             
             y_center_fb = (y_min_fb + y_max_fb) / 2
             for k in range(1, len(poly_fallback), 2):
                if poly_fallback[k] > y_center_fb:
                    poly_fallback[k] = nuevo_y_max_fb
             
             poligonos_retorno.append(poly_fallback)
             print(f"[INFO] Fallback recortado a 1/3 de su altura original.")

    return poligonos_retorno

    return poligonos_retorno
