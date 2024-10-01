import mysql.connector
from mysql.connector import Error
from fastapi import HTTPException
import os

# Database configuration
DB_CONFIG = {
    'host': os.getenv("DB_HOST"),
    'user': os.getenv("DB_USER"),
    'password': os.getenv("DB_PASSWORD"),
    'database': os.getenv("DB_NAME")
}

class ChatDB:
    def add_chat(self, email: str, thread_id: str, assistant_id: str, chat_history: str):
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            if connection.is_connected():
                cursor = connection.cursor()
                query = "INSERT INTO ChatData (StudentID, ThreadID, AssistantID, ChatHistory) VALUES (%s, %s, %s, %s)"
                cursor.execute(query, (email, thread_id, assistant_id, chat_history))
                connection.commit()
        except Error as e:
            print(f"Error while inserting chat: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

def get_or_create_thread_id(studentid: str, assistant_id: str = None, existing_thread_id: str = None):
    chat = ChatDB()

    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            cursor = connection.cursor()

            if existing_thread_id:
                # Check if the existing thread ID is valid for this user
                query = "SELECT ThreadID FROM ChatData WHERE StudentID = %s AND ThreadID = %s"
                cursor.execute(query, (studentid, existing_thread_id))
                result = cursor.fetchone()
                if result:
                    print("Existing thread id is", existing_thread_id)
                    return existing_thread_id

            # If no valid existing thread ID, check if ThreadID exists for this user
            query = "SELECT ThreadID FROM ChatData WHERE StudentID = %s"
            cursor.execute(query, (studentid,))
            result = cursor.fetchone()

            if result:
                print("The thread id is ", result[0])
                return result[0]  # Return the existing ThreadID

            else:
                thread_id = client.beta.threads.create().id  # Ensure `client` is accessible here
                chat.add_chat(studentid, thread_id, assistant_id, "")
                print("My new created thread id is ", thread_id)
                return thread_id
    except Error as e:
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
