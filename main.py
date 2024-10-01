# import os
# import logging
# import time
# import mysql.connector
# from mysql.connector import Error
# import openai
# import base64
# import urllib.parse
# from fastapi import FastAPI, HTTPException, APIRouter, UploadFile, File, Form,Cookie,requests,Request
# from pydantic import BaseModel
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import StreamingResponse
# from fastapi.openapi.docs import get_swagger_ui_html
# from typing import AsyncGenerator, Optional
# from typing_extensions import override
# from dotenv import load_dotenv
# from Crypto.Cipher import AES

# # Load environment variables (for OpenAI API key)
# load_dotenv()

# # OpenAI API client initialization
# openai_api_key = os.getenv("OPENAI_API_KEY")
# openai.api_key = openai_api_key
# client = openai.OpenAI(api_key=openai_api_key)

# # Database connection parameters
# DB_CONFIG = {
#     'host': os.getenv("DB_HOST"),
#     'user': os.getenv("DB_USER"),
#     'password': os.getenv("DB_PASSWORD"),
#     'database': os.getenv("DB_NAME")
# }

# # FastAPI app initialization
# app = FastAPI(
#     title="ES Student Bot",
#     description="Welcome to the documentation for ES Student Bot Backend! These API consist of  ES Student Bot GPT APIs! Here you can find all the info",
#     openapi_url="/esstudent/openapi.json",
#     docs_url="/esstudent/docs"
# )

# # Add CORS middleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Allows all origins
#     allow_credentials=True,
#     allow_methods=["*"],  # Allows all methods
#     allow_headers=["*"])

# # Hardcoded Assistant ID
# assistant_id = os.getenv("ASSISTANT_ID")


# class CookieData(BaseModel):
#     cookie: str
    
# class ChatRequest(BaseModel):
#     question: str
#     thread_id: Optional[str] = None  # Make thread_id optional

# class ChatDB:
#     def add_chat(self, email: str, thread_id: str, assistant_id: str, chat_history: str):
#         try:
#             connection = mysql.connector.connect(**DB_CONFIG)
#             if connection.is_connected():
#                 cursor = connection.cursor()
#                 query = "INSERT INTO ChatData (StudentID, ThreadID, AssistantID, ChatHistory) VALUES (%s, %s, %s, %s)"
#                 cursor.execute(query, (email, thread_id, assistant_id, chat_history))
#                 connection.commit()
#         except Error as e:
#             print(f"Error while inserting chat: {e}")
#         finally:
#             if connection.is_connected():
#                 cursor.close()
#                 connection.close()


# def decrypt_esdubai_student_id(cookies: str):
#     def get_cookie_value(cookies, cookie_name):
#         cookies_dict = dict(cookie.strip().split('=', 1) for cookie in cookies.split(';'))
#         return cookies_dict.get(cookie_name)

#     def fix_base64_padding(value):
#         missing_padding = len(value) % 4
#         if missing_padding != 0:
#             value += '=' * (4 - missing_padding)
#         return value

#     def unpad(s):
#         padding_len = s[-1]
#         return s[:-padding_len]

#     key = b'key'.ljust(16, b'\0')  # Replace 'key' with the actual key

#     encrypted_value = get_cookie_value(cookies, 'ESDUBAI_STUDENT_ID')
#     if not encrypted_value:
#         return None

#     encrypted_value = urllib.parse.unquote(encrypted_value)
#     encrypted_value = fix_base64_padding(encrypted_value)

#     try:
#         encrypted_value = base64.b64decode(encrypted_value)
#     except Exception as e:
#         print(f"Error during base64 decoding: {e}")
#         return None

#     cipher = AES.new(key, AES.MODE_ECB)
#     decrypted_value = cipher.decrypt(encrypted_value)

#     try:
#         decrypted_value = unpad(decrypted_value)
#         return decrypted_value.decode('utf-8')
#     except Exception as e:
#         print(f"Error during decryption: {e}")
#         return None

# def wait_for_run_completion(client, thread_id, run_id, sleep_interval=5):
#     """
#     Waits for a run to complete and prints the elapsed time.
#     """
#     while True:
#         try:
#             run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
#             if run.completed_at:
#                 elapsed_time = run.completed_at - run.created_at
#                 formatted_elapsed_time = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
#                 print(f"Run completed in {formatted_elapsed_time}")
#                 logging.info(f"Run completed in {formatted_elapsed_time}")

