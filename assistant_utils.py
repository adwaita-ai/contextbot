from openai import OpenAI
import os
import json
import time
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load .env file
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
logger.debug("OpenAI client initialized")

def send_email(to: str, subject: str, body: str):
    """Simulate sending an email"""
    logger.info(f"Simulating email to {to}")
    print(f"📧 Email sent to {to}")
    print(f"Subject: {subject}")
    print(f"Body: {body}")
    print("-" * 50)
    return "Email sent successfully"

import os
import logging
from openai import OpenAI
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load .env file
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
logger.debug("OpenAI client initialized")

def create_or_get_assistant(context_text):
    """Create an Assistant with context-restricted instructions and uploaded file"""
    instructions = (
        "You are a context-locked AI assistant. Answer questions only based on the content provided in the uploaded file. "
        "If a question is out of scope, respond with: 'I'm sorry, I can only answer questions based on the provided training content.' "
        "If the user requests to send an email notification, call the send_email function with the appropriate parameters."
    )
    try:
        # Save context to a temporary file
        with open("context.txt", "w", encoding="utf-8") as f:
            f.write(context_text)
        
        # Upload the file to OpenAI
        with open("context.txt", "rb") as f:
            file = client.files.create(file=f, purpose="assistants")
        
        # Create Assistant with the uploaded file
        assistant = client.beta.assistants.create(
            name="ContextBot",
            instructions=instructions,
            model="gpt-4o",
            tools=[{
                "type": "function",
                "function": {
                    "name": "send_email",
                    "description": "Simulate sending an email notification",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "to": {"type": "string", "description": "Recipient email address"},
                            "subject": {"type": "string", "description": "Email subject"},
                            "body": {"type": "string", "description": "Email body"}
                        },
                        "required": ["to", "subject", "body"]
                    }
                }
            }],
            file_ids=[file.id]  # Attach the uploaded file
        )
        logger.debug(f"Created assistant ID: {assistant.id} with file ID: {file.id}")
        return assistant
    except Exception as e:
        logger.error(f"Failed to create assistant: {e}")
        raise Exception(f"Failed to create assistant: {e}")
    
def ask_assistant(query, context_text, assistant_id):
    """Query the Assistant with a user question"""
    try:
        logger.debug(f"Querying assistant {assistant_id} with: {query}")
        # Create a thread
        thread = client.beta.threads.create()
        
        # Add user message to the thread
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=query
        )
        
        # Run the assistant
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant_id
        )
        
        # Poll for completion
        while run.status in ["queued", "in_progress", "requires_action"]:
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            
            # Handle tool calls
            if run.status == "requires_action":
                tool_outputs = []
                for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                    if tool_call.function.name == "send_email":
                        args = json.loads(tool_call.function.arguments)
                        output = send_email(args["to"], args["subject"], args["body"])
                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": output
                        })
                client.beta.threads.runs.submit_tool_outputs(
                    thread_id=thread.id,
                    run_id=run.id,
                    tool_outputs=tool_outputs
                )
        
        # Get the response
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        response = messages.data[0].content[0].text.value
        logger.debug(f"Assistant response: {response}")
        return response
    except Exception as e:
        logger.error(f"Error querying assistant: {e}")
        return f"Error: {e}"