import os
import json
import logging
import re
from huggingface_hub import InferenceClient
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from io import BytesIO

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load .env file
load_dotenv()

# Initialize Hugging Face Inference Client
client = InferenceClient(api_key=os.getenv("HF_TOKEN"))
logger.debug("Hugging Face Inference Client initialized")

def extract_pdf_text(file):
    """Extract text from a PDF file"""
    try:
        pdf_reader = PdfReader(BytesIO(file.read()))
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        logger.debug(f"Extracted {len(text)} characters from PDF")
        return text
    except Exception as e:
        logger.error(f"Error extracting PDF text: {e}")
        return ""

def save_memory(session_id, chat_history):
    """Save chat history to a file for persistence"""
    try:
        with open(f"memory_{session_id}.json", "w", encoding="utf-8") as f:
            json.dump(chat_history, f, ensure_ascii=False, indent=2)
        logger.debug(f"Saved chat history for session {session_id}")
    except Exception as e:
        logger.error(f"Failed to save memory: {e}")

def load_memory(session_id):
    """Load chat history from a file"""
    try:
        if os.path.exists(f"memory_{session_id}.json"):
            with open(f"memory_{session_id}.json", "r", encoding="utf-8") as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"Failed to load memory: {e}")
        return []

def send_email(to: str, subject: str, body: str):
    """Simulate sending an email"""
    logger.info(f"Simulating email to {to}")
    print(f"📧 Email sent to {to}")
    print(f"Subject: {subject}")
    print(f"Body: {body}")
    print("-" * 50)
    return "Email sent successfully"

def ask_assistant(query, context_text, session_id, pdf_text=""):
    """Query the Mixtral-8x7B-Instruct model via Hugging Face Inference API with context restriction"""
    try:
        logger.debug(f"Querying Mixtral-8x7B-Instruct model with: {query[:50]}...")
        # Combine manual context and PDF-extracted text
        full_context = context_text + "\n\n" + pdf_text if pdf_text else context_text
        prompt = (
            "You are a context-locked assistant. Answer questions only based on the following training content:\n\n"
            f"{full_context}\n\n"
            "If a question is out of scope, respond with: 'I'm sorry, I can only answer questions based on the provided training content.' "
            "If the query requests to send an email, parse the email parameters and return the email response.\n\n"
            f"User query: {query}"
        )
        
        # Query the Mixtral-8x7B-Instruct model
        completion = client.chat.completions.create(
            model="mistralai/Mixtral-8x7B-Instruct-v0.1",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=512,
            temperature=0.7,
            top_p=0.9
        )
        
        response_text = completion.choices[0].message.content
        logger.debug(f"Mixtral-8x7B-Instruct response: {response_text[:50]}...")
        
        # Handle email requests
        if "send email" in query.lower():
            email_match = re.search(r"send email to (\S+) with subject (.+?) and body (.+)", query, re.IGNORECASE)
            if email_match:
                to, subject, body = email_match.groups()
                email_response = send_email(to, subject, body)
                response_text = f"{response_text}\nEmail sent: {email_response}"
        
        # Save to chat history
        chat_history = load_memory(session_id)
        chat_history.append({"type": "user", "message": query})
        chat_history.append({"type": "bot", "message": response_text})
        save_memory(session_id, chat_history)
        
        return response_text
    except Exception as e:
        logger.error(f"Error querying Mixtral-8x7B-Instruct model: {e}")
        return f"Error: {e}"