#                 # Get messages here once Run is completed!
#                 messages = client.beta.threads.messages.list(thread_id=thread_id)
#                 last_message = messages.data[0]
#                 response = last_message.content[0].text.value
#                 return response
#         except Exception as e:
#             logging.error(f"An error occurred while retrieving the run: {e}")
#             break

#         logging.info("Waiting for run to complete...")
#         time.sleep(sleep_interval)

# def get_response_openai_streamed(query):
#     for i in query:
#         time.sleep(0.05)
#         yield i

# def check_credentials(email: str, password: str) -> bool:
#     try:
#         connection = mysql.connector.connect(**DB_CONFIG)
#         if connection.is_connected():
#             cursor = connection.cursor()
#             query = "SELECT * FROM StudentData WHERE StudentID = %s AND StudentPassword = %s"
#             cursor.execute(query, (email, password))
#             result = cursor.fetchone()
#             return result is not None
#     except Error as e:
#         print(f"Error while connecting to MySQL: {e}")
#         return False
#     finally:
#         if connection.is_connected():
#             cursor.close()
#             connection.close()

# # Function to add new student if it doesn't exist
# def add_new_student_to_db(student, student_email, password):
#     """Add a new student to the StudentData table and return the newly created student."""
#     username = student_email.split('@')[0]  # Deriving username from email
#     student.add_student(student_email, username, password)
#     return student.get_student_by_email(student_email)

# # Function to create a new thread if it doesn't exist
# def create_new_thread(student_email, assistant_id, chat):
#     """Create a new thread using OpenAI API, add to ChatData table, and return the thread ID."""
#     thread = openai.beta.threads.create()
#     thread_id = thread.id

#     # Insert new thread details into the ChatData table
#     chat.add_chat(student_email, thread_id, assistant_id, "")
#     return thread_id

# # Main function to get or create thread ID
# def get_or_create_thread_id(studentid: str, assistant_id: str = None, existing_thread_id: str = None):
#     chat = ChatDB()

#     try:
#         connection = mysql.connector.connect(**DB_CONFIG)
#         if connection.is_connected():
#             cursor = connection.cursor()

#             if existing_thread_id:
#                 # Check if the existing thread ID is valid for this user
#                 query = "SELECT ThreadID FROM ChatData WHERE StudentID = %s AND ThreadID = %s"
#                 cursor.execute(query, (studentid, existing_thread_id))
#                 result = cursor.fetchone()
#                 if result:
#                     print("Existing thread id is",existing_thread_id)
#                     return existing_thread_id


#             # If no valid existing thread ID, check if ThreadID exists for this user
#             query = "SELECT ThreadID FROM ChatData WHERE StudentID = %s"
#             cursor.execute(query, (studentid,))
#             result = cursor.fetchone()

#             if result:
#                 print("The thread id is ",result[0])
#                 return result[0]  # Return the existing ThreadID

#             else:
#                 thread_id = create_new_thread(studentid, assistant_id, chat)
#                 print("My new created thread id is ",thread_id)
#                 return thread_id
#     except Error as e:
#         raise HTTPException(status_code=500, detail="Internal server error")
#     finally:
#         if connection.is_connected():
#             cursor.close()
#             connection.close()


# # @app.post("/cookie")
# # async def receive_cookie(cookie_data: CookieData):
# #     global stored_cookie
# #     stored_cookie = cookie_data.cookie
# #     return {"message": "Cookie received and stored"}

# # @app.get("/cookie")
# # async def get_cookie():
# #     global stored_cookie
# #     if stored_cookie is None:
# #         return {"error": "No cookie has been stored yet"}
# #     return {"cookie": stored_cookie}






# @app.get("/", include_in_schema=False)
# async def custom_swagger_ui_html():
#     return get_swagger_ui_html(openapi_url="/openapi.json", title="API Docs")

# # Endpoint to serve OpenAPI schema
# @app.get("/esstudent/openapi.json", include_in_schema=False)
# async def get_openapi_schema():
#     return app.openapi()

# # Login endpoint
# @app.get("/thread")
# async def thread(request: Request):
#     # Extract cookies from the request
#     cookies = request.headers.get("Cookies")
#     print("Cookies are",cookies)

#     if not cookies:
#         raise HTTPException(status_code=400, detail="Cookie not found")
    
