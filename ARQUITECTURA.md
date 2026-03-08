# Asesor Virtual Banco Caja Social
## Documento de Arquitectura y Proyección de Costos

---

## 📋 Resumen Ejecutivo

El **Asesor Virtual del Banco Caja Social** es un chatbot conversacional con capacidades de voz que utiliza inteligencia artificial para atender consultas de clientes sobre productos y servicios bancarios. La solución está diseñada para desplegarse en pantallas de autoservicio en oficinas del banco.

### Características Principales
- 💬 Chat conversacional con IA (Azure OpenAI GPT-4o-mini)
- 🎙️ Entrada de voz (Speech-to-Text)
- 🔊 Respuestas por voz natural (Text-to-Speech con Andrew DragonHD)
- 🏦 Base de conocimiento especializada del Banco Caja Social
- 🌐 Interfaz web responsive
- 🔒 Conexión segura HTTPS

---

## 🏗️ Arquitectura del Sistema

### Diagrama de Arquitectura
📊 [Ver diagrama interactivo en FigJam](https://www.figma.com/online-whiteboard/create-diagram/a2742978-93fc-4335-8780-848fe84188f8?utm_source=other&utm_content=edit_in_figjam)

### Flujo de Datos (numerado)
1. **Micrófono** → WebM Audio → Flask
2. **Interfaz Web** → HTTPS → Cloudflare Tunnel
3. **Tunnel** → HTTP:5000 → Flask + Gunicorn
4. **Flask** → WebM → pydub + FFmpeg (conversión)
5. **pydub** → WAV → Azure STT
6. **STT** → Texto transcrito → Flask
7. **Flask** → Mensaje usuario → Bot Engine
8. **Bot Engine** → Chat API → Azure OpenAI
9. **OpenAI** → Respuesta IA → Bot Engine
10. **Bot Engine** → Texto respuesta → Flask
11. **Flask** → Texto → Azure TTS
12. **TTS** → Audio MP3 48kHz → Flask
13. **Flask** → Audio Stream → Altavoz

### Componentes

#### 1. Frontend (Cliente)
- **Tecnología**: HTML5, CSS3, JavaScript vanilla
- **Funcionalidades**:
  - Interfaz de chat responsiva
  - Grabación de audio via Web Audio API
  - Reproducción de respuestas de voz
  - Selector de voces y velocidad

#### 2. Backend (Servidor)
- **Framework**: Flask + Gunicorn (Python 3.12)
- **Infraestructura**: Azure VM Ubuntu 24.04 LTS
- **Especificaciones actuales**: Standard_B1s (1 vCPU, 1GB RAM)
- **Endpoints**:
  - `POST /chat` - Procesar mensajes de texto
  - `POST /voz` - Generar audio TTS
  - `POST /transcribe` - Convertir audio a texto
  - `GET /` - Servir interfaz web

#### 3. Servicios de Azure

| Servicio | Uso | Modelo/Configuración |
|----------|-----|---------------------|
| Azure OpenAI | Generación de respuestas | GPT-4o-mini |
| Azure Speech | Text-to-Speech | Andrew DragonHD (48kHz/192kbps) |
| Azure Speech | Speech-to-Text | es-CO (Español Colombia) |
| Azure VM | Hosting aplicación | Standard_B1s |

#### 4. Red y Seguridad
- **Cloudflare Tunnel**: HTTPS sin configurar certificados
- **NSG**: Solo puerto 5000 abierto internamente
- **Systemd**: Servicios con auto-restart

---

## 💰 Proyección de Costos para 5,000 Oficinas

### Supuestos de Uso
- **Horario**: 8 horas/día, 22 días/mes
- **Interacciones por oficina**: 50 conversaciones/día promedio
- **Mensajes por conversación**: 5 mensajes promedio
- **Uso de voz**: 70% de las interacciones

### Cálculo de Volumen Mensual

| Métrica | Cálculo | Total Mensual |
|---------|---------|---------------|
| Conversaciones | 5,000 × 50 × 22 | 5,500,000 |
| Mensajes (tokens entrada) | 5.5M × 5 × ~100 tokens | 2,750M tokens |
| Mensajes (tokens salida) | 5.5M × 5 × ~150 tokens | 4,125M tokens |
| Caracteres TTS | 5.5M × 5 × 0.7 × 400 chars | 7,700M caracteres |
| Minutos STT | 5.5M × 5 × 0.7 × 0.5 min | 9,625,000 minutos |

### Costos Azure por Servicio (Precios marzo 2026)

#### Azure OpenAI (GPT-4o-mini)
| Tipo | Volumen | Precio/1M tokens | Costo Mensual |
|------|---------|------------------|---------------|
| Input | 2,750M | $0.15 | $412.50 |
| Output | 4,125M | $0.60 | $2,475.00 |
| **Subtotal OpenAI** | | | **$2,887.50** |

#### Azure Speech Services
| Servicio | Volumen | Precio | Costo Mensual |
|----------|---------|--------|---------------|
| TTS Neural HD | 7,700M chars | $16/1M chars | $123,200 |
| STT Standard | 9.6M min | $1/60 min | $160,416 |
| **Subtotal Speech** | | | **$283,616** |

#### Infraestructura
| Recurso | Configuración | Costo Mensual |
|---------|---------------|---------------|
| VMs Backend | 10× Standard_D4s_v3 (Load balanced) | $1,401.60 |
| Load Balancer | Standard | $25.55 |
| Storage | 100GB SSD | $19.20 |
| Bandwidth | 500GB egress | $43.45 |
| **Subtotal Infra** | | **$1,489.80** |

### Resumen de Costos Mensuales

| Categoría | Costo USD |
|-----------|-----------|
| Azure OpenAI | $2,887.50 |
| Azure Speech | $283,616.00 |
| Infraestructura | $1,489.80 |
| **TOTAL MENSUAL** | **$287,993.30** |
| **Costo por oficina/mes** | **$57.60** |

---

## 💡 Recomendaciones para Optimización

### 1. Reducir Costos de Speech (Mayor Impacto)

#### Opción A: Voces Neural Estándar en lugar de HD
- Usar `es-CO-SalomeNeural` en lugar de DragonHD
- **Ahorro**: ~60% en TTS ($73,920/mes en lugar de $123,200)
- **Trade-off**: Voz menos natural pero aún de buena calidad

#### Opción B: Caching de Respuestas Frecuentes
- Pre-generar audio para respuestas comunes (saludo, despedida, info básica)
- Implementar cache Redis para respuestas repetidas
- **Ahorro estimado**: 30-40% en tokens y TTS

#### Opción C: Modo Híbrido Texto/Voz
- Ofrecer voz solo cuando el usuario lo solicite
- Por defecto mostrar respuestas en texto
- **Ahorro potencial**: 50-70% en Speech si solo 30% usa voz

### 2. Optimizar Azure OpenAI

#### Usar Batch API para Análisis
- Para tareas no interactivas (reportes, análisis)
- **Ahorro**: 50% en tokens procesados en batch

#### Implementar Respuestas Predefinidas
- FAQ con respuestas exactas (sin IA)
- Solo usar OpenAI para consultas complejas
- **Ahorro estimado**: 40% en tokens

### 3. Arquitectura Recomendada para Producción

```
                    ┌─────────────────┐
                    │   Azure Front   │
                    │     Door CDN    │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
        ┌─────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐
        │  Region 1 │  │  Region 2 │  │  Region 3 │
        │  (Bogotá) │  │  (Miami)  │  │ (São Paulo)│
        └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
              │              │              │
        ┌─────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐
        │    AKS    │  │    AKS    │  │    AKS    │
        │  Cluster  │  │  Cluster  │  │  Cluster  │
        └───────────┘  └───────────┘  └───────────┘
```

#### Componentes Sugeridos
- **Azure Front Door**: CDN + WAF + Load Balancing global
- **Azure Kubernetes Service (AKS)**: Escalabilidad automática
- **Azure Cache for Redis**: Caching de respuestas
- **Azure Cosmos DB**: Estado de conversaciones distribuido
- **Application Insights**: Monitoreo y alertas

### 4. Plan de Implementación por Fases

#### Fase 1: Piloto (1-3 meses)
- 50 oficinas en ciudades principales
- Validar adopción y ajustar UX
- **Costo estimado**: ~$3,000/mes

#### Fase 2: Expansión Regional (4-6 meses)
- 500 oficinas
- Implementar caching y optimizaciones
- **Costo estimado**: ~$20,000/mes (con optimizaciones)

#### Fase 3: Despliegue Nacional (7-12 meses)
- 5,000 oficinas
- Arquitectura multi-región
- **Costo estimado**: ~$150,000-200,000/mes (con todas las optimizaciones)

---

## 🔐 Consideraciones de Seguridad

1. **Datos Sensibles**: No almacenar información bancaria en logs
2. **Autenticación**: Implementar Azure AD para administradores
3. **Cifrado**: TLS 1.3 en tránsito, AES-256 en reposo
4. **Cumplimiento**: Revisar normativa SFC Colombia
5. **Auditoría**: Logs de todas las interacciones (sin datos PII)

---

## 📊 KPIs Recomendados

| Métrica | Objetivo |
|---------|----------|
| Tiempo de respuesta | < 3 segundos |
| Tasa de resolución | > 70% |
| Satisfacción usuario | > 4.0/5.0 |
| Disponibilidad | 99.9% |
| Escalamiento a humano | < 20% |

---

## 📁 Estructura del Proyecto

```
bcs-bot/
├── app/
│   ├── __init__.py
│   ├── bot.py              # Lógica del chatbot + Azure OpenAI
│   ├── voice.py            # TTS/STT con Azure Speech
│   └── knowledge_base.py   # Base de conocimiento BCS
├── web/
│   ├── static/
│   │   ├── css/styles.css
│   │   ├── js/app.js
│   │   └── img/bcs-ico.png
│   └── templates/
│       └── index.html
├── web_server.py           # Flask server
├── main.py                 # CLI interface
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Comandos de Despliegue

### Encender VM y obtener URL
```powershell
# Iniciar VM
az vm start --resource-group MyLowCostVM_group --name MyLowCostVM

# Obtener IP pública
az vm show -d --resource-group MyLowCostVM_group --name MyLowCostVM --query publicIps -o tsv

# Obtener URL del túnel (esperar ~1 min después de encender)
ssh -i MyLowCostVM_key.pem azureuser@<IP> "grep trycloudflare /var/log/cloudflared.log | tail -1"
```

### Apagar VM (ahorro de costos)
```powershell
az vm deallocate --resource-group MyLowCostVM_group --name MyLowCostVM
```

---

## 📞 Contacto

**Repositorio**: https://github.com/Jairo-Zabala/ia-bcs-bot

---

## 📖 Glosario de Conceptos

| Término | Descripción |
|---------|-------------|
| **Azure OpenAI** | Servicio de Microsoft que permite usar modelos de OpenAI (como GPT-4) en la nube de Azure con seguridad empresarial. |
| **GPT-4o-mini** | Modelo de lenguaje de OpenAI optimizado para velocidad y costo, ideal para chatbots. Entiende contexto y genera respuestas naturales. |
| **TTS (Text-to-Speech)** | Tecnología que convierte texto escrito en audio hablado. Azure ofrece voces neurales que suenan muy naturales. |
| **STT (Speech-to-Text)** | Tecnología que convierte audio hablado en texto escrito. Permite que los usuarios hablen en lugar de escribir. |
| **Andrew DragonHD** | Voz neural de Azure basada en LLMs que detecta automáticamente el tono emocional del texto y ajusta la entonación. |
| **SSML** | Speech Synthesis Markup Language. Lenguaje XML para controlar cómo se pronuncia el texto (velocidad, tono, pausas). |
| **Flask** | Framework web de Python, ligero y flexible, usado para crear APIs y servir la interfaz web. |
| **Gunicorn** | Servidor HTTP para Python que permite manejar múltiples solicitudes simultáneas en producción. |
| **Cloudflare Tunnel** | Servicio que crea un túnel seguro HTTPS hacia tu servidor sin necesidad de abrir puertos o configurar certificados SSL. |
| **WebM** | Formato de audio/video usado por navegadores. El micrófono del navegador graba en este formato. |
| **WAV** | Formato de audio sin compresión requerido por Azure Speech para transcripción. |
| **pydub** | Librería Python para manipular audio. Usada para convertir WebM a WAV. |
| **FFmpeg** | Herramienta de línea de comandos para procesar audio/video. pydub lo usa internamente. |
| **Systemd** | Sistema de Linux para gestionar servicios. Permite que la app se inicie automáticamente al encender la VM. |
| **VM (Virtual Machine)** | Computadora virtual en la nube. Ejecuta el servidor Python 24/7. |
| **API** | Application Programming Interface. Forma estándar de comunicación entre sistemas (ej: `/chat`, `/voz`). |
| **Endpoint** | URL específica de una API que realiza una función (ej: `POST /transcribe` convierte audio a texto). |
| **Token** | Unidad de texto que procesan los modelos de IA. ~4 caracteres en español. Se cobra por tokens procesados. |
| **Latencia** | Tiempo que tarda el sistema en responder. Menor latencia = mejor experiencia de usuario. |
| **Cache** | Almacenamiento temporal de respuestas frecuentes para evitar reprocesar y ahorrar costos. |
| **AKS** | Azure Kubernetes Service. Plataforma para desplegar aplicaciones escalables en contenedores. |
| **CDN** | Content Delivery Network. Red de servidores que acelera la entrega de contenido estático. |
| **WAF** | Web Application Firewall. Protege contra ataques web comunes (SQL injection, XSS, etc). |
| **SFC** | Superintendencia Financiera de Colombia. Entidad que regula el sector financiero. |

---

*Documento generado: Marzo 2026*
