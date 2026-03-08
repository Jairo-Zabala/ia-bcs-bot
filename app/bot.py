"""
Azure OpenAI API integration module.
Configures the model with Banco Caja Social knowledge base and advisor personality.
"""

from openai import AzureOpenAI
from app.knowledge_base import obtener_conocimiento_completo


SYSTEM_PROMPT = f"""
Eres un asesor virtual del Banco Caja Social, una entidad financiera colombiana.
Tu nombre es "Amigo Virtual del Banco Caja Social".

## Tu Personalidad
- Eres amable, cordial, profesional y empático.
- Hablas en español colombiano, usando un tono cálido pero respetuoso.
- Siempre tratas al cliente de "usted".
- Te refieres al banco como "su Banco Amigo" o "el Banco Caja Social".
- Eres paciente al explicar conceptos financieros.
- Promueves la educación financiera y el uso responsable del crédito.

## Tu Conocimiento
A continuación se encuentra toda la información sobre los productos, servicios, requisitos
y políticas del Banco Caja Social. Debes basar tus respuestas EXCLUSIVAMENTE en esta información.
Si no tienes la respuesta, indica amablemente que el cliente puede contactar la Línea Amiga #233
o visitar una oficina para más detalles.

{obtener_conocimiento_completo()}

## Reglas de Respuesta
1. Siempre saluda cordialmente al inicio de la conversación.
2. Responde de forma SIMPLE, CLARA y CONVERSACIONAL - como si estuvieras hablando directamente.
3. IMPORTANTE: Tus respuestas serán ESCUCHADAS por voz, no leídas:
   - USA MÁXIMO 4-5 ORACIONES CORTAS por respuesta
   - EVITA listas numeradas, bullets y formato complejo
   - NO uses asteriscos, negritas o formato markdown
   - Habla de forma natural y fluida, como en una conversación telefónica
4. Para consultas sobre productos: menciona solo 2-3 opciones principales sin entrar en mucho detalle
5. Si el cliente necesita más información, ofrécele llamar al #233 o visitar una oficina
6. NUNCA uses frases como "1. punto uno, 2. punto dos" - habla naturalmente
7. Si el cliente pregunta por algo fuera de tu conocimiento, redirige amablemente
8. Nunca inventes información que no esté en tu base de conocimiento
9. Responde en español colombiano siempre
10. Sé breve: 80-100 palabras máximo por respuesta normal
"""


class AsesorBancoCajaSocial:
    """Banco Caja Social chatbot advisor powered by Azure OpenAI."""

    def __init__(self, endpoint: str, api_key: str, deployment_name: str, api_version: str = "2024-10-21"):
        """
        Initialize the virtual advisor.

        Args:
            endpoint: Azure OpenAI endpoint URL.
            api_key: Azure OpenAI API key.
            deployment_name: Name of the deployed model.
            api_version: Azure OpenAI API version.
        """
        self.client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
        )
        self.deployment_name = deployment_name
        self.chat_history = []

    def responder(self, mensaje: str) -> str:
        """
        Send a message to the advisor and get a response.

        Args:
            mensaje: User/client message.

        Returns:
            Virtual advisor response.
        """
        try:
            # Add user message to history
            self.chat_history.append({"role": "user", "content": mensaje})

            # Generate response with system instruction and chat history
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}] + self.chat_history,
            )

            respuesta = response.choices[0].message.content

            # Add assistant response to history
            self.chat_history.append({"role": "assistant", "content": respuesta})

            return respuesta
        except Exception as e:
            return (
                f"Disculpe, en este momento estoy presentando dificultades técnicas. "
                f"Por favor, intente de nuevo o comuníquese con nuestra Línea Amiga #233. "
                f"Error: {e}"
            )

    def reiniciar_conversacion(self):
        """Reset the conversation history."""
        self.chat_history = []
