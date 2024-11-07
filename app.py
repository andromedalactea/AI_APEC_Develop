# Import Standard Libraries
import os
import logging
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from dotenv import load_dotenv

# Local imports
from scripts.extract_available_openai_models import extract_openai_models
from scripts.generate_responses import (
    generate_chat_response,
    generate_chat_responses_stream,
    generate_chat_responses_o1_model
)

# Load environment variables from the .env file
load_dotenv(override=True)

# Configuración del logger
log_file = "app.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),  # Logs a archivo
        logging.StreamHandler()         # Logs a consola
    ]
)
logger = logging.getLogger(__name__)

# Crear instancia de FastAPI
app = FastAPI()

# Permitir peticiones CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ajusta según la política de tu organización
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Middleware para manejar errores no capturados
@app.middleware("http")
async def global_error_handler(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Uncaught global error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": {"message": "Internal server error"}}
        )


# Ruta para obtener modelos disponibles
@app.get("/v1/models")
async def get_models():
    # Inicial template para la respuesta
    response_data = {
        "data": [],
        "object": "list"
    }

    try:
        # Extraer los modelos disponibles (aquí simulado con una lista)
        # available_models = extract_openai_models()  # Uncomment this in prod
        available_models = ['chatgpt-4o& APEC', 'gpt-4o-mini& APE', 'o1-preview& APEC']
        
        if available_models:
            for model in available_models:
                response_data["data"].append({
                    "id": model,
                    "object": "model",
                    "owned_by": "organization-owner",
                    "permission": [{}]
                })
        else:
            response_data = {
                "error": {
                    "message": "No models available"
                }
            }

        return JSONResponse(content=response_data)

    except Exception as e:
        logger.error(f"Error fetching models: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": {"message": "Internal server error"}}
        )


# Ruta para generar completions de chat
@app.post("/v1/chat/completions")
async def get_chat_completions(request: Request):
    try:
        data = await request.json()
        logger.info('Received POST request to /v1/chat/completions')
        logger.info(f'Received data: {data}')

        if data.get('stream') is True:
            # Generar respuestas de chat en streaming
            logger.info("Generating chat responses in streaming...")

            try:
                if data.get('model') == 'o1-preview& APEC':
                    event_stream = generate_chat_responses_o1_model(data)
                    return StreamingResponse(event_stream, media_type="text/event-stream")
                else:
                    event_stream = generate_chat_responses_stream(data)
                    return StreamingResponse(event_stream, media_type="text/event-stream")
            except Exception as e:
                logger.error(f"Error generating streaming responses: {e}")
                return JSONResponse(
                    content={"error": "Error generating streaming responses"},
                    status_code=500
                )
        else:
            # Retornar la respuesta completa de una vez
            return await generate_chat_response(data)

    except Exception as e:
        logger.error(f"Error processing chat completions: {e}")
        return JSONResponse(
            content={"error": {"message": "Internal server error"}},
            status_code=500
        )


# Arrancar la aplicación
if __name__ == "__main__":
    import uvicorn
    # Opcional, para el uso de ngrok o enlaces públicos
    from pyngrok import ngrok
    domain = "sex.ngrok.app" 
    ngrok_tunnel = ngrok.connect(8000, domain=domain)
    print('NGROK Tunnel URL:', ngrok_tunnel.public_url)

    uvicorn.run(app, host="0.0.0.0", port=8000)