from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import os
import logging

# Configurar logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar la API Key de Humata AI y el document_id desde las variables de entorno
HUMATA_API_KEY = os.getenv("HUMATA_API_KEY")  # Usa el nombre correcto de la variable de entorno
DOCUMENT_ID = os.getenv("HUMATA_DOCUMENT_ID")  # Ahora el document_id se configura en Render
HUMATA_ENDPOINT = "https://app.humata.ai/api/v1/conversations"  # Reemplaza con el endpoint correcto si cambia

app = FastAPI()

# Habilitar CORS para permitir solicitudes desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # También puedes restringirlo a tu dominio específico
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permitir todos los encabezados
)

# Ruta raíz para comprobar que el backend funciona
@app.get("/", methods=["GET", "HEAD"])
def home():
    return {"message": "Bienvenido al backend del Asistente Virtual IDCBIS"}

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    if not HUMATA_API_KEY:
        logger.error("API Key no configurada. Verifica las variables de entorno en Render.")
        raise HTTPException(status_code=500, detail="API Key no configurada. Verifica las variables de entorno en Render.")
    
    if not DOCUMENT_ID:
        logger.error("DOCUMENT_ID no configurado. Verifica las variables de entorno en Render.")
        raise HTTPException(status_code=500, detail="DOCUMENT_ID no configurado. Verifica las variables de entorno en Render.")
    
    try:
        headers = {
            "Authorization": f"Bearer {HUMATA_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "query": request.message,
            "document_id": DOCUMENT_ID,  # Usamos el DOCUMENT_ID configurado en Render
        }
        
        logger.info(f"Enviando solicitud a Humata AI: {payload}")
        response = requests.post(HUMATA_ENDPOINT, json=payload, headers=headers)
        response_data = response.json()
        
        logger.info(f"Respuesta de Humata AI: {response_data}")

        if response.status_code == 200:
            return {"reply": response_data.get("answer", "No encontré una respuesta en los documentos.")}
        else:
            logger.error(f"Error en la API de Humata AI: {response_data}")
            raise HTTPException(status_code=response.status_code, detail=response_data)

    except requests.exceptions.RequestException as e:
        logger.error(f"Error en la solicitud a Humata AI: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en la solicitud a Humata AI: {str(e)}")
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

