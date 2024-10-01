import os
import logging
import time
import mysql.connector
from mysql.connector import Error
import openai
import base64
import urllib.parse
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from Crypto.Cipher import AES

# Import helper functions and classes
from utils.decrypt_cookie import decrypt_esdubai_student_id
from utils.database import ChatDB, get_or_create_thread_id
from utils.openai_response import wait_for_run_completion, get_response_openai_streamed

router = APIRouter()

# Initialize OpenAI API
openai_api_key = os.getenv("OPENAI_API_KEY")
openai.api_key = openai_api_key
client = openai.OpenAI(api_key=openai_api_key)

# Database configuration
DB_CONFIG = {
    'host': os.getenv("DB_HOST"),
    'user': os.getenv("DB_USER"),
    'password': os.getenv("DB_PASSWORD"),
    'database': os.getenv("DB_NAME")
}

# Hardcoded Assistant ID
assistant_id = os.getenv("ASSISTANT_ID")

class CookieData(BaseModel):
    cookie: str

class ChatRequest(BaseModel):
    question: str
    thread_id: Optional[str] = None  # Make thread_id optional

@router.get("/thread",tags=['Cookie and Thread'])
async def thread(request: Request):
    # Extract cookies from the request
    cookies = request.headers.get("Cookies")
    print("Cookies are", cookies)

    if not cookies:
        raise HTTPException(status_code=400, detail="Cookie not found")

    studentid = decrypt_esdubai_student_id(cookies)
    print("Student ID is", studentid)
    if not studentid:
        raise HTTPException(status_code=400, detail="Invalid cookie value")

    print("Student ID is test:", studentid)
    thread_id = get_or_create_thread_id(studentid, assistant_id)
    return {"thread_id": thread_id}

@router.post("/history/",tags=['History'])
async def post_history(thread_id: str):
    if not thread_id:
        raise HTTPException(status_code=400, detail="Thread ID is not provided.")

    try:
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        history = []

        for msg in messages.data:
            content = msg.content[0].text.value if msg.content else ""
            history.append({"role": msg.role, "content": content})

        # Reverse the order of messages so the oldest appears first
        history.reverse()

        return {"history": history}
    except Exception as e:
        logging.error(f"Error fetching history from assistant: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post('/chat', tags=['Chat'])
async def get_context_docs_response(chat_request: ChatRequest):
    try:
        # If no thread_id is provided, create a new thread
        if not chat_request.thread_id:
            chat_request.thread_id = client.beta.threads.create().id

        # Create the user message based on the incoming question and thread_id
        user_message = client.beta.threads.messages.create(
            thread_id=chat_request.thread_id,
            role="user",
            content=chat_request.question
        )

        # Run the assistant with the proper context
        run = client.beta.threads.runs.create(
            thread_id=chat_request.thread_id,
            assistant_id=assistant_id,
            instructions="""
You are an educational chatbot designed to assist students in learning English.

Your primary focus is to:
- Provide clear, engaging, and context-appropriate responses.
- Help students understand grammar, vocabulary, pronunciation, and sentence structure.

Your responses should always aim to:
- Simplify complex concepts where necessary.
- Offer examples to clarify points.
- Provide corrections in a supportive and constructive manner.

When interacting with students:
- Be patient and maintain a friendly tone.
- Use positive reinforcement to motivate and encourage them.

Adapt your language based on the student's proficiency level:
- For beginners, use simpler English and offer clear explanations.
- For higher-level learners, use more advanced English and delve deeper into topics.
"""
        )

        # Wait for completion and return the response
        response_text = wait_for_run_completion(client=client, thread_id=chat_request.thread_id, run_id=run.id)
        return StreamingResponse(get_response_openai_streamed(response_text), media_type="text/event-stream")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
