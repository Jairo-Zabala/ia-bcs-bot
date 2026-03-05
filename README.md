# Asesor Virtual - Banco Caja Social

Chatbot inteligente que simula un asesor del Banco Caja Social, con conocimiento completo de productos, servicios y requisitos del banco. Disponible en modo consola (CLI) y modo web con interfaz gráfica.

## Características

- **IA con Google Gemini** — Respuestas naturales basadas en información real del banco
- **Modo consola (CLI)** — Chat por terminal con soporte de voz
- **Modo web** — Interfaz gráfica con servidor Flask
- **Text-to-Speech** — Respuestas por voz en español colombiano (Edge TTS)
- **Speech-to-Text** — Entrada por micrófono opcional
- **Memoria conversacional** — Mantiene el contexto durante la sesión

## Requisitos Previos

- Python 3.10 o superior
- API Key de Google Gemini (gratuita) → [Obtener aquí](https://aistudio.google.com/apikey)
- (Opcional) `portaudio` para entrada por micrófono

## Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/Jairo-Zabala/ia-bcs-bot.git
cd ia-bcs-bot

# 2. Crear y activar entorno virtual
python3 -m venv venv
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env y agregar tu GEMINI_API_KEY
```

### Instalar soporte de micrófono (opcional)

```bash
# macOS
brew install portaudio
pip install SpeechRecognition pyaudio

# Linux (Debian/Ubuntu)
sudo apt install portaudio19-dev
pip install SpeechRecognition pyaudio
```

## Ejecución

### Modo Consola (CLI)

```bash
# Solo texto
python main.py

# Con respuestas por voz
python main.py --voz

# Voz + entrada por micrófono
python main.py --voz --microfono

# Usar otro modelo de Gemini
python main.py --modelo gemini-2.0-flash
```

### Modo Web

```bash
# Iniciar servidor (abre el navegador automáticamente)
python web_server.py

# Especificar puerto
PORT=8080 python web_server.py
```

El servidor estará disponible en `http://localhost:5000` (o el puerto configurado).

### Comandos durante el chat (modo consola)

| Comando     | Descripción                        |
|-------------|-------------------------------------|
| `/salir`    | Terminar la conversación           |
| `/nueva`    | Iniciar nueva conversación         |
| `/voz on`   | Activar respuestas por voz         |
| `/voz off`  | Desactivar respuestas por voz      |
| `/mic on`   | Activar entrada por micrófono      |
| `/mic off`  | Desactivar entrada por micrófono   |
| `/ayuda`    | Mostrar menú de comandos           |

## Generar Ejecutable

```bash
# Genera un binario standalone en dist/
python build.py

# Ejecutar
./dist/BancoCajaSocialBot
```

> El archivo `.env` con `GEMINI_API_KEY` debe estar junto al ejecutable.

## Estructura del Proyecto

```
banco_caja_social_bot/
├── app/
│   ├── __init__.py
│   ├── bot.py                # Integración con Gemini API
│   ├── knowledge_base.py     # Base de conocimiento del banco
│   └── voice.py              # Módulo de voz (TTS/STT)
├── web/
│   ├── static/
│   │   ├── css/styles.css
│   │   └── js/app.js
│   └── templates/
│       └── index.html
├── main.py                   # Punto de entrada CLI
├── web_server.py             # Punto de entrada Web (Flask)
├── build.py                  # Script para generar ejecutable
├── requirements.txt          # Dependencias Python
├── .env.example              # Plantilla de variables de entorno
└── README.md
```

## API Endpoints (modo web)

| Método | Ruta          | Descripción                     |
|--------|---------------|---------------------------------|
| GET    | `/`           | Interfaz web del chat           |
| POST   | `/chat`       | Enviar mensaje al asesor        |
| POST   | `/reset`      | Reiniciar conversación          |
| POST   | `/voz`        | Generar audio de texto (TTS)    |
| POST   | `/transcribe` | Transcribir audio a texto (STT) |
| GET    | `/health`     | Health check del servidor       |
