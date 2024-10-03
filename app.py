# Import Standard Libraries
import os
import logging

# Local imports from the same directory
from scripts.extract_available_openai_models import extract_openai_models
from scripts.generate_responses import generate_chat_response, generate_chat_responses_stream

# Import Third-Party Libraries
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse


# Load environment variables from the .env file
load_dotenv(override=True)

# Configurar el logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Datos de ejemplo que la API devolverá
response_data = {
    "data": [
        {
            "id": "APEC_model",
            "object": "model",
            "owned_by": "organization-owner",
            "permission": [{}]
        }
    ],
    "object": "list"
}

@app.get("/v1/models")
async def get_models():

    # Initial template for the response
    response_data = {
        "data": [],
        "object": "list"
    }
    # Extract the available models for openai
    # available_models = extract_openai_models()
    available_models = ['chatgpt-4o-latest& APEC', 'gpt-4o-mini& APE', 'o1-preview& APEC']
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


@app.post("/v1/chat/completions")
async def get_chat_completions(request: Request):
    try:
        data = await request.json()
        logger.info('Received POST request to /v1/chat/completions')
        logger.info(f'Received data: {data}')

        if data.get('stream') is True:
            # Generar las respuestas de chat en forma de streaming
            logger.info("Generating chat responses in streaming...")
            event_stream = generate_chat_responses_stream(data)
            return StreamingResponse(event_stream, media_type="text/event-stream")
        else:
            # Return the full response at once
            return await generate_chat_response(data)
    except Exception as e:
        logger.error(f"Error processing chat completions: {e}")
        return JSONResponse(content={"error": {"message": "Internal server error"}}, status_code=500)


if __name__ == "__main__":
    import uvicorn
    # from pyngrok import ngrok
    # # Running in 8000 port
    # # Persinalized domain
    # domain = "sex.ngrok.app"  

    # # Configure ngrok with the port on which Flask is running
    # ngrok_tunnel = ngrok.connect(8000, domain=domain)
    # print('NGROK Tunnel URL:', ngrok_tunnel.public_url)
    uvicorn.run(app, host="0.0.0.0", port=8000)