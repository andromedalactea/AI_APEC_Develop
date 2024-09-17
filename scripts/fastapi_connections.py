from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
import logging
import json
import asyncio

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
    logger.info('Received GET request to /v1/models with body: {}')
    logger.info(f'Returning {response_data}')
    return JSONResponse(content=response_data)

async def generate_chat_responses_stream(data):
    try:
        for i in range(1, 6):
            message_content = f"Chat completion part {i}"
            # Formato alineado con la API de OpenAI para respuestas en streaming
            message = {
                "id": f"chatcmpl-stream-{i}",
                "object": "chat.completion.chunk",
                "created": int(asyncio.get_event_loop().time()),
                "model": data.get("model", "APEC_model"),
                "choices": [{
                    "delta": {
                        "content": message_content
                    },
                    "index": 0,
                    "finish_reason": None
                }]
            }
            event = f"data: {json.dumps(message)}\n\n"
            yield event
            await asyncio.sleep(1)  # Simula tiempo de procesamiento

        # Enviar el mensaje de finalización del streaming
        end_message = {
            "id": "chatcmpl-stream-end",
            "object": "chat.completion.chunk",
            "created": int(asyncio.get_event_loop().time()),
            "model": data.get("model", "APEC_model"),
            "choices": [{
                "delta": {},
                "index": 0,
                "finish_reason": "stop"
            }]
        }
        yield f"data: {json.dumps(end_message)}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.error(f"Error in generating chat responses: {e}")
        error_message = {
            "error": {
                "message": "Internal server error"
            }
        }
        yield f"data: {json.dumps(error_message)}\n\n"

async def generate_chat_response(data):
    try:
        # Generar la respuesta completa de una vez
        full_content = ' '.join([f"Chat completion part {i}" for i in range(1,6)])
        message = {
            "id": "chatcmpl-nostream",
            "object": "chat.completion",
            "created": int(asyncio.get_event_loop().time()),
            "model": data.get("model", "APEC_model"),
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": full_content
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }
        return JSONResponse(content=message)
    except Exception as e:
        logger.error(f"Error in generating chat responses: {e}")
        return JSONResponse(content={"error": {"message": "Internal server error"}}, status_code=500)

@app.post("/v1/chat/completions")
async def get_chat_completions(request: Request):
    try:
        data = await request.json()
        logger.info('Received POST request to /v1/chat/completions')
        logger.info(f'Received data: {data}')

        if data.get('stream') is True:
            # Generar las respuestas de chat en forma de streaming
            event_stream = generate_chat_responses_stream(data)
            return StreamingResponse(event_stream, media_type="text/event-stream")
        else:
            # Return the full response at once
            return await generate_chat_response(data)
    except Exception as e:
        logger.error(f"Error processing chat completions: {e}")
        return JSONResponse(content={"error": {"message": "Internal server error"}}, status_code=500)
