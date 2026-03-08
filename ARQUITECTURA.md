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
📊 [Ver diagrama interactivo en FigJam](https://www.figma.com/online-whiteboard/create-diagram/1bb34c84-71f6-401a-8520-a40c0bacb3a2?utm_source=other&utm_content=edit_in_figjam)

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

*Documento generado: Marzo 2026*
