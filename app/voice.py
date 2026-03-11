"""
Voice module for the Banco Caja Social virtual advisor.
Includes text-to-speech (TTS) and speech-to-text (STT) via Azure Speech SDK.
"""

import os
import tempfile
import platform

import azure.cognitiveservices.speech as speechsdk

# Andrew Dragon HD - LLM-based voice with automatic emotional detection
# Male voice, professional but friendly tone
VOZ_DEFAULT = "en-US-Andrew:DragonHDLatestNeural"


def _get_speech_config(speech_key: str, speech_region: str) -> speechsdk.SpeechConfig:
    """Create a SpeechConfig with the given credentials."""
    return speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)


def texto_a_voz(
    texto: str,
    speech_key: str,
    speech_region: str,
    voz: str = VOZ_DEFAULT,
    reproducir: bool = True,
) -> str:
    """
    Convert text to audio using Azure Speech SDK (neural voices).

    Args:
        texto: Text to convert to speech.
        speech_key: Azure Speech subscription key.
        speech_region: Azure Speech region.
        voz: Neural voice name to use.
        reproducir: If True, plays the audio automatically.

    Returns:
        Path to the generated audio file.
    """
    config = _get_speech_config(speech_key, speech_region)
    config.speech_synthesis_voice_name = voz
    config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio48Khz192KBitRateMonoMp3
    )

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        ruta_audio = tmp.name

    audio_config = speechsdk.audio.AudioOutputConfig(filename=ruta_audio)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=config, audio_config=audio_config)
    result = synthesizer.speak_text_async(texto).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        if reproducir:
            reproducir_audio(ruta_audio)
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation = result.cancellation_details
        print(f"[ERROR] TTS cancelado: {cancellation.reason}")
        if cancellation.error_details:
            print(f"    Detalle: {cancellation.error_details}")

    return ruta_audio


def _build_ssml(texto: str, voz: str) -> str:
    """
    Build SSML markup for warm, friendly bank advisor speech.
    Uses prosody adjustments for a conversational, approachable tone.
    """
    # Escape XML special characters
    texto_escaped = (
        texto.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
    
    # Ava DragonHD automatically detects emotional context from text
    # Uses <lang> tag to speak in Colombian Spanish
    # Minimal prosody adjustments - let the HD voice handle naturalness
    return f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" 
    xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="es-CO">
    <voice name="{voz}">
        <lang xml:lang="es-CO">
            {texto_escaped}
        </lang>
    </voice>
</speak>"""


def texto_a_voz_bytes(
    texto: str,
    speech_key: str,
    speech_region: str,
    voz: str = VOZ_DEFAULT,
) -> bytes:
    """
    Convert text to audio bytes using Azure Speech SDK with SSML.
    Used by the web server to stream audio to the browser.

    Returns:
        Audio data as bytes (MP3).
    """
    config = _get_speech_config(speech_key, speech_region)
    config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio48Khz192KBitRateMonoMp3
    )

    synthesizer = speechsdk.SpeechSynthesizer(speech_config=config, audio_config=None)
    ssml = _build_ssml(texto, voz)
    result = synthesizer.speak_ssml_async(ssml).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return result.audio_data

    cancellation = result.cancellation_details
    raise RuntimeError(f"TTS falló: {cancellation.reason} - {cancellation.error_details}")


def transcribir_audio(
    ruta_audio: str,
    speech_key: str,
    speech_region: str,
    idioma: str = "es-CO",
) -> str | None:
    """
    Transcribe an audio file to text using Azure Speech SDK.

    Args:
        ruta_audio: Path to the audio file (WAV format).

    Returns:
        Recognized text or None if recognition failed.
    """
    config = _get_speech_config(speech_key, speech_region)
    config.speech_recognition_language = idioma

    audio_config = speechsdk.audio.AudioConfig(filename=ruta_audio)
    recognizer = speechsdk.SpeechRecognizer(speech_config=config, audio_config=audio_config)
    result = recognizer.recognize_once()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        return result.text
    elif result.reason == speechsdk.ResultReason.NoMatch:
        print(f"[STT] NoMatch: {result.no_match_details}", flush=True)
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation = result.cancellation_details
        print(f"[STT] Canceled: reason={cancellation.reason}, details={cancellation.error_details}", flush=True)
    else:
        print(f"[STT] Unexpected reason: {result.reason}", flush=True)
    return None


def escuchar_microfono(
    speech_key: str,
    speech_region: str,
    idioma: str = "es-CO",
) -> str | None:
    """
    Capture audio from microphone and convert to text using Azure Speech SDK.

    Returns:
        Recognized text or None if recognition failed.
    """
    config = _get_speech_config(speech_key, speech_region)
    config.speech_recognition_language = idioma

    recognizer = speechsdk.SpeechRecognizer(speech_config=config)

    print("Escuchando... (hable ahora)")
    result = recognizer.recognize_once()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        return result.text
    elif result.reason == speechsdk.ResultReason.NoMatch:
        print("No se detecto voz. Intente de nuevo.")
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation = result.cancellation_details
        print(f"[ERROR] Reconocimiento cancelado: {cancellation.reason}")
        if cancellation.error_details:
            print(f"    Detalle: {cancellation.error_details}")
    return None


def reproducir_audio(ruta: str):
    """Play an audio file based on the operating system."""
    sistema = platform.system()
    try:
        if sistema == "Darwin":
            os.system(f'afplay "{ruta}"')
        elif sistema == "Linux":
            if os.system("which mpg123 > /dev/null 2>&1") == 0:
                os.system(f'mpg123 -q "{ruta}"')
            elif os.system("which ffplay > /dev/null 2>&1") == 0:
                os.system(f'ffplay -nodisp -autoexit -loglevel quiet "{ruta}"')
            else:
                print("[AVISO] No se encontro reproductor de audio. Instale mpg123.")
        elif sistema == "Windows":
            os.system(f'start "" "{ruta}"')
    except Exception as e:
        print(f"[ERROR] Reproduciendo audio: {e}")


def limpiar_archivos_temporales(rutas: list[str]):
    """Remove temporary audio files."""
    for ruta in rutas:
        try:
            if os.path.exists(ruta):
                os.remove(ruta)
        except OSError:
            pass
