# 📄 LECTOR - Sistema de Procesamiento de Documentos

Sistema completo para procesamiento de documentos con **enderezado automático** y **extracción de tablas** usando **OpenCV** y **Azure AI Document Intelligence**.

---

## 🎯 Características

### ✨ FLUJO 1: Enderezado de Documentos
- 📸 Efecto CamScanner profesional
- 🔍 Detección automática de bordes del documento
- 📐 Corrección de perspectiva
- 🎨 Conversión a blanco y negro nítido
- 💾 Guardado de imágenes intermedias del proceso

### ✨ FLUJO 2: Extracción de Tablas
- 🤖 Detección de tablas con Azure AI Document Intelligence
- 📊 Cálculo preciso de bounding boxes
- ✂️ Recorte automático de regiones
- 💯 Alta precisión con modelo `prebuilt-layout`

---

## 📁 Estructura del Proyecto

```
LECTOR/
├── README.md                      # Este archivo
├── requirements.txt               # Dependencias del proyecto
├── .gitignore                     # Archivos a ignorar en git
├── venv/                          # Entorno virtual Python
│
├── PRUEBASIMG/                    # 📥 Imágenes de entrada
│   ├── A1.jpeg
│   ├── A2.jpeg
│   └── A3.jpg
│
├── proceso/                       # 🔄 Imágenes intermedias (FLUJO 1)
│   ├── 1_escala_grises.jpg
│   ├── 2_deteccion_bordes.jpg
│   ├── 3_contorno_detectado.jpg
│   ├── 4_documento_enderezado.jpg
│   └── 5_resultado_final_escaner.jpg
│
├── recortes/                      # ✂️ Tablas extraídas (FLUJO 2)
│
├── FLUJO1_ENDEREZADO/             # 📐 Script de enderezado
│   └── document_scanner.py
│
└── FLUJO2_RECORTE/                # 📊 Script de extracción
    ├── table_extractor.py
    └── .env                       # Credenciales de Azure
```

---

## 🚀 Instalación

### Requisitos Previos
- **Python 3.8+**
- **Azure AI Document Intelligence** (para FLUJO 2)

### Paso 1: Clonar o descargar el proyecto

```bash
cd LECTOR
```

### Paso 2: Crear y activar entorno virtual

```bash
# Crear entorno virtual
python -m venv venv

# Activar (Windows)
venv\Scripts\activate

# Activar (Linux/Mac)
source venv/bin/activate
```

### Paso 3: Instalar dependencias

```bash
pip install -r requirements.txt
```

### Paso 4: Configurar Azure AI (solo para FLUJO 2)

