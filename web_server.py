#!/usr/bin/env python3
"""
Web server for the Banco Caja Social Virtual Advisor.
Provides a REST API for the web interface using Azure OpenAI and Azure Speech.
"""

import io
import os
import sys
import subprocess
import tempfile
import threading
import webbrowser

from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
from dotenv import load_dotenv
from pydub import AudioSegment

from app.bot import AsesorBancoCajaSocial
from app.voice import texto_a_voz_bytes, transcribir_audio


def get_base_path():
    """Get base path, compatible with PyInstaller."""
    if getattr(sys, '_MEIPASS', None):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def abrir_navegador(url: str):
    """Open browser, preferring Chrome with fallback to default."""
    chrome_paths = [
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '/Applications/Chromium.app/Contents/MacOS/Chromium',
    ]
    for chrome in chrome_paths:
        if os.path.exists(chrome):
            try:
                subprocess.Popen([chrome, url])
                return
            except Exception:
                continue
    webbrowser.open(url)


# Load environment variables
base_path = get_base_path()
env_path = os.path.join(base_path, '.env')
load_dotenv(env_path)

app = Flask(
    __name__,
    template_folder=os.path.join(base_path, 'web', 'templates'),
    static_folder=os.path.join(base_path, 'web', 'static'),
)
CORS(app)

# Validate required environment variables
required_vars = [
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_KEY",
    "AZURE_OPENAI_DEPLOYMENT_NAME",
    "AZURE_SPEECH_KEY",
    "AZURE_SPEECH_REGION",
]
for var in required_vars:
    if not os.getenv(var):
        raise ValueError(f"{var} no está configurada en las variables de entorno")

# Initialize advisor with Azure OpenAI
asesor = AsesorBancoCajaSocial(
    endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
)

# Azure Speech credentials
SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")


@app.route('/')
def index():
    """Serve the web interface."""
    return render_template('index.html')


@app.route('/favicon.ico')
def favicon():
    """Serve favicon for browser tab."""
    return send_file(
        os.path.join(app.static_folder, 'img', 'bcs-ico.png'),
        mimetype='image/png'
    )


@app.route('/chat', methods=['POST'])
def chat():
    """Endpoint to process user messages."""
    try:
        data = request.get_json()
        mensaje = data.get('message', '').strip()

        if not mensaje:
            return jsonify({'error': 'Mensaje vacio'}), 400

        respuesta = asesor.responder(mensaje)

        return jsonify({
            'response': respuesta,
            'status': 'success'
        })

    except Exception as e:
        print(f"Error procesando mensaje: {e}")
        return jsonify({
            'error': 'Error interno del servidor',
            'details': str(e)
        }), 500


@app.route('/reset', methods=['POST'])
def reset():
    """Endpoint to reset the conversation."""
    try:
        asesor.reiniciar_conversacion()
        return jsonify({
            'status': 'success',
            'message': 'Conversación reiniciada'
        })
    except Exception as e:
        return jsonify({
            'error': 'Error reiniciando conversación',
            'details': str(e)
        }), 500


@app.route('/transcribe', methods=['POST'])
def transcribe():
    """Endpoint to transcribe audio from the client microphone."""
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file'}), 400

        audio_file = request.files['audio']

        # Save uploaded audio — use mktemp to avoid Windows file locking
        webm_path = os.path.join(tempfile.gettempdir(), f'bcs_{os.getpid()}_{id(request)}.webm')
        audio_file.save(webm_path)
        print(f'[TRANSCRIBE] webm saved: {webm_path} ({os.path.getsize(webm_path)} bytes)', flush=True)

        # Convert webm to wav (Azure Speech SDK requires wav)
        wav_path = webm_path.replace('.webm', '.wav')
        try:
            audio_segment = AudioSegment.from_file(webm_path, format='webm')
            audio_segment.export(wav_path, format='wav')
            print(f'[TRANSCRIBE] wav exported: {wav_path} ({os.path.getsize(wav_path)} bytes), duration={len(audio_segment)}ms', flush=True)

            text = transcribir_audio(wav_path, SPEECH_KEY, SPEECH_REGION)
            print(f'[TRANSCRIBE] result: {repr(text)}', flush=True)

            if text:
                return jsonify({'text': text, 'status': 'success'})
            else:
                return jsonify({'text': '', 'status': 'no_speech'})

        finally:
            for f in [webm_path, wav_path]:
                try:
                    if os.path.exists(f):
                        os.unlink(f)
                except OSError:
                    pass

    except Exception as e:
        print(f'Error transcribing: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/voz', methods=['POST'])
def voz():
    """Endpoint to generate audio with Azure Speech TTS."""
    try:
        data = request.get_json()
        texto = data.get('texto', '').strip()

        if not texto:
            return jsonify({'error': 'Texto vacio'}), 400

        voz_nombre = data.get('voz', 'es-CO-SalomeNeural')

        audio_bytes = texto_a_voz_bytes(
            texto=texto,
            speech_key=SPEECH_KEY,
            speech_region=SPEECH_REGION,
            voz=voz_nombre,
        )

        buffer = io.BytesIO(audio_bytes)
        buffer.seek(0)
        return send_file(buffer, mimetype='audio/mpeg')

    except Exception as e:
        print(f"Error generando audio: {e}")
        return jsonify({'error': 'Error generando audio'}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'Banco Caja Social - Asesor Virtual (Azure)'
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    url = f'http://localhost:{port}'

    print("Iniciando servidor web del Asesor Virtual...")
    print(f"Servidor corriendo en: {url}")
    print("Presione Ctrl+C para detener el servidor\n")

    threading.Timer(1.5, abrir_navegador, args=[url]).start()

    app.run(host='0.0.0.0', port=port, debug=False)
