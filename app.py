from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import os

# Cargar la API Key de Humata AI desde las variables de entorno
HUMATA_API_KEY = os.getenv("8bec1799eaacf6519239f45d5b137eba444f2a5a9adb069c37952a2e1229")
HUMATA_ENDPOINT = "https://app.humata.ai/api/v1/conversations"  # Reemplaza con el endpoint correcto si cambia

app = FastAPI()

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        headers = {
            "Authorization": f"Bearer {HUMATA_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "query": request.message,
            "document_id": "08d2e631-74ed-45e9-ac51-2dfce94b3b01",  # Reemplaza con el ID del documento en Humata AI
        }
        
        response = requests.post(HUMATA_ENDPOINT, json=payload, headers=headers)
        response_data = response.json()

        if response.status_code == 200:
            return {"reply": response_data.get("answer", "No encontré una respuesta en los documentos.")}
        else:
            raise HTTPException(status_code=response.status_code, detail=response_data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
