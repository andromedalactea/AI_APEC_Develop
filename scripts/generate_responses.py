# Import Standard Libraries
import os
import asyncio
import json

# Local imports from the same directory
from scripts.extract_context_from_vs import extract_context_from_vector_search
from scripts.image_to_base_64 import image_to_base64_markdown
from scripts.auxiliar_functions import sources_to_md, replace_sources, extract_user_messages
from prompts.prompts import system_prompt

# Import Third-Party Libraries
from fastapi.responses import JSONResponse, StreamingResponse
from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv(override=True)

async def generate_chat_response(data):
    try:
        client = OpenAI()
        # Generate response with OpenAI
        completion = client.chat.completions.create(
                                                model=data.get("model", "gpt-4o").split("&")[0],
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
        # User context to vector search
        user_messages = extract_user_messages(data['messages'], 4)
        
        # Extract the context for the model
        context, sources = extract_context_from_vector_search(user_messages)
        
        # Intsert the context and prompt in the messages
        data["messages"].insert(-1, {"role": "system", "content": f"This is the context regarding of the user query:\n{context}"})
        data["messages"].insert(-1, {"role": "system", "content": system_prompt})
        
        
        print(data["messages"])
        client = AsyncOpenAI()  # Use AsyncOpenAI for async handling
        print(data.get("model", "gpt-4o").split("&")[0])

        # Generate response with OpenAI using async
        stream = await client.chat.completions.create(
            model=data.get("model", "gpt-4o").split("&")[0],
            messages=data.get("messages", []),
            stream=True,
            max_tokens=data.get("max_tokens", 1000),
        )

        # Use async for to handle streaming
        # image_md = image_to_base64_markdown("/home/andromedalactea/freelance/AI_APEC_Develop/to_develop_purposes/ecuatorial.png", "Here is an image included in the Markdown text:")
        # print(image_md)
        # Extract the domain
        domain_docs = os.getenv("DOMAIN_DOCS")

        # Generate the URLs
        URLS = [f"{domain_docs}/pdfs/{source.replace('/mnt/apec-ai-feed/', '').replace(' ', '%20')}" for source, _ in sources]

        message_content = ""
        sources_used = []
        async for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                message_content += chunk.choices[0].delta.content

                if message_content.count('{') != message_content.count('}') and '\n' not in message_content:
                    continue

                # Replace the placeholders with the corresponding sources
                message_content, sources_used_ = replace_sources(message_content, URLS)
                
                # Extend the sources used
                sources_used.extend(sources_used_)
                print(message_content)
                # message_content += "![Alt text](https://pngimg.com/uploads/lgbt/lgbt_PNG38.png)" # Append the image markdown to the message content
                # Formato alineado con la API de OpenAI para respuestas en streaming
                message = {
                    "id": f"chatcmpl-stream-{asyncio.get_event_loop().time()}",
                    "object": "chat.completion.chunk",
                    "created": int(asyncio.get_event_loop().time()),
                    "model": data.get("model", "gpt-4o"),
                    "choices": [{
                        "delta": {
                            "content":  message_content
                        },
                        "index": 0,
                        "finish_reason": None
                    }]
                }
                event = f"data: {json.dumps(message)}\n\n"

                # Delete the message content
                message_content = ""
                yield event

        # Create the references in Markdown format
        sources_used = list(sorted(set(sources_used)))
        md_sources = sources_to_md(sources, sources_used)

        # Enviar el mensaje de finalización del streaming
        end_message = {
            "id": "chatcmpl-stream-end",
            "object": "chat.completion.chunk",
            "created": int(asyncio.get_event_loop().time()),
            "model": data.get("model", "APEC_model"),
            "choices": [{
                "delta": {
                    "content": "\n\n" + md_sources
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