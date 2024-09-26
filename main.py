import os
import logging
import time
import mysql.connector
from mysql.connector import Error
import openai
import base64
import urllib.parse
from fastapi import FastAPI, HTTPException, APIRouter, UploadFile, File, Form,Cookie,requests,Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator, Optional
from typing_extensions import override
from dotenv import load_dotenv
from Crypto.Cipher import AES

# Load environment variables (for OpenAI API key)
load_dotenv()

# OpenAI API client initialization
openai_api_key = os.getenv("OPENAI_API_KEY")
openai.api_key = openai_api_key
client = openai.OpenAI(api_key=openai_api_key)

# Database connection parameters
DB_CONFIG = {
    'host': os.getenv("DB_HOST"),
    'user': os.getenv("DB_USER"),
    'password': os.getenv("DB_PASSWORD"),
    'database': os.getenv("DB_NAME")
}

# FastAPI app initialization
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"])

# Hardcoded Assistant ID
assistant_id = os.getenv("ASSISTANT_ID")


class CookieData(BaseModel):
    cookie: str
    
class ChatRequest(BaseModel):
    question: str
    thread_id: Optional[str] = None  # Make thread_id optional

class ChatDB:
    def add_chat(self, email: str, thread_id: str, assistant_id: str):
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            if connection.is_connected():
                cursor = connection.cursor()
                query = "INSERT INTO chatbot_english_db (StudentID, ThreadID, AssistantID) VALUES (%s, %s, %s)"
                cursor.execute(query, (email, thread_id, assistant_id))
                connection.commit()
        except Error as e:
            print(f"Error while inserting chat: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

def decrypt_esdubai_student_id(cookies: str):
    def get_cookie_value(cookies, cookie_name):
        cookies_dict = dict(cookie.strip().split('=', 1) for cookie in cookies.split(';'))
        return cookies_dict.get(cookie_name)

    def fix_base64_padding(value):
        missing_padding = len(value) % 4
        if missing_padding != 0:
            value += '=' * (4 - missing_padding)
        return value

    def unpad(s):
        padding_len = s[-1]
        return s[:-padding_len]

    key = b'key'.ljust(16, b'\0')  # Replace 'key' with the actual key

    encrypted_value = get_cookie_value(cookies, 'ESDUBAI_STUDENT_ID')
    if not encrypted_value:
        return None

    encrypted_value = urllib.parse.unquote(encrypted_value)
    encrypted_value = fix_base64_padding(encrypted_value)

    try:
        encrypted_value = base64.b64decode(encrypted_value)
    except Exception as e:
        print(f"Error during base64 decoding: {e}")
        return None

    cipher = AES.new(key, AES.MODE_ECB)
    decrypted_value = cipher.decrypt(encrypted_value)

    try:
        decrypted_value = unpad(decrypted_value)
        return decrypted_value.decode('utf-8')
    except Exception as e:
        print(f"Error during decryption: {e}")
        return None

def wait_for_run_completion(client, thread_id, run_id, sleep_interval=5):
    """
    Waits for a run to complete and prints the elapsed time.
    """
    while True:
        try:
            run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
            if run.completed_at:
                elapsed_time = run.completed_at - run.created_at
                formatted_elapsed_time = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
                print(f"Run completed in {formatted_elapsed_time}")
                logging.info(f"Run completed in {formatted_elapsed_time}")

                # Get messages here once Run is completed!
                messages = client.beta.threads.messages.list(thread_id=thread_id)
                last_message = messages.data[0]
                response = last_message.content[0].text.value
                return response
        except Exception as e:
            logging.error(f"An error occurred while retrieving the run: {e}")
            break

        logging.info("Waiting for run to complete...")
        time.sleep(sleep_interval)

def get_response_openai_streamed(query):
    for i in query:
        time.sleep(0.05)
        yield i

# Function to create a new thread if it doesn't exist
def create_new_thread(student_email, assistant_id, chat):
    """Create a new thread using OpenAI API, add to chatbot_english_db table, and return the thread ID."""
    thread = openai.beta.threads.create()
    thread_id = thread.id

    # Insert new thread details into the chatbot_english_db table
    chat.add_chat(student_email, thread_id, assistant_id)
    return thread_id

# Main function to get or create thread ID
def get_or_create_thread_id(studentid: str, assistant_id: str = None, existing_thread_id: str = None):
    chat = ChatDB()

    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            cursor = connection.cursor()

            if existing_thread_id:
                # Check if the existing thread ID is valid for this user
                query = "SELECT ThreadID FROM chatbot_english_db WHERE StudentID = %s AND ThreadID = %s"
                cursor.execute(query, (studentid, existing_thread_id))
                result = cursor.fetchone()
                if result:
                    print("Existing thread id is",existing_thread_id)
                    return existing_thread_id


            # If no valid existing thread ID, check if ThreadID exists for this user
            query = "SELECT ThreadID FROM chatbot_english_db WHERE StudentID = %s"
            cursor.execute(query, (studentid,))
            result = cursor.fetchone()

            if result:
                print("The thread id is ",result[0])
                return result[0]  # Return the existing ThreadID

            else:
                thread_id = create_new_thread(studentid, assistant_id, chat)
                print("My new created thread id is ",thread_id)
                return thread_id
    except Error as e:
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


# Login endpoint
@app.get("/thread")
async def thread(request: Request):
    # Extract cookies from the request
    cookies = request.headers.get("Cookies")
    print("Cookies are",cookies)

    if not cookies:
        raise HTTPException(status_code=400, detail="Cookie not found")
    
    studentid = decrypt_esdubai_student_id(cookies)
    print("Student ID is",studentid)
    if not studentid:
        raise HTTPException(status_code=400, detail="Invalid cookie value")
    
    print("Student ID is test:",studentid)
    thread_id = get_or_create_thread_id(studentid, assistant_id)
    return {"thread_id": thread_id}


@app.post("/history/")
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



class QueryModel(BaseModel):
    question: str

@app.post('/chat', tags=['RAG_Related'])
async def get_context_docs_response(chat_request: ChatRequest):
    try:
        # If no thread_id is provided, create a new thread or raise an error based on your logic
        if not chat_request.thread_id:
            # Option 1: Handle missing thread_id by creating a new one (or)
            chat_request.thread_id = client.beta.threads.create().id
            # Option 2: Raise an error if thread_id must be present
            # raise HTTPException(status_code=400, detail="Thread ID is not provided.")
        
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
            instructions =  """
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
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
