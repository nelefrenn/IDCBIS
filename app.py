from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import os
import logging

# Configurar logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar la API Key de Humata AI y el conversationId desde las variables de entorno
HUMATA_API_KEY = os.getenv("HUMATA_API_KEY")  # Usa el nombre correcto de la variable de entorno
CONVERSATION_ID = os.getenv("HUMATA_CONVERSATION_ID")  # Ahora usa conversationId en vez de document_id
HUMATA_ENDPOINT = "https://app.humata.ai/api/v1/ask"  # Nuevo endpoint basado en la documentación

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

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    if not HUMATA_API_KEY:
        logger.error("API Key no configurada. Verifica las variables de entorno en Render.")
        raise HTTPException(status_code=500, detail="API Key no configurada. Verifica las variables de entorno en Render.")
    
    if not CONVERSATION_ID or CONVERSATION_ID.strip() == "":
        logger.error(f"CONVERSATION_ID no configurado o vacío. Valor actual: {CONVERSATION_ID}")
        raise HTTPException(status_code=500, detail=f"CONVERSATION_ID no configurado o vacío. Verifica las variables de entorno en Render.")
    
    try:
        logger.info(f"Usando CONVERSATION_ID: {CONVERSATION_ID}")  # Log para verificar si CONVERSATION_ID está vacío
        headers = {
            "Authorization": f"Bearer {HUMATA_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "conversationId": CONVERSATION_ID,
            "model": "gpt-4-turbo-preview",  # Modelo que usa Humata AI
            "question": request.message,  # Cambié "query" por "question"
        }
        
        logger.info(f"Enviando solicitud a Humata AI con payload: {payload}")
        response = requests.post(HUMATA_ENDPOINT, json=payload, headers=headers)
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
