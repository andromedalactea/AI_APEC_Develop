# Import Standard Libraries
import asyncio
import json

# Local imports from the same directory
from scripts.extract_context_from_vs import extract_context_from_vector_search
from scripts.image_to_base_64 import image_to_base64_markdown
from scripts.auxiliar_functions import sources_to_md
# Import Third-Party Libraries
from fastapi.responses import JSONResponse, StreamingResponse
from openai import OpenAI, AsyncOpenAI
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
    

async def generate_chat_responses_stream(data):
    try:
        # Extract the context for the model
        context, sources = extract_context_from_vector_search(str(data['messages'][-1]['content']))
        data["messages"].insert(-1, {"role": "system", "content": f"This is the context regarding of the user query:\n{context}"})
        print(data["messages"])
        client = AsyncOpenAI()  # Use AsyncOpenAI for async handling
        print(data.get("model", "gpt-4o").split("_")[0])

        # Generate response with OpenAI using async
        stream = await client.chat.completions.create(
            model=data.get("model", "gpt-4o").split("_")[0],
            messages=data.get("messages", []),
            stream=True,
            max_tokens=data.get("max_tokens", 1000),
        )

        # Use async for to handle streaming
        # image_md = image_to_base64_markdown("/home/andromedalactea/freelance/AI_APEC_Develop/to_develop_purposes/ecuatorial.png", "Here is an image included in the Markdown text:")
        # print(image_md)
        async for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                message_content = chunk.choices[0].delta.content
                # message_content += "![Alt text](https://pngimg.com/uploads/lgbt/lgbt_PNG38.png)" # Append the image markdown to the message content
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

        # Create the references in Markdown format
        md_sources = sources_to_md(sources)
        # Enviar el mensaje de finalización del streaming
        end_message = {
            "id": "chatcmpl-stream-end",
            "object": "chat.completion.chunk",
            "created": int(asyncio.get_event_loop().time()),
            "model": data.get("model", "APEC_model"),
            "choices": [{
                "delta": {
                    "content": md_sources
                },
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