#!/usr/bin/env python3
"""
Web server for the Banco Caja Social Virtual Advisor.
Provides a REST API for the web interface.
"""

import asyncio
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
import edge_tts
import speech_recognition as sr
from pydub import AudioSegment

from app.bot import AsesorBancoCajaSocial


def get_base_path():
    """Get base path, compatible with PyInstaller."""
    if getattr(sys, '_MEIPASS', None):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def abrir_navegador(url: str):
    """Open browser, preferring Chrome with fallback to default."""
    # Common Chrome paths on macOS
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
    # Fallback: default browser
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

# Initialize advisor
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY no está configurada en las variables de entorno")

asesor = AsesorBancoCajaSocial(api_key=api_key, model_name="gemini-2.5-flash")


@app.route('/')
def index():
    """Serve the web interface."""
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    """Endpoint to process user messages."""
    try:
        data = request.get_json()
        mensaje = data.get('message', '').strip()
        
        if not mensaje:
            return jsonify({'error': 'Mensaje vacio'}), 400
        
        # Get advisor response
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

        # Save uploaded webm to temp file
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as tmp:
            audio_file.save(tmp.name)
            webm_path = tmp.name

        # Convert webm to wav (speech_recognition requires wav/flac/aiff)
        wav_path = webm_path.replace('.webm', '.wav')
        try:
            audio_segment = AudioSegment.from_file(webm_path, format='webm')
            audio_segment.export(wav_path, format='wav')

            recognizer = sr.Recognizer()
            with sr.AudioFile(wav_path) as source:
                audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language='es-CO')
            return jsonify({'text': text, 'status': 'success'})
        except sr.UnknownValueError:
            return jsonify({'text': '', 'status': 'no_speech'})
        except sr.RequestError as e:
            return jsonify({'error': f'Recognition service error: {e}'}), 500
        finally:
            for f in [webm_path, wav_path]:
                if os.path.exists(f):
                    os.unlink(f)

    except Exception as e:
        print(f'Error transcribing: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/voz', methods=['POST'])
def voz():
    """Endpoint to generate audio with Edge TTS (Microsoft neural voices)."""
    try:
        data = request.get_json()
        texto = data.get('texto', '').strip()

        if not texto:
            return jsonify({'error': 'Texto vacio'}), 400

        # Generate audio with Edge TTS (selected neural voice)
        voz = data.get('voz', 'es-CO-SalomeNeural')
        buffer = io.BytesIO()
        asyncio.run(_generar_audio_buffer(texto, buffer, voz))
        buffer.seek(0)

        return send_file(buffer, mimetype='audio/mpeg')

    except Exception as e:
        print(f"Error generando audio: {e}")
        return jsonify({'error': 'Error generando audio'}), 500


async def _generar_audio_buffer(texto: str, buffer: io.BytesIO, voz: str = "es-CO-SalomeNeural"):
    """Generate audio with Edge TTS and write to buffer."""
    communicate = edge_tts.Communicate(texto, voz)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buffer.write(chunk["data"])


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'Banco Caja Social - Asesor Virtual'
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    url = f'http://localhost:{port}'

    print("Iniciando servidor web del Asesor Virtual...")
    print(f"Servidor corriendo en: {url}")
    print("Presione Ctrl+C para detener el servidor\n")

    # Open Chrome after a short delay so Flask can start
    threading.Timer(1.5, abrir_navegador, args=[url]).start()

    app.run(host='0.0.0.0', port=port, debug=False)
