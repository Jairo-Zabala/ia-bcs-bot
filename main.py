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


def obtener_config_azure() -> dict:
    """Get Azure configuration from environment variables."""
    load_dotenv()

    config = {
        "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
        "api_key": os.getenv("AZURE_OPENAI_KEY"),
        "deployment_name": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini"),
        "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        "speech_key": os.getenv("AZURE_SPEECH_KEY"),
        "speech_region": os.getenv("AZURE_SPEECH_REGION", "eastus2"),
    }

    if not config["endpoint"] or not config["api_key"]:
        print("\n[ERROR] Variables de Azure no configuradas.")
        print("   Configure las siguientes variables en el archivo .env:")
        print("   - AZURE_OPENAI_ENDPOINT")
        print("   - AZURE_OPENAI_KEY")
        print("   - AZURE_SPEECH_KEY")
        print("   - AZURE_SPEECH_REGION")
        sys.exit(1)

    return config


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
    args = parser.parse_args()

    print(BANNER)

    # Configure Azure
    config = obtener_config_azure()

    print("Inicializando asesor virtual (Azure OpenAI)...")
    asesor = AsesorBancoCajaSocial(
        endpoint=config["endpoint"],
        api_key=config["api_key"],
        deployment_name=config["deployment_name"],
        api_version=config["api_version"],
    )
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
        ruta = texto_a_voz(saludo, config["speech_key"], config["speech_region"], reproducir=True)
        archivos_audio.append(ruta)

    # Main loop
    while True:
        try:
            # Get user input
            if mic_activo:
                print("─" * 50)
                mensaje = escuchar_microfono(config["speech_key"], config["speech_region"])
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
                ruta = texto_a_voz(respuesta, config["speech_key"], config["speech_region"], reproducir=True)
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