#     studentid = decrypt_esdubai_student_id(cookies)
#     print("Student ID is",studentid)
#     if not studentid:
#         raise HTTPException(status_code=400, detail="Invalid cookie value")
    
#     print("Student ID is test:",studentid)
#     thread_id = get_or_create_thread_id(studentid, assistant_id)
#     return {"thread_id": thread_id}


# @app.post("/history/")
# async def post_history(thread_id: str):
#     if not thread_id:
#         raise HTTPException(status_code=400, detail="Thread ID is not provided.")
    
#     try:
#         messages = client.beta.threads.messages.list(thread_id=thread_id)
#         history = []

#         for msg in messages.data:
#             content = msg.content[0].text.value if msg.content else ""
#             history.append({"role": msg.role, "content": content})

#         # Reverse the order of messages so the oldest appears first
#         history.reverse()

#         return {"history": history}
#     except Exception as e:
#         logging.error(f"Error fetching history from assistant: {e}")
#         raise HTTPException(status_code=500, detail="Internal Server Error")



# class QueryModel(BaseModel):
#     question: str

# @app.post('/chat', tags=['Chat'])
# async def get_context_docs_response(chat_request: ChatRequest):
#     try:
#         # If no thread_id is provided, create a new thread or raise an error based on your logic
#         if not chat_request.thread_id:
#             # Option 1: Handle missing thread_id by creating a new one (or)
#             chat_request.thread_id = client.beta.threads.create().id
#             # Option 2: Raise an error if thread_id must be present
#             # raise HTTPException(status_code=400, detail="Thread ID is not provided.")
        
#         # Create the user message based on the incoming question and thread_id
#         user_message = client.beta.threads.messages.create(
#             thread_id=chat_request.thread_id,
#             role="user",
#             content=chat_request.question
#         )

#         # Run the assistant with the proper context
#         run = client.beta.threads.runs.create(
#             thread_id=chat_request.thread_id,
#             assistant_id=assistant_id,
#             instructions = """
# You are a helpful and knowledgeable assistant designed to handle inquiries for students. You should remember previous conversations and respond accordingly. Depending on the user's language, adjust your replies to match their preferred language. When responding, be polite and provide concise, accurate information that adheres to the following instructions. If the user's query matches any of the predefined topics below, respond according to the given guidelines:

# 1. **Class Level Changes**:
#    - If a user asks about changing their class level, tell them:
#      - They need to submit a ticket through the portal addressed to 'Academics' with the category 'Level Change.'
#      - The reason for the change must be included in the description.

# 2. **Retaking a Test**:
#    - For questions about retaking a test:
#      - Inform the user that they must submit a ticket to 'Academics' under the category 'Test.'
#      - They can retake the test only within one week of missing it.

# 3. **Missed Classes**:
#    - If asked about missed classes:
#      - Explain that missed classes are counted as absences unless they took a full week of holidays.

# 4. **Required Level for Courses**:
#    - For inquiries about Business or Digital Marketing classes:
#      - The user must be at level 5 to fully understand the content.

# 5. **Refund for Canceling Accommodation**:
#    - For cancellation refunds:
#      - There is a two-week penalty for cancellations.
#      - A ticket should be sent to 'Accommodation' under the category 'Refund,' explaining the reason for cancellation.

# 6. **Extending Accommodation**:
#    - If asked about accommodation extensions:
#      - Advise users to send a ticket requesting the extension.
#      - The cost varies by hotel and room type, with a minimum extension of four weeks.

# 7. **Changing Classes**:
#    - For changing classes or schedules:
#      - Users should submit a ticket to 'Admissions' with the category 'Class Change.'
#      - For schedule changes, follow the same steps but change the category to 'Class Schedule Change.' 
#      - Include their preferred new schedule in detail, and note that changes are subject to availability.

# 8. **Changing Course Intensity**:
#    - There is no cost for changing the course intensity.
#    - The number of weeks will change based on their request.

# 9. **Intensive Course**:
#    - An intensive course involves two classes per day, and the total course duration is halved.
   
# 10. **Switching Course Type**:
#     - Users can switch from an intensive to a semi-intensive course, which will double the remaining number of weeks.

# 11. **Course Duration**:
#     - A complete level lasts 12 weeks.

# 12. **Book Prices**:
#     - Prices are 220 dirhams for General English books and 150 dirhams for Business books.

# 13. **Speaking Class Book**:
#     - A book is not required for the Speaking class.

