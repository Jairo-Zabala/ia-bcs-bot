#!/usr/bin/env python3
"""
Script de build para generar el ejecutable del Asesor Virtual.

Uso:
    pip install -r requirements.txt
    python build.py

El ejecutable se generará en: dist/BancoCajaSocialBot
"""

import PyInstaller.__main__
import os
import platform

sep = ':' if platform.system() != 'Windows' else ';'

PyInstaller.__main__.run([
    'web_server.py',
    '--name=BancoCajaSocialBot',
    '--onefile',
    f'--add-data=web{sep}web',
    f'--add-data=app{sep}app',
    f'--add-data=.env{sep}.',
    '--hidden-import=flask',
    '--hidden-import=flask_cors',
    '--hidden-import=gtts',
    '--hidden-import=google.genai',
    '--hidden-import=google.genai.types',
    '--hidden-import=app.bot',
    '--hidden-import=app.knowledge_base',
    '--hidden-import=app.voice',
    '--console',
    '--noconfirm',
])

print()
print("=" * 60)
print("✅ Build completado!")
print(f"   Ejecutable en: dist/BancoCajaSocialBot")
print()
print("   Para ejecutar:")
print("   ./dist/BancoCajaSocialBot")
print()
print("   ⚠️  Asegúrese de que el archivo .env con GEMINI_API_KEY")
print("   esté junto al ejecutable, o que la variable esté")
print("   definida en el entorno.")
print("=" * 60)
