from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import os
import logging
import time
time.sleep(0.5)  # Esperar medio segundo antes de enviar la respuesta completa


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

    # 🔍 Imprimir la respuesta completa para depuración
    logger.info(f"Respuesta cruda de Humata AI: {response.status_code} - {response.text}")

    if response.status_code == 200:
        try:
            conversation_data = response.json()
            logger.info(f"Respuesta completa de Humata AI: {conversation_data}")  # 🔍 Ver la estructura exacta

            # 🔥 FIX: Asignar correctamente el ID
           conversation_id = conversation_data.get("id", None)  # Accede directamente al ID


            if not conversation_id:
                logger.error("❌ Humata AI no devolvió un conversationId válido. Respuesta completa:")
                logger.error(conversation_data)

            logger.info(f"✅ Conversación creada con ID: {conversation_id}")
            return conversation_id
        except Exception as e:
            logger.error(f"❌ Error al procesar JSON de Humata AI: {str(e)} - Respuesta: {response.text}")
            return None
    else:
        logger.error(f"❌ Error al crear conversación: Código {response.status_code} - {response.text}")
        return None


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    if not HUMATA_API_KEY:
        logger.error("API Key no configurada. Verifica las variables de entorno en Render.")
        raise HTTPException(status_code=500, detail="API Key no configurada. Verifica las variables de entorno en Render.")
    
    if not DOCUMENT_ID:
        logger.error("DOCUMENT_ID no configurado. Verifica las variables de entorno en Render.")
        raise HTTPException(status_code=500, detail="DOCUMENT_ID no configurado. Verifica las variables de entorno en Render.")
    
    # Crear una conversación antes de hacer preguntas
    conversation_id = create_conversation()
    if not conversation_id:
        raise HTTPException(status_code=500, detail="No se pudo crear la conversación con Humata AI. Verifica el DOCUMENT_ID y los logs.")

    try:
        headers = {
            "Authorization": f"Bearer {HUMATA_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
    "id": conversation_id,  # Usar "id" en lugar de "conversationId"
    "model": "gpt-4-turbo-preview",
    "question": request.message,
}
        
        logger.info(f"Preguntando a Humata AI con payload: {payload}")
        response = requests.post(ASK_ENDPOINT, json=payload, headers=headers)
        response_data = response.json()
        
        logger.info(f"Código de respuesta de Humata AI: {response.status_code}")
        logger.info(f"Respuesta completa de Humata AI: {response_data}")

        if response.status_code == 200:
            return {"reply": response_data.get("answer", "No encontré una respuesta en los documentos.")}
        else:
            logger.error(f"Error en la API de Humata AI: Código {response.status_code}, Respuesta {response.text}")
            raise HTTPException(status_code=response.status_code, detail=f"Error de Humata AI: {response_data}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Error en la solicitud a Humata AI: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en la solicitud a Humata AI: {str(e)}")
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")

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

    # 🔍 Imprimir respuesta completa de Humata para depuración
    logger.info(f"Respuesta cruda de Humata AI: {response.status_code} - {response.text}")

    if response.status_code == 200:
        try:
            conversation_data = response.json()
            conversation_id = conversation_data.get("conversationId")
            
            if not conversation_id:
                logger.error("❌ Humata AI no devolvió un conversationId válido. Respuesta completa:")
                logger.error(conversation_data)  # 🔍 Ver la estructura de la respuesta

            logger.info(f"✅ Conversación creada con ID: {conversation_id}")
            return conversation_id
        except Exception as e:
            logger.error(f"❌ Error al procesar JSON de Humata AI: {str(e)} - Respuesta: {response.text}")
            return None
    else:
        logger.error(f"❌ Error al crear conversación: Código {response.status_code} - {response.text}")
        return None

