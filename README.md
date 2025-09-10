# Generador de Comandos gcloud storage

Aplicación de escritorio en **Python + ttkbootstrap (Tkinter mejorado)** que permite generar comandos de `gcloud storage` a partir de una lista estructurada de acciones.  
Funciona como un **asistente interactivo** para construir comandos CLI de Google Cloud Storage con placeholders personalizables.

---

## 🚀 Características

- **Explorador de acciones** en árbol (Buckets, Objetos, IAM, Operaciones globales, Transferencias).
- **Parámetros dinámicos**:
  - Menú desplegable para regiones (desde `params/regions.json`).
  - Menú desplegable para storage classes (desde `params/storage_classes.json`).
  - Entradas libres para nombres de bucket, objetos y otros parámetros.
- **Generación en tiempo real** del comando gcloud.
- **Botón de copiar** con confirmación rápida (“Comando copiado ✅”).
- **Temas personalizables** con `ttkbootstrap`.
- **Soporte extendido** para operaciones de IAM, seguridad, transferencias y gestión avanzada de objetos.

---

## 📂 Estructura del proyecto

```
.
├── actions/
│   └── storage.json        # Definición jerárquica de acciones (Buckets, Objetos, IAM, etc.)
├── params/
│   ├── regions.json        # Lista de regiones GCP
│   └── storage_classes.json# Lista de clases de almacenamiento
├── instraestructure/
│   └── command_builder.py  # Función para interpolar parámetros en comandos
│   └── loader.py               # Carga de ficheros JSON/YAML
├── app.py    # Aplicación principal con UI
└── README.md               # Este archivo
```

---

## 🖥️ Uso

1. Ejecuta la aplicación:
   ```bash
   python app.py
   ```

2. Selecciona una acción en el árbol lateral (ejemplo: **Buckets → Creación → Crear bucket**).  
3. Completa los parámetros (ej. `bucket`, `region`, `storage_class`).  
4. El comando se generará automáticamente.  
5. Pulsa **📋 Copiar** para llevarlo al portapapeles.

---

## 📌 Ejemplo de salida

Seleccionando `Crear bucket` con parámetros:

- bucket = `my-bucket`
- region = `us-east1`
- storage_class = `STANDARD`

Se genera:

```bash
gcloud storage buckets create my-bucket --location=us-east1 --default-storage-class=STANDARD
```

---

## 📊 Roadmap de Features

El archivo [`features_roadmap.json`](features_roadmap.json) contiene un mapeo de:

- ✅ **Soportado**
- ❌ **No soportado**
- 💡 **Sugerencias** de mejora

Ejemplo (extracto):

```json
"Buckets": {
  "Soportado": ["Crear", "Listar", "Borrar", "Lifecycle", "Etiquetas"],
  "NoSoportado": ["Multi-region config", "Retención lock (WORM)", "Public Access Prevention"],
  "Sugerencia": "Añadir comandos avanzados de bucket + editor de políticas públicas"
}
```

---

## 📦 Requisitos

- Python 3.9+
- Dependencias:
  ```bash
  pip install ttkbootstrap
  ```

---

## 🔮 Mejoras futuras

- Validaciones en vivo con `google-cloud-storage` SDK.  
- Estimación de costes vía Pricing API.  
- Asistente paso a paso (wizard).  
- Compatibilidad extendida con comandos exclusivos de `gsutil`.  
- Exportar a `.sh` para automatización.

---

## ✨ Créditos

Desarrollado como prototipo de asistente para **GCP Storage CLI**.  
Facilita la generación rápida y correcta de comandos para administradores, developers y data engineers.
