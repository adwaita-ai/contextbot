import streamlit as st
import re
import os
from dotenv import load_dotenv
import logging
from huggingface_hub import InferenceClient

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load .env file
load_dotenv()

# Debug HF token loading
hf_token = os.getenv("HF_TOKEN")
if not hf_token:
    logger.error("HF_TOKEN not found in environment variables")
    st.error("❌ HF_TOKEN not found. Please configure it in Streamlit Cloud Secrets or .env file.")
    st.stop()
try:
    client = InferenceClient(token=hf_token)
    # Test token with a simple request
    client.text_generation("test", model="meta-llama/Llama-3.2-3B-Instruct")
    logger.debug("Hugging Face client initialized")
except Exception as e:
    logger.error(f"Invalid HF_TOKEN: {e}")
    st.error(f"❌ Invalid HF_TOKEN: {e}. Please verify the token in Streamlit Cloud Secrets or .env file.")
    st.stop()

# Page config
st.set_page_config(page_title="ContextBot", page_icon="🤖", layout="wide")

# Load external CSS
try:
    with open("style.css") as f:
        css = f.read()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    st.warning("style.css not found. Using default styling.")

# Import assistant_utils
from assistant_utils import query_llama, send_email

# Session state initialization
for key in ["context", "emails", "chat_history"]:
    if key not in st.session_state:
        st.session_state[key] = [] if key in ["emails", "chat_history"] else ""

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
                st.session_state["context"] = training_content
                st.success("✅ Context saved successfully! You can now ask questions.")
            except Exception as e:
                st.error(f"Failed to save context: {e}")
                logger.error(f"Error saving context: {e}")
        else:
            st.error("Please enter some training content.")

    # Email Capture
    st.markdown("""
    <div class="section-header">
        <span class="icon">✉️</span>
        <h2>Email Capture</h2>
    </div>
    """, unsafe_allow_html=True)

    email_input = st.text_input("Enter an email address:", key="email_input")
    if st.button("Add Email", key="add_email"):
        if email_input:
            if re.match(r"[^@]+@[^@]+\.[^@]+", email_input):
                if email_input not in st.session_state["emails"]:
                    st.session_state["emails"].append(email_input)
                    st.success(f"✅ Email {email_input} added successfully!")
                else:
                    st.warning("Email already exists.")
            else:
                st.error("Please enter a valid email address.")
        else:
            st.error("Please enter an email address.")

    # Display registered emails
    if st.session_state["emails"]:
        st.markdown("**Registered Emails:**")
        for email in st.session_state["emails"]:
            st.write(f"- {email}")

# Right Panel: Chat
with col2:
    st.markdown("""
    <div class="section-header">
        <span class="icon">💬</span>
        <h2>Chat with ContextBot</h2>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state["context"]:
        st.warning("Please save training content before chatting.")
    else:
        user_input = st.text_input("Ask a question:", key="user_input")
        if st.button("Send", key="send_question"):
            if user_input:
                try:
                    response = query_llama(user_input, st.session_state["context"], st.session_state["emails"], client)
                    st.session_state["chat_history"].append({"user": user_input, "bot": response})
                except Exception as e:
                    st.error(f"Error querying Llama: {e}")
                    logger.error(f"Error querying Llama: {e}")
            else:
                st.error("Please enter a question.")

        # Display chat history
        if st.session_state["chat_history"]:
            st.markdown("**Chat History:**")
            for chat in st.session_state["chat_history"]:
                st.markdown(f"**You:** {chat['user']}")
                st.markdown(f"**Bot:** {chat['bot']}")
                st.markdown("---")