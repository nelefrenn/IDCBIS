from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import os
import logging
import json

# Configurar logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar la API Key de Humata AI y el document_id desde las variables de entorno
HUMATA_API_KEY = os.getenv("HUMATA_API_KEY")  # API Key
DOCUMENT_ID = os.getenv("HUMATA_DOCUMENT_ID")  # Documento al que se hará preguntas
CREATE_CONVERSATION_ENDPOINT = "https://app.humata.ai/api/v1/conversations"  # Endpoint para crear conversación
ASK_ENDPOINT = "https://app.humata.ai/api/v1/ask"  # Endpoint para preguntar en la conversación

app = FastAPI()

# Habilitar CORS para permitir solicitudes desde el frontend específico
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://nelefrenn.github.io"],  # Permitir solo el frontend
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # Métodos permitidos
    allow_headers=["Content-Type", "Authorization"],  # Permitir solo encabezados necesarios
)

# Ruta raíz para comprobar que el backend funciona
@app.get("/")
@app.head("/")
def home():
    return {"message": "Bienvenido al backend del Asistente Virtual IDCBIS"}

class ChatRequest(BaseModel):
    message: str

# Función para crear una nueva conversación con el documento
def create_conversation():
    headers = {
        "Authorization": f"Bearer {HUMATA_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "documentIds": [DOCUMENT_ID]  # Crear conversación con el documento
    }
    
    logger.info(f"Creando nueva conversación con Humata AI usando DOCUMENT_ID: {DOCUMENT_ID}")
    response = requests.post(CREATE_CONVERSATION_ENDPOINT, json=payload, headers=headers)
    
    logger.info(f"Respuesta completa de Humata AI al crear conversación: {response.status_code} - {response.text}")

    if response.status_code == 200:
        conversation_data = response.json()
        conversation_id = conversation_data.get("conversationId")
        if not conversation_id:
            logger.error("Humata AI no devolvió un conversationId válido.")
            return None
        logger.info(f"Conversación creada con ID: {conversation_id}")
        return conversation_id
    else:
        logger.error(f"Error al crear conversación: {response.status_code} - {response.text}")
        return None

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    if not HUMATA_API_KEY:
        logger.error("API Key no configurada. Verifica las variables de entorno en Render.")
        raise HTTPException(status_code=500, detail="API Key no configurada. Verifica las variables de entorno en Render.")
    
    if not DOCUMENT_ID:
        logger.error("DOCUMENT_ID no configurado. Verifica las variables de entorno en Render.")
        raise HTTPException(status_code=500, detail="DOCUMENT_ID no configurado. Verifica las variables de entorno en Render.")
    
    conversation_id = create_conversation()
    if not conversation_id:
        raise HTTPException(status_code=500, detail="No se pudo crear la conversación con Humata AI. Verifica el DOCUMENT_ID y los logs.")

    try:
        headers = {
            "Authorization": f"Bearer {HUMATA_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "conversationId": conversation_id,  # Usar la conversación recién creada
            "model": "gpt-4-turbo-preview",
            "question": request.message,
        }
        
        logger.info(f"Preguntando a Humata AI con payload: {payload}")
        response = requests.post(ASK_ENDPOINT, json=payload, headers=headers, stream=True)
        
        # Leer la respuesta en streaming y ensamblar el texto correctamente
        answer_parts = []
        buffer_word = ""  # Para acumular fragmentos parciales de palabras

        for line in response.iter_lines():
            if line:
                try:
                    line_data = line.decode("utf-8").replace("data: ", "").strip()
                    json_data = json.loads(line_data)  # Convertir string a JSON
                    content = json_data.get("content", "")

                    # Unir fragmentos cortados
                    if buffer_word:
                        content = buffer_word + content
                        buffer_word = ""

                    # Si el fragmento es muy corto (≤3 caracteres) y no inicia con espacio, lo acumulamos
                    if len(content) <= 3 and not content.startswith(" "):
                        buffer_word = content
                    else:
                        answer_parts.append(content)

                except Exception as e:
                    logger.error(f"Error al procesar chunk de Humata AI: {str(e)} - Datos: {line}")

        # Si quedó un fragmento en buffer_word, agregarlo al final
        if buffer_word:
            answer_parts.append(buffer_word)

        # Unir los fragmentos correctamente y limpiar el texto
        final_answer = " ".join(answer_parts)

        # Corregir espacios incorrectos en puntuación
        final_answer = (
            final_answer.replace(" ,", ",")
                        .replace(" .", ".")
                        .replace(" :", ":")
                        .replace(" ;", ";")
                        .replace("( ", "(")
                        .replace(" )", ")")
                        .strip()
        )
        
        logger.info(f"Respuesta en streaming procesada y limpia: {final_answer}")
        return {"reply": final_answer}

    except requests.exceptions.RequestException as e:
        logger.error(f"Error en la solicitud a Humata AI: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en la solicitud a Humata AI: {str(e)}")
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")

