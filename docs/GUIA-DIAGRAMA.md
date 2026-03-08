# Guía para Crear el Diagrama de Arquitectura Profesional

## Iconos Incluidos

Los iconos oficiales de Azure están en la carpeta `docs/azure-icons/`:
- `azure-openai.svg` - Azure OpenAI
- `azure-speech.svg` - Azure Speech Services  
- `azure-vm.svg` - Virtual Machine
- `browser.svg` - Navegador/Cliente

## Herramienta Recomendada: Draw.io (Diagrams.net)

1. Abre https://app.diagrams.net
2. Selecciona "Create New Diagram"
3. Elige "Blank Diagram"

---

## Paso 1: Configurar el Lienzo

1. **File → Page Setup**
2. Tamaño: **Letter Landscape** o **A4 Landscape**
3. Fondo: Blanco o gradiente suave

---

## Paso 2: Crear los Grupos (Contenedores)

Crea 5 rectángulos redondeados como contenedores:

### Grupo 1: Cliente (Navegador Web)
- **Color**: Azul claro (#E3F2FD)
- **Borde**: Azul (#1976D2)
- **Posición**: Izquierda
- **Contenido**:
  - 🎙️ Micrófono
  - 🖥️ Interfaz Web
  - 🔊 Altavoz

### Grupo 2: Cloudflare
- **Color**: Naranja claro (#FFF3E0)
- **Borde**: Naranja (#F57C00)
- **Posición**: Centro-izquierda
- **Contenido**:
  - 🔒 Quick Tunnel HTTPS

### Grupo 3: Azure VM (Ubuntu)
- **Color**: Morado claro (#F3E5F5)
- **Borde**: Morado (#7B1FA2)
- **Posición**: Centro
- **Icono**: `azure-vm.svg`
- **Contenido**:
  - ⚙️ Flask + Gunicorn
  - 🔄 pydub + FFmpeg
  - 🤖 Bot Engine
  - 📚 Knowledge Base BCS

### Grupo 4: Azure Speech Services
- **Color**: Verde claro (#E8F5E9)
- **Borde**: Verde (#388E3C)
- **Posición**: Derecha-arriba
- **Icono**: `azure-speech.svg`
- **Contenido**:
  - 🎤→📝 STT (Speech-to-Text)
  - 📝→🔊 TTS (Andrew DragonHD)

### Grupo 5: Azure OpenAI
- **Color**: Amarillo claro (#FFFDE7)
- **Borde**: Amarillo (#FBC02D)
- **Posición**: Derecha-abajo
- **Icono**: `azure-openai.svg`
- **Contenido**:
  - 🧠 GPT-4o-mini

---

## Paso 3: Importar Iconos SVG

1. **File → Import from → Device**
2. Selecciona los SVG de `docs/azure-icons/`
3. Posiciona cada icono en la esquina superior de su grupo
4. Tamaño recomendado: 48x48 px

---

## Paso 4: Agregar las Flechas (Flujo de Datos)

### Flujo de Entrada de Voz (Usuario habla):
```
① Micrófono ──WebM──→ Flask
④ Flask ──WebM──→ pydub
⑤ pydub ──WAV──→ STT
⑥ STT ──Texto──→ Bot Engine
```

### Flujo de Chat:
```
② Interfaz Web ──HTTPS──→ Cloudflare Tunnel
③ Tunnel ──HTTP:5000──→ Flask
⑦ Flask ──Mensaje──→ Bot Engine
⑧ Bot Engine ──Chat API──→ GPT-4o-mini
⑨ GPT-4o-mini ──Respuesta──→ Bot Engine
⑩ Bot Engine ──Texto──→ Flask
```

### Flujo de Salida de Voz (Bot responde):
```
⑪ Flask ──Texto──→ TTS
⑫ TTS ──MP3 48kHz──→ Flask
⑬ Flask ──Audio Stream──→ Altavoz
```

### Estilo de Flechas:
- **Solicitud (request)**: Línea sólida, punta de flecha
- **Respuesta (response)**: Línea punteada, punta de flecha
- **Grosor**: 2px
- **Color**: Mismo que el grupo de origen

---

## Paso 5: Agregar Leyenda

Crear un rectángulo en la esquina inferior izquierda:

```
┌─────────────────────────────────────┐
│ LEYENDA                             │
├─────────────────────────────────────┤
│ ───→  Solicitud (request)           │
│ - - →  Respuesta (response)         │
│ ①-⑬  Flujo numerado                │
│                                     │
│ 🔵 Cliente   🟠 Red   🟣 Servidor   │
│ 🟢 Speech   🟡 IA                   │
└─────────────────────────────────────┘
```

---

## Paso 6: Agregar Título y Metadatos

En la parte superior del diagrama:

```
╔════════════════════════════════════════════════════════════╗
║  ARQUITECTURA - ASESOR VIRTUAL BANCO CAJA SOCIAL           ║
║  Azure OpenAI + Azure Speech + Flask                        ║
╚════════════════════════════════════════════════════════════╝
```

---

## Paso 7: Exportar

1. **File → Export as → PNG** (para presentaciones)
2. **File → Export as → PDF** (para documentos)
3. **File → Export as → SVG** (para web)

Configuración recomendada:
- Escala: 200%
- Borde: 10px
- Fondo: Transparente o Blanco

---

## Diagrama de Referencia (ASCII)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    ARQUITECTURA - ASESOR VIRTUAL BCS                                 │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐    ┌──────────────┐    ┌─────────────────────┐    ┌──────────────────┐
│ 🌐 CLIENTE       │    │ ☁️ CLOUDFLARE │    │ 🖥️ AZURE VM         │    │ 🎤 AZURE SPEECH   │
│                  │    │              │    │    Ubuntu 24.04     │    │                  │
│  ┌────────────┐  │    │ ┌──────────┐ │    │  ┌───────────────┐  │    │  ┌────────────┐  │
│  │ 🎙️ Micrófono│──┼────┼─┼──────────┼─┼────┼─→│ Flask+Gunicorn│──┼────┼─→│    STT     │  │
│  └────────────┘  │ ①  │ │  Tunnel  │ │ ③  │  └───────┬───────┘  │ ⑤  │  │  es-CO     │  │
│                  │    │ │  HTTPS   │ │    │          │ ④        │    │  └─────┬──────┘  │
│  ┌────────────┐  │    │ └──────────┘ │    │  ┌───────▼───────┐  │    │        │ ⑥      │
│  │ 🖥️ Interfaz │──┼────┼─→    ②      │    │  │pydub + FFmpeg │  │    │        │         │
│  │    Web     │  │    │              │    │  └───────────────┘  │    │  ┌─────▼──────┐  │
│  └────────────┘  │    └──────────────┘    │                     │    │  │    TTS     │  │
│                  │                        │  ┌───────────────┐  │    │  │ DragonHD   │  │
│  ┌────────────┐  │                        │  │  Bot Engine   │←─┼────┼──┤   48kHz    │  │
│  │ 🔊 Altavoz │←─┼────────────────────────┼──│  + KB BCS     │  │    │  └────────────┘  │
│  └────────────┘  │         ⑬             │  └───────┬───────┘  │    └──────────────────┘
│                  │                        │          │ ⑦⑧      │
└──────────────────┘                        │          ▼         │    ┌──────────────────┐
                                            │  ┌───────────────┐ │    │ 🧠 AZURE OPENAI   │
                                            │  │   ⑨⑩⑪⑫      │ │    │                  │
                                            │  └───────────────┘ │    │  ┌────────────┐  │
                                            │                     │    │  │ GPT-4o-mini│  │
                                            └─────────────────────┘    │  └────────────┘  │
                                                                       └──────────────────┘
```

---

## Colores Oficiales Azure

| Servicio | Color HEX | RGB |
|----------|-----------|-----|
| Azure (general) | #0078D4 | 0, 120, 212 |
| OpenAI | #10A37F | 16, 163, 127 |
| Speech | #5C2D91 | 92, 45, 145 |
| VM | #0078D4 | 0, 120, 212 |
| Cloudflare | #F38020 | 243, 128, 32 |

---

## Archivo Draw.io Base

El archivo `arquitectura-diagram.drawio` contiene una versión básica que puedes editar.
Ábrelo en https://app.diagrams.net y reemplaza los emojis por los iconos SVG.
