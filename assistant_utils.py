import logging
import json
import re

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def send_email(to: str, subject: str, body: str):
    """Simulate sending an email"""
    logger.info(f"Simulating email to {to}")
    print(f"📧 Email sent to {to}")
    print(f"Subject: {subject}")
    print(f"Body: {body}")
    print("-" * 50)
    return "Email sent successfully"

def query_llama(query, context_text, emails, client):
    """Query Llama 3.2 3B Instruct with context-restricted instructions"""
    instructions = (
        "You are a context-locked AI assistant using Llama 3.2 3B Instruct. Answer questions only based on the provided context below. "
        "If a question is out of scope, respond with: 'I'm sorry, I can only answer questions based on the provided training content.' "
        "If the user requests to send an email notification, output a JSON object with 'function': 'send_email', 'to': email address, 'subject', and 'body'. "
        f"Registered emails: {', '.join(emails) if emails else 'None'}.\n\n"
        f"Context:\n{context_text}\n"
    )
    prompt = f"{instructions}\nUser: {query}\nAssistant: "
    
    try:
        # Call Llama 3.2 via Hugging Face Inference API
        response = client.text_generation(
            prompt,
            model="meta-llama/Llama-3.2-3B-Instruct",
            max_new_tokens=200,
            temperature=0.7,
            top_p=0.9,
            stop_sequences=["</s>", "Assistant: "]
        )
        logger.debug(f"Llama response: {response}")

        # Check for function call (JSON-like output)
        function_call_pattern = r'\{.*"function":\s*"send_email".*\}'
        match = re.search(function_call_pattern, response, re.DOTALL)
        if match:
            try:
                function_data = json.loads(match.group(0))
                if function_data.get("function") == "send_email":
                    to = function_data.get("to")
                    if to not in emails:
                        return f"Error: Email {to} not registered."
                    return send_email(to, function_data.get("subject"), function_data.get("body"))
            except json.JSONDecodeError:
                logger.error("Invalid JSON in function call")
                return "Error: Invalid function call format."

        # Return the response if not a function call
        return response.strip()
    except Exception as e:
        logger.error(f"Error querying Llama: {e}")
        return f"Error: {e}"