1. **Obtener credenciales de Azure:**
   - Ve a [Azure Portal](https://portal.azure.com)
   - Crea un recurso "Document Intelligence"
   - Copia el **Endpoint** y **API Key**

2. **Crear archivo `.env`:**
   ```bash
   cd FLUJO2_RECORTE
   # Edita .env con tus credenciales
   ```

   Contenido del archivo `.env`:
   ```env
   AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://tu-recurso.cognitiveservices.azure.com/
   AZURE_DOCUMENT_INTELLIGENCE_KEY=tu_api_key_aqui
   ```

---

## 📖 Uso

### 🔷 FLUJO 1: Enderezar Documento

Convierte una foto de documento en una imagen escaneada profesional.

```bash
# Activar entorno virtual
venv\Scripts\activate

# Ejecutar FLUJO 1
cd FLUJO1_ENDEREZADO
python document_scanner.py ../PRUEBASIMG/A1.jpeg

# Resultado:
# - Imágenes intermedias en: ../proceso/
# - Documento final: ../proceso/5_resultado_final_escaner.jpg
```

**Salida del FLUJO 1:**
- `1_escala_grises.jpg` - Imagen en escala de grises
- `2_deteccion_bordes.jpg` - Bordes detectados con Canny
- `3_contorno_detectado.jpg` - Contorno del documento
- `4_documento_enderezado.jpg` - Documento con perspectiva corregida
- `5_resultado_final_escaner.jpg` - **Resultado final (efecto escáner)**

---

### 🔷 FLUJO 2: Extraer Tabla

Detecta y recorta tablas de documentos usando Azure AI.

```bash
# Activar entorno virtual
venv\Scripts\activate

# Ejecutar FLUJO 2
cd FLUJO2_RECORTE
python table_extractor.py ../PRUEBASIMG/A3.jpg

# O usar documento enderezado del FLUJO 1
python table_extractor.py ../proceso/5_resultado_final_escaner.jpg

# Resultado:
# - Tabla recortada en: ../recortes/
```

**Salida del FLUJO 2:**
- Tabla extraída guardada en `../recortes/`
- Ventana mostrando el recorte
- Coordenadas del bounding box en consola

---

### 🔁 Pipeline Completo (FLUJO 1 → FLUJO 2)

Procesa un documento desde foto cruda hasta tabla extraída:

```bash
# 1. Activar entorno virtual
venv\Scripts\activate

# 2. Enderezar documento
cd FLUJO1_ENDEREZADO
python document_scanner.py ../PRUEBASIMG/A1.jpeg

# 3. Extraer tabla
cd ../FLUJO2_RECORTE
python table_extractor.py ../proceso/5_resultado_final_escaner.jpg

# Resultado final en: ../recortes/
```

---

## 🛠️ Tecnologías Utilizadas

| Componente | Tecnología | Propósito |
|------------|-----------|-----------|
| **Visión Artificial** | OpenCV 4.13+ | Procesamiento de imágenes |
| **Cálculos Numéricos** | NumPy 2.4+ | Operaciones con arrays |
| **IA Cloud** | Azure AI Document Intelligence | Detección de tablas |
| **Variables de Entorno** | python-dotenv | Gestión de credenciales |

---

## 📊 Ejemplos de Resultados

### FLUJO 1: Antes y Después

| Entrada | Salida |
|---------|--------|
| 📷 Foto de documento inclinada | 📄 Documento enderezado con efecto escáner |

### FLUJO 2: Extracción de Tabla

| Entrada | Salida |
|---------|--------|
| 📄 Documento con tabla | 📊 Tabla recortada con precisión |

---

## ⚙️ Configuración Avanzada

### Ajustar calidad de FLUJO 1

Edita `FLUJO1_ENDEREZADO/document_scanner.py`:

```python
# Línea 318: Cambiar ancho de procesamiento
imagen_procesamiento, ratio = redimensionar_imagen(imagen_original, ancho_objetivo=500)

# Línea 276-282: Ajustar umbralización adaptativa
imagen_escaneada = cv2.adaptiveThreshold(
    gris,
    255,
    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    cv2.THRESH_BINARY,
    11,  # Tamaño de bloque (debe ser impar)
    10   # Constante C
)
```

### Cambiar modelo de Azure AI

Edita `FLUJO2_RECORTE/table_extractor.py`:

```python
# Línea 73: Cambiar modelo
poller = self.client.begin_analyze_document(
    model_id="prebuilt-layout",  # Otros: prebuilt-document, prebuilt-invoice
    body=imagen_bytes,
    content_type="application/octet-stream"
)
```

---

## 🐛 Solución de Problemas

### Error: `ModuleNotFoundError: No module named 'cv2'`

**Solución:**
```bash
# Asegúrate de activar el venv correcto
conda deactivate  # Si usas conda
venv\Scripts\activate
pip install -r requirements.txt
```

### Error: `No connection adapters were found`

**Causa:** Credenciales de Azure incorrectas.

**Solución:**
1. Verifica que `FLUJO2_RECORTE/.env` tenga valores reales
2. El endpoint debe empezar con `https://` y terminar con `/`
3. La API Key debe ser alfanumérica larga

### No se detectan tablas

**Soluciones:**
- Asegúrate de que la imagen tenga una tabla visible
- La tabla debe tener líneas claras y estructura definida
- Prueba primero con FLUJO 1 para enderezar el documento
- Verifica que la imagen no esté borrosa

### Error: `El archivo no existe`

**Causa:** Ruta incorrecta o extensión de archivo.

**Solución:**
- Usa rutas relativas correctas (ej: `../PRUEBASIMG/A1.jpeg`)
- Verifica la extensión: `.jpg` vs `.jpeg`
- Usa `ls` para ver archivos disponibles

---

## 📚 Documentación de APIs

- **OpenCV:** https://docs.opencv.org/
- **Azure AI Document Intelligence:** https://learn.microsoft.com/azure/ai-services/document-intelligence/
- **NumPy:** https://numpy.org/doc/

---

## 🔒 Seguridad

⚠️ **IMPORTANTE:**
- **NO subas** el archivo `.env` a git (ya está en `.gitignore`)
- **NO compartas** tus credenciales de Azure
- Rota tus API Keys periódicamente desde Azure Portal

---

## 📝 Licencia

Proyecto educativo para procesamiento de documentos con visión artificial.

---

## 👨‍💻 Autor

Desarrollado con ❤️ usando **OpenCV**, **Azure AI** y **Python**

---

## 🚀 Próximas Mejoras

- [ ] Detección múltiple de tablas
- [ ] Exportación a Excel/CSV
- [ ] Interfaz gráfica (GUI)
- [ ] API REST
- [ ] Procesamiento por lotes
- [ ] Detección de texto con OCR

---

**¿Preguntas o problemas?** Abre un issue en el repositorio.
