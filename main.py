#!/usr/bin/env python3
"""
Banco Caja Social Virtual Advisor.
Console application with text and voice support.

Usage:
    python main.py                    # Text mode
    python main.py --voz              # Voice responses
    python main.py --voz --microfono  # Voice input and output
"""

import argparse
import os
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from app.bot import AsesorBancoCajaSocial
from app.voice import texto_a_voz, escuchar_microfono, limpiar_archivos_temporales

console = Console()


BANNER = """
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║       BANCO CAJA SOCIAL - Asesor Virtual                 ║
║       Bienvenido a su Banco Amigo                        ║
║                                                          ║
╠══════════════════════════════════════════════════════════╣
║  Comandos:                                               ║
║    /salir     - Terminar la conversacion                 ║
║    /nueva     - Iniciar nueva conversacion               ║
║    /voz on    - Activar respuestas por voz               ║
║    /voz off   - Desactivar respuestas por voz            ║
║    /mic on    - Activar entrada por microfono            ║
║    /mic off   - Desactivar entrada por microfono         ║
║    /ayuda     - Mostrar este menu                        ║
╚══════════════════════════════════════════════════════════╝
"""


def obtener_api_key() -> str:
    """Get the Gemini API key from environment variables or user input."""
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print("\n[AVISO] No se encontro GEMINI_API_KEY en las variables de entorno.")
        print("   Puede configurarla de las siguientes formas:")
        print("   1. Crear un archivo .env con: GEMINI_API_KEY=su_clave_aqui")
        print("   2. Exportar la variable: export GEMINI_API_KEY=su_clave_aqui")
        print()
        api_key = input("   O ingrese su API key de Gemini ahora: ").strip()

    if not api_key:
        print("[ERROR] Se requiere una API key de Gemini para continuar.")
        print("   Obtenga una en: https://aistudio.google.com/apikey")
        sys.exit(1)

    return api_key


def procesar_comando(comando: str, voz_activa: bool, mic_activo: bool) -> tuple[bool, bool, bool]:
    """
    Process special commands.

    Returns:
        Tuple (continue_chat, voice_active, mic_active)
    """
    cmd = comando.lower().strip()

    if cmd == "/salir":
        print("\nGracias por usar el Asesor Virtual del Banco Caja Social.")
        print("   Recuerde que tambien puede contactarnos al #233. Hasta pronto!")
        return False, voz_activa, mic_activo

    if cmd == "/nueva":
        print("\nConversacion reiniciada.\n")
        return True, voz_activa, mic_activo

    if cmd == "/voz on":
        print("[VOZ] Respuestas por voz ACTIVADAS.")
        return True, True, mic_activo

    if cmd == "/voz off":
        print("[VOZ] Respuestas por voz DESACTIVADAS.")
        return True, False, mic_activo

    if cmd == "/mic on":
        print("[MIC] Entrada por microfono ACTIVADA.")
        return True, voz_activa, True

    if cmd == "/mic off":
        print("[MIC] Entrada por microfono DESACTIVADA.")
        return True, voz_activa, False

    if cmd == "/ayuda":
        print(BANNER)
        return True, voz_activa, mic_activo

    return True, voz_activa, mic_activo


def main():
    parser = argparse.ArgumentParser(
        description="Asesor Virtual del Banco Caja Social"
    )
    parser.add_argument(
        "--voz",
        action="store_true",
        help="Activar respuestas por voz (text-to-speech)",
    )
    parser.add_argument(
        "--microfono",
        action="store_true",
        help="Activar entrada por micrófono (speech-to-text)",
    )
    parser.add_argument(
        "--modelo",
        default="gemini-2.5-flash",
        help="Modelo de Gemini a usar (default: gemini-2.5-flash)",
    )
    args = parser.parse_args()

    print(BANNER)

    # Configure API
    api_key = obtener_api_key()

    print("Inicializando asesor virtual...")
    asesor = AsesorBancoCajaSocial(api_key=api_key, model_name=args.modelo)
    print("Asesor listo. Puede empezar a hacer sus preguntas.\n")

    voz_activa = args.voz
    mic_activo = args.microfono
    archivos_audio = []

    if voz_activa:
        print("[VOZ] Modo voz activado - Las respuestas se reproduciran en audio.")
    if mic_activo:
        print("[MIC] Modo microfono activado - Puede hablar para hacer preguntas.")
    print()

    # Initial greeting
    saludo = asesor.responder("Hola, preséntate brevemente como asesor del banco.")
    console.print(Panel(Markdown(saludo), title="Asesor", border_style="green", padding=(1, 2)))
    console.print()
    if voz_activa:
        ruta = texto_a_voz(saludo, reproducir=True)
        archivos_audio.append(ruta)

    # Main loop
    while True:
        try:
            # Get user input
            if mic_activo:
                print("─" * 50)
                mensaje = escuchar_microfono()
                if mensaje is None:
                    continuar = input("   (Escriba su mensaje o presione Enter para intentar de nuevo): ").strip()
                    if continuar:
                        mensaje = continuar
                    else:
                        continue
                print(f"Usted dijo: {mensaje}")
            else:
                mensaje = input("Usted: ").strip()

            if not mensaje:
                continue

            # Check if it's a command
            if mensaje.startswith("/"):
                continuar, voz_activa, mic_activo = procesar_comando(
                    mensaje, voz_activa, mic_activo
                )
                if not continuar:
                    break
                if mensaje.lower().strip() == "/nueva":
                    asesor.reiniciar_conversacion()
                continue

            # Get advisor response
            console.print("Pensando...", style="dim")
            respuesta = asesor.responder(mensaje)
            console.print()
            console.print(Panel(Markdown(respuesta), title="Asesor", border_style="green", padding=(1, 2)))
            console.print()

            # Play voice if active
            if voz_activa:
                ruta = texto_a_voz(respuesta, reproducir=True)
                archivos_audio.append(ruta)

        except KeyboardInterrupt:
            print("\n\nHasta luego. Recuerde que su Banco Amigo siempre esta para usted.")
            break
        except EOFError:
            break

    # Clean up temp files
    limpiar_archivos_temporales(archivos_audio)


if __name__ == "__main__":
    main()
