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
HUMATA_API_KEY = os.getenv("HUMATA_API_KEY")  
DOCUMENT_ID = os.getenv("HUMATA_DOCUMENT_ID")  

# Endpoints de Humata AI
CREATE_CONVERSATION_ENDPOINT = "https://app.humata.ai/api/v1/conversations"  
ASK_ENDPOINT = "https://app.humata.ai/api/v1/ask"  

# Variable global para almacenar conversationId
CONVERSATION_ID = None  

app = FastAPI()

# Habilitar CORS para permitir solicitudes desde el frontend específico
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://nelefrenn.github.io"],  
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  
    allow_headers=["Content-Type", "Authorization"],  
)

@app.get("/")
@app.head("/")
def home():
    return {"message": "Bienvenido al backend del Asistente Virtual IDCBIS"}

class ChatRequest(BaseModel):
    message: str

# Función para crear una nueva conversación con el documento
def create_conversation():
    global CONVERSATION_ID  

    if CONVERSATION_ID:
        logger.info(f"Usando conversación existente: {CONVERSATION_ID}")
        return CONVERSATION_ID

    headers = {
        "Authorization": f"Bearer {HUMATA_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "documentIds": [DOCUMENT_ID]  
    }
    
    logger.info(f"Creando nueva conversación con Humata AI usando DOCUMENT_ID: {DOCUMENT_ID}")
    response = requests.post(CREATE_CONVERSATION_ENDPOINT, json=payload, headers=headers)

    try:
        response_data = response.json()
        logger.info(f"Respuesta de Humata AI al crear conversación: {response.status_code} - {response_data}")
    except Exception as e:
        logger.error(f"No se pudo parsear la respuesta de Humata AI: {str(e)} - Respuesta: {response.text}")
        return None

    if response.status_code == 200:
        conversation_id = response_data.get("id")  

        if not conversation_id:
            logger.error(f"Humata AI no devolvió un conversationId válido. Respuesta: {response_data}")
            return None

        logger.info(f"Conversación creada con ID: {conversation_id}")
        CONVERSATION_ID = conversation_id  
        return conversation_id
    else:
        logger.error(f"Error al crear conversación: {response.status_code} - {response_data}")
        return None

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    global CONVERSATION_ID  

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
            "conversationId": conversation_id,  
            "model": "gpt-4-turbo-preview",
            "question": request.message,
        }
        
        logger.info(f"Preguntando a Humata AI con payload: {payload}")
        response = requests.post(ASK_ENDPOINT, json=payload, headers=headers, stream=True)

        if response.status_code != 200:
            logger.error(f"Error en la API de Humata AI: {response.status_code} - {response.text}")
            raise HTTPException(status_code=response.status_code, detail=f"Error de Humata AI: {response.text}")

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

        if not final_answer:
            final_answer = "No encontré una respuesta en los documentos."

        return {"reply": final_answer}

    except requests.exceptions.RequestException as e:
        logger.error(f"Error en la solicitud a Humata AI: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en la solicitud a Humata AI: {str(e)}")
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")
