# ESBOT Backend

ESBOT is a FastAPI-based backend for a chatbot designed to handle student inquiries. It offers multilingual capabilities, session state management, and the ability to store and retrieve previous chat history. The project is built with a React frontend, FastAPI backend, and MySQL database to provide intelligent responses using OpenAI's language model.

## Key Features

- **Multilingual Capability**: The bot can respond in multiple languages, adjusting to the user's preferred language.
- **Session Management**: Each chat session is maintained through session state, ensuring smooth conversations across multiple interactions.
- **Chat History**: The system stores previous conversations, allowing users to retrieve their chat history at any time.

## Getting Started

### Prerequisites

- Python 3.x
- MySQL
- FastAPI
- OpenAI API Key

### Clone the Repository

First, clone the repository to your local machine:
git clone https://github.com/yourusername/esbot-backend.git
cd esbot-backend

### pip install -r requirements.txt
### uvicorn main:app --host 0.0.0.0 --port 8000 --reload


## API ENDPOINT
- **Thread**: Decrypt the student cookie to get the StudentID , checks if the Student's ThreadID exists in the MYSQL Database otherwise creates one against that StudentID
- **History**: Fetches history of chat using OpenAI Assistant API for the StudentID using their threadID.
- **Chat**: Sends a chat request to the Assistant API and replies in real time

 
