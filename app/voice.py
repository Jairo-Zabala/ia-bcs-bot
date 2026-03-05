"""
Voice module for the Banco Caja Social virtual advisor.
Includes text-to-speech (TTS) via Edge TTS and optional speech-to-text (STT).
"""

import asyncio
import os
import tempfile
import platform

import edge_tts

# Colombian neural voice (female). Male alternative: "es-CO-GonzaloNeural"
VOZ_DEFAULT = "es-CO-SalomeNeural"


def texto_a_voz(texto: str, voz: str = VOZ_DEFAULT, reproducir: bool = True) -> str:
    """
    Convert text to audio using Microsoft Edge TTS (neural voices).

    Args:
        texto: Text to convert to speech.
        voz: Neural voice name to use.
        reproducir: If True, plays the audio automatically.

    Returns:
        Path to the generated audio file.
    """
    # Create temp file for audio
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        ruta_audio = tmp.name

    # Generate audio with Edge TTS (async)
    asyncio.run(_generar_audio(texto, voz, ruta_audio))

    if reproducir:
        reproducir_audio(ruta_audio)

    return ruta_audio


async def _generar_audio(texto: str, voz: str, ruta: str):
    """Generate audio using Edge TTS asynchronously."""
    communicate = edge_tts.Communicate(texto, voz)
    await communicate.save(ruta)


def reproducir_audio(ruta: str):
    """
    Play an audio file based on the operating system.

    Args:
        ruta: Path to the audio file.
    """
    sistema = platform.system()
    try:
        if sistema == "Darwin":  # macOS
            os.system(f'afplay "{ruta}"')
        elif sistema == "Linux":
            # Try different audio players
            if os.system("which mpg123 > /dev/null 2>&1") == 0:
                os.system(f'mpg123 -q "{ruta}"')
            elif os.system("which ffplay > /dev/null 2>&1") == 0:
                os.system(f'ffplay -nodisp -autoexit -loglevel quiet "{ruta}"')
            else:
                print("[AVISO] No se encontro reproductor de audio. Instale mpg123: sudo apt install mpg123")
        elif sistema == "Windows":
            os.system(f'start "" "{ruta}"')
        else:
            print(f"[AVISO] Sistema operativo no soportado para reproduccion: {sistema}")
    except Exception as e:
        print(f"[ERROR] Reproduciendo audio: {e}")


def escuchar_microfono(timeout: int = 5, idioma: str = "es-CO") -> str | None:
    """
    Capture audio from microphone and convert to text using speech_recognition.

    Args:
        timeout: Max seconds to wait for speech.
        idioma: Language code for recognition (defaults to Colombian Spanish).

    Returns:
        Recognized text or None if recognition failed.
    """
    try:
        import speech_recognition as sr
    except ImportError:
        print("[AVISO] Para usar reconocimiento de voz, instale: pip install SpeechRecognition pyaudio")
        return None

    recognizer = sr.Recognizer()

    try:
        with sr.Microphone() as source:
            print("Escuchando... (hable ahora)")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=15)

        print("Procesando su mensaje...")
        texto = recognizer.recognize_google(audio, language=idioma)
        return texto

    except OSError as e:
        print(f"[ERROR] Accediendo al microfono: {e}")
        print("    Verifique que su microfono este conectado y tenga permisos.")
        print("    En macOS: Configuracion del Sistema > Privacidad y Seguridad > Microfono")
        return None
    except sr.WaitTimeoutError:
        print("No se detecto voz. Intente de nuevo.")
        return None
    except sr.UnknownValueError:
        print("No se pudo entender el audio. Intente de nuevo.")
        return None
    except sr.RequestError as e:
        print(f"[ERROR] Servicio de reconocimiento: {e}")
        return None


def limpiar_archivos_temporales(rutas: list[str]):
    """Remove temporary audio files."""
    for ruta in rutas:
        try:
            if os.path.exists(ruta):
                os.remove(ruta)
        except OSError:
            pass
