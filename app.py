import streamlit as st
import re
import os
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load .env file
load_dotenv()

# Debug API key loading
api_key = os.getenv("OPENAI_API_KEY")
logger.debug(f"Loaded API Key: {api_key[:8]}...{api_key[-4:]}")  # Mask key for safety

# Page config
st.set_page_config(page_title="ContextBot", page_icon="🤖", layout="wide")

# Load external CSS
try:
    with open("style.css") as f:
        css = f.read()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    st.warning("style.css not found. Using default styling.")

# Check for API key
if not api_key:
    st.error("❌ OPENAI_API_KEY not found in .env file. Please provide a valid API key.")
    st.stop()

# Import assistant_utils only if API key is set
from assistant_utils import create_or_get_assistant, ask_assistant, send_email

# Page header
st.markdown("""
<div class="header">
    <h1>🤖 ContextBot</h1>
    <p>Your Private Context-Locked AI Assistant</p>
</div>
""", unsafe_allow_html=True)

# Session state initialization
for key in ["context", "emails", "chat_history", "assistant_id"]:
    if key not in st.session_state:
        st.session_state[key] = [] if key in ["emails", "chat_history"] else "" if key == "context" else None

# Layout
col1, col2 = st.columns([1, 1])

# Left Panel: Training + Email
with col1:
    st.markdown("""
    <div class="section-header">
        <span class="icon">📚</span>
        <h2>Training Content</h2>
    </div>
    """, unsafe_allow_html=True)

    training_content = st.text_area("Enter your training content (FAQs, docs, etc.):", height=200, key="training_content")

    if st.button("Save Context", key="save_context"):
        if training_content.strip():
            try:
                # Only create a new assistant if one doesn't exist
                if not st.session_state["assistant_id"]:
                    assistant = create_or_get_assistant(training_content)
                    st.session_state["assistant_id"] = assistant.id
                st.session_state["context"] = training_content
                st.success("✅ Context saved successfully! You can now ask questions.")
            except Exception as e:
                st.error(f"Failed to save context: {e}")
                logger.error(f"Error saving context: {e}")
        else:
            st.error("Please enter some training content.")

            
# Right Panel: Chat Interface
with col2:
    st.markdown("""
    <div class="section-header">
        <span class="icon">💬</span>
        <h2>Chat with ContextBot</h2>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state["context"] and st.session_state["assistant_id"]:
        if st.button("🗑️ Clear Chat History", key="clear_chat"):
            st.session_state["chat_history"] = []
            st.rerun()

        for chat in st.session_state["chat_history"]:
            msg_type = chat["type"]
            msg_content = chat["message"]
            st.markdown(
                f"""
                <div class="chat-message {'user-message' if msg_type == 'user' else 'bot-message'}">
                    <strong>{'You' if msg_type == 'user' else '🤖 ContextBot'}:</strong> {msg_content}
                </div>
                """, unsafe_allow_html=True
            )

        query = st.text_input("Ask a question based on the training content:", key="chat_input")

        if st.button("📤 Send", key="send_query") and query:
            st.session_state["chat_history"].append({"type": "user", "message": query})
            with st.spinner("🤔 Thinking..."):
                try:
                    response = ask_assistant(query, st.session_state["context"], st.session_state["assistant_id"])
                    st.session_state["chat_history"].append({"type": "bot", "message": response})
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {e}")
                    logger.error(f"Error querying assistant: {e}")
    else:
        st.info("📝 Please save your training content to begin chatting.")

# Footer
st.markdown("""
<div class="footer">
    <p>© 2025 ContextBot. Powered by OpenAI Assistants API</p>
</div>
""", unsafe_allow_html=True)