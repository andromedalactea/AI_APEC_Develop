# Import Standard Libraries
import os
import asyncio
import json

# Import Third-Party Libraries
from fastapi.responses import JSONResponse, StreamingResponse
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv(override=True)

# Import 
async def generate_chat_response(data):
    try:
        client = OpenAI()
        # Generate response with OpenAI
        completion = client.chat.completions.create(
                                                model=data.get("model", "gpt-4o").split("_")[0],
                                                messages=data.get("messages", []),
                                                stream=False,
                                                max_tokens=data.get("max_tokens", 150),
                                                )

        response = completion.choices[0].message.content
        
        message = {
            "id": "chatcmpl-nostream",
            "object": "chat.completion",
            "created": int(asyncio.get_event_loop().time()),
            "model": data.get("model", "APEC_model"),
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response
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
        print(f"Error in generating chat responses: {e}")
        return JSONResponse(content={"error": {"message": "Internal server error"}}, status_code=500)
    
import json
import asyncio
from openai import AsyncOpenAI  # Ensure to use the async version of OpenAI

async def generate_chat_responses_stream(data):
    try:
        client = AsyncOpenAI()  # Use AsyncOpenAI for async handling
        print(data.get("model", "gpt-4o").split("_")[0])

        # Generate response with OpenAI using async
        stream = await client.chat.completions.create(
            model=data.get("model", "gpt-4o").split("_")[0],
            messages=data.get("messages", []),
            stream=True,
            max_tokens=data.get("max_tokens", 150),
        )

        # Use async for to handle streaming
        async for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                message_content = chunk.choices[0].delta.content
                # Formato alineado con la API de OpenAI para respuestas en streaming
                message = {
                    "id": f"chatcmpl-stream-{asyncio.get_event_loop().time()}",
                    "object": "chat.completion.chunk",
                    "created": int(asyncio.get_event_loop().time()),
                    "model": data.get("model", "gpt-4o"),
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
        print(f"Error in generating chat responses: {e}")
        error_message = {
            "error": {
                "message": "Internal server error"
            }
        }
        yield f"data: {json.dumps(error_message)}\n\n"