# 14. **Class Change Availability**:
#     - If a user is unable to change their class, explain that the groups may be full for that level this week, and they may need to wait until the end of the week when space may open up.

# 15. **Number of Campuses**:
#     - There are two campuses: one in Mazaya and one in Wollongong.

# 16. **Campus Transfer**:
#     - Students can transfer to another country to continue their course, such as to a campus in London.

# 17. **Job Search Assistance**:
#     - Job search assistance in Dubai includes CV workshops, interview preparation, and job postings in the school's WhatsApp group.

# 18. **Resuming Classes**:
#     - To resume classes, users should send a ticket to 'Sales' with the category 'Return to Class,' mentioning their previous level and unit, and when they want to return.

# 19. **Pausing the Course**:
#     - To pause the course, users need to send a ticket to 'Sales' with the category 'Pause Course,' including the reason. Remind them they have six months to resume.

# 20. **Inability to Continue Studies**:
#     - If a user cannot continue studying, they can pause the course for up to six months or transfer it to an immediate family member.

# 21. **Payment Methods for Course Extensions**:
#     - Payments can be made using an international card (3.5% fee), a local card (2.5% fee), or cash on the 15th floor.

# 22. **Payments for Social Activities**:
#     - Payments for social activities can be made on the 15th floor behind reception.

# 23. **Social Activities**:
#     - Social activities can be found in the portal under 'Social Activities' or in the WhatsApp group.

# 24. **Reaching the School**:
#     - Provide instructions on how to reach the school if the user misses the accommodation bus, based on their location.

# 25. **Visa Cancellations**:
#     - For visa cancellations, users should send a ticket to the 'Visas' department with the category 'Visa Cancellation,' including the reason. Processing takes 10 to 15 business days.

# 26. **Visa Extensions**:
#     - For visa extensions, users need to send a ticket to the 'Visas' department stating their desire and reason for the extension.

# 27. **Portal Access Issues**:
#     - If a user cannot access their portal, they should use their registered email and birthdate as their password. If issues persist, they should contact via WhatsApp.

# 28. **Biometric Exams**:
#     - Provide instructions on how to reach biometric exams when the user collects documents from the Visa team.

# 29. **Printing Documents**:
#     - Direct users to the reception on the 36th floor to print documents.

# 30. **Uploading Speaking Test**:
#     - If a user cannot upload their speaking test, advise them to refresh the page and try again or send a voice message via WhatsApp.

# 31. **Wi-Fi at Wollongong**:
#     - The Wi-Fi network at Wollongong is ES Dubai, and the password is 24712471.

# 32. **Teacher Nationalities**:
#     - Most teachers are from the UK, America, and Ireland.

# 33. **Certificate of Completion**:
#     - To receive a certificate, users must attend at least 10 units of a level, maintain 80% attendance, and achieve a grade above 80 in exams.

# 34. **Vacation Eligibility**:
#     - Vacations are only available weekly. If the user attends even one class, they are not eligible for the vacation week.

# 35. **Ticket Response Time**:
#     - If the user hasn't received a response and cannot open another ticket in the same department, inform them that responses typically take 24 to 48 hours if the ticket is not closed.

# 36. **Courses Offered**:
#     - Courses include General English, Business, Speaking, Digital Marketing, IELTS, and Academic English.

# 37. **Class Format**:
#     - All classes are 100% in-person and held Monday to Friday.
# """

#         )

#         # Wait for completion and return the response
#         response_text = wait_for_run_completion(client=client, thread_id=chat_request.thread_id, run_id=run.id)
#         return StreamingResponse(get_response_openai_streamed(response_text), media_type="text/event-stream")

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)



import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from dotenv import load_dotenv
import uvicorn

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="ES Student Bot",
    description="Welcome to the documentation for ES Student Bot Backend! These API consist of ES Student Bot GPT APIs! Here you can find all the info",
    openapi_url="/esstudent/openapi.json",
    docs_url="/esstudent/docs"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"]
)

# Import and include the router
from routers.router import router as esstudent_router
app.include_router(esstudent_router, prefix="/esstudent")

# Custom Swagger UI
@app.get("/", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(openapi_url="/esstudent/openapi.json", title="API Docs")

# Endpoint to serve OpenAPI schema
@app.get("/esstudent/openapi.json", include_in_schema=False)
async def get_openapi_schema():
    return app.openapi()

# Main entry point
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
