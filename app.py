import streamlit as st
from assistant_utils import ask_assistant, load_memory, save_memory, send_email, extract_pdf_text
import re
from dotenv import load_dotenv
import os
import logging
import time

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load .env file
load_dotenv()

# Debug API key loading
api_key = os.getenv("HF_TOKEN")
if api_key:
    logger.debug(f"Loaded HF_TOKEN: {api_key[:8]}...{api_key[-4:]}")
else:
    logger.error("HF_TOKEN not found in .env file")

# Page config
st.set_page_config(
    page_title="ContextBot - AI Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "ContextBot - Your Private Context-Locked AI Assistant"
    }
)

# Load external CSS
try:
    with open("style.css") as f:
        css = f.read()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    st.warning("⚠️ style.css not found. Using default styling.")

# Check for API key
if not api_key:
    st.markdown(
        """
        <div style="text-align: center; padding: 3rem; background: linear-gradient(135deg, rgba(244, 67, 54, 0.1), rgba(229, 115, 115, 0.05)); border: 1px solid rgba(244, 67, 54, 0.3); border-radius: 20px; margin: 2rem;">
            <h2 style="color: #FF5252; margin-bottom: 1rem;">🔑 API Configuration Required</h2>
            <p style="color: rgba(0, 0, 0, 0.8); font-size: 1.1rem;">HF_TOKEN not found in .env file. Please provide a valid Hugging Face API token to continue.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.stop()

# Session state initialization
session_defaults = {
    "context": "",
    "pdf_text": "",
    "emails": [],
    "session_id": None,
    "show_chatbot": False,
    "chat_history": [],
    "processing": False,
    "last_query": "",
    "stats": {"total_queries": 0, "successful_responses": 0}
}

for key, default_value in session_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default_value

# Initialize session_id
if not st.session_state.session_id:
    st.session_state.session_id = str(hash(time.time()))

# Load chat history
if not st.session_state.chat_history:
    st.session_state.chat_history = load_memory(st.session_state.session_id) or []

# Header
st.markdown(
    """
    <div class='header'>
        <h2>🤖 ContextBot</h2>
        <p style="margin-bottom: 0.5rem;">Your Private Context-Locked AI Assistant</p>
        <p style="font-size: 1rem; opacity: 0.7; margin: 0;">Powered by Mixtral-8x7B-Instruct • Secure • Fast • Intelligent</p>
    </div>
    """,
    unsafe_allow_html=True
)

# Main container
st.markdown('<div class="main-container">', unsafe_allow_html=True)

# Statistics bar
if st.session_state.stats["total_queries"] > 0:
    success_rate = (st.session_state.stats["successful_responses"] / st.session_state.stats["total_queries"]) * 100
    st.markdown(
        f"""
        <div style="display: flex; justify-content: center; gap: 2rem; margin-bottom: 2rem; padding: 1rem; background: rgba(38, 166, 154, 0.05); border-radius: 16px; border: 1px solid rgba(38, 166, 154, 0.2);">
            <div style="text-align: center;">
                <div style="font-size: 1.5rem; font-weight: 600; color: #0A2C27;">{st.session_state.stats["total_queries"]}</div>
                <div style="font-size: 0.9rem; opacity: 0.7; color: #1A1A1A;">Total Queries</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 1.5rem; font-weight: 600; color: #4CAF50;">{success_rate:.1f}%</div>
                <div style="font-size: 0.9rem; opacity: 0.7; color: #1A1A1A;">Success Rate</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 1.5rem; font-weight: 600; color: #FF9800;">{len(st.session_state.emails)}</div>
                <div style="font-size: 0.9rem; opacity: 0.7; color: #1A1A1A;">Email Contacts</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# Two-column layout
col1, col2 = st.columns([1.2, 1], gap="large")

# Left column: Training content and email management
with col1:
    # Training content section
    st.markdown(
        '<div class="section-header"><span class="icon">📝</span>Training Content Management</div>',
        unsafe_allow_html=True
    )

    # Content input area
    col_text, col_upload = st.columns([4, 1])
    with col_text:
        training_content = st.text_area(
            "📝 Enter training content for the assistant",
            height=200,
            placeholder="Enter FAQs, knowledge base content, or any training material here...\n\nExample:\nQ: What are your business hours?\nA: We're open Monday-Friday, 9 AM to 6 PM.",
            key="training_content",
            help="This content will be used to train the assistant. Include FAQs, procedures, or any relevant information."
        )

    with col_upload:
        st.markdown("<div style='margin-top: 1.8rem;'>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "📄 Upload PDF",
            type=["pdf"],
            key="pdf_upload",
            label_visibility="collapsed",
            help="Upload a PDF document to extract text content for training"
        )
        if uploaded_file:
            with st.spinner("🔄 Processing PDF..."):
                try:
                    pdf_text = extract_pdf_text(uploaded_file)
                    st.session_state.pdf_text = pdf_text
                    st.success(f"✅ PDF processed successfully! Extracted {len(pdf_text)} characters.")
                    with st.expander("📖 Preview Extracted Text"):
                        st.text_area(
                            "Extracted Content Preview",
                            value=pdf_text[:500] + ("..." if len(pdf_text) > 500 else ""),
                            height=150,
                            disabled=True
                        )
                except Exception as e:
                    st.error(f"❌ Failed to process PDF: {str(e)}")
                    logger.error(f"Error processing PDF: {e}")
        st.markdown("</div>", unsafe_allow_html=True)

    # Save button and status
    col_save, col_status = st.columns([2, 1])
    with col_save:
        save_disabled = not (training_content.strip() or st.session_state.pdf_text)
        if st.button("💾 Save Context", key="save_context", disabled=save_disabled):
            if training_content.strip() or st.session_state.pdf_text:
                try:
                    st.session_state.context = training_content
                    st.session_state.show_chatbot = True
                    st.success("✅ Context saved successfully! Chatbot is now ready.")
                    st.balloons()
                    time.sleep(0.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Failed to save context: {str(e)}")
                    logger.error(f"Error saving context: {e}")
    with col_status:
        if st.session_state.context or st.session_state.pdf_text:
            st.markdown(
                """
                <div style="display: flex; align-items: center; gap: 0.5rem; color: #4CAF50; font-weight: 500; margin-top: 0.5rem;">
                    <span>✅</span>
                    <span>Context Ready</span>
                </div>
                """,
                unsafe_allow_html=True
            )

    # Email management section
    st.markdown('<div class="section-header"><span class="icon">📧</span>Email Notification Center</div>', unsafe_allow_html=True)
    col_email_input, col_email_add = st.columns([3, 1])
    with col_email_input:
        email_input = st.text_input(
            "📧 Email Address",
            placeholder="Enter email for notifications (e.g., user@domain.com)",
            key="email_input",
            help="Add email addresses to receive notifications when the bot is queried"
        )
    with col_email_add:
        st.markdown("<div style='margin-top: 1.8rem;'>", unsafe_allow_html=True)
        if st.button("➕ Add", key="add_email"):
            if email_input and re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email_input):
                if email_input not in st.session_state.emails:
                    st.session_state.emails.append(email_input)
                    st.success(f"✅ Email {email_input} added successfully!")
                    st.rerun()
                else:
                    st.warning("⚠️ Email already registered.")
            elif email_input:
                st.error("❌ Please enter a valid email address.")
            else:
                st.error("❌ Please enter an email address.")
        st.markdown("</div>", unsafe_allow_html=True)

    # Email list
    if st.session_state.emails:
        st.markdown("**📋 Registered Email Addresses:**")
        for i, email in enumerate(st.session_state.emails):
            col_email_display, col_email_remove = st.columns([4, 1])
            with col_email_display:
                st.markdown(f'<div class="email-item">{email}</div>', unsafe_allow_html=True)
            with col_email_remove:
                if st.button("🗑️", key=f"remove_{i}_{email}", help=f"Remove {email}"):
                    st.session_state.emails.remove(email)
                    st.success(f"Email {email} removed.")
                    st.rerun()
    else:
        st.markdown(
            """
            <div style="text-align: center; padding: 2rem; background: rgba(38, 166, 154, 0.05); border: 1px dashed rgba(38, 166, 154, 0.3); border-radius: 12px; margin: 1rem 0;">
                <p style="color: rgba(0, 0, 0, 0.6); margin: 0;">📧 No email addresses registered yet</p>
                <p style="color: rgba(0, 0, 0, 0.4); font-size: 0.9rem; margin: 0;">Add emails to receive notifications</p>
            </div>
            """,
            unsafe_allow_html=True
        )

# Right column: Chatbot Interface
with col2:
    st.markdown(
        '<div class="section-header"><span class="icon">💬</span>AI Chat Interface</div>',
        unsafe_allow_html=True
    )
    context_ready = bool(st.session_state.context or st.session_state.pdf_text)
    status_color = "#4CAF50" if context_ready else "#FF9800"
    status_text = "Ready" if context_ready else "Needs Context"
    status_icon = "🟢" if context_ready else "🟡"
    st.markdown(
        f"""
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 1rem; background: rgba(38, 166, 154, 0.05); border-radius: 12px; margin-bottom: 1rem; border: 1px solid rgba(38, 166, 154, 0.2);">
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <span>{status_icon}</span>
                <span style="font-weight: 500; color: #1A1A1A;">Status: {status_text}</span>
            </div>
            <div style="font-size: 0.9rem; opacity: 0.7; color: #1A1A1A;">
                Context: {len(st.session_state.context) + len(st.session_state.pdf_text)} chars
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if st.button(
        f"🤖 {'Hide' if st.session_state.show_chatbot else 'Open'} Chatbot",
        key="toggle_chatbot",
        disabled=not context_ready,
        help="Open the chat interface to interact with your trained assistant"
    ):
        st.session_state.show_chatbot = not st.session_state.show_chatbot
        st.rerun()

    if st.session_state.show_chatbot and context_ready:
        col_clear, col_export = st.columns(2)
        with col_clear:
            if st.button("🗑️ Clear History", key="clear_chat", help="Delete all chat messages"):
                st.session_state.chat_history = []
                save_memory(st.session_state.session_id, [])
                st.success("Chat history cleared!")
                st.rerun()
        with col_export:
            if st.session_state.chat_history and st.button("📤 Export Chat", key="export_chat"):
                chat_export = "\n\n".join([
                    f"{'You' if chat['type'] == 'user' else 'ContextBot'}: {chat['message']}"
                    for chat in st.session_state.chat_history
                ])
                st.download_button(
                    label="💾 Download",
                    data=chat_export,
                    file_name=f"contextbot_chat_{st.session_state.session_id}.txt",
                    mime="text/plain"
                )

        chat_container = st.container()
        with chat_container:
            if st.session_state.chat_history:
                for i, chat in enumerate(st.session_state.chat_history):
                    msg_type = chat["type"]
                    msg_content = chat["message"]
                    timestamp = chat.get("timestamp", "")
                    st.markdown(
                        f"""
                        <div class="chat-message {'user-message' if msg_type == 'user' else 'bot-message'}" style="animation-delay: {i * 0.1}s;">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
                                <strong style="color: {'#0A2C27' if msg_type == 'user' else '#26A69A'};">
                                    {'👤 You' if msg_type == 'user' else '🤖 ContextBot'}
                                </strong>
                                {f'<span style="font-size: 0.8rem; opacity: 0.6; color: #1A1A1A;">{timestamp}</span>' if timestamp else ''}
                            </div>
                            <div style="line-height: 1.6; color: #1A1A1A;">{msg_content}</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            else:
                st.markdown(
                    """
                    <div style="text-align: center; padding: 3rem; background: rgba(38, 166, 154, 0.05); border: 1px dashed rgba(38, 166, 154, 0.3); border-radius: 16px; margin: 2rem 0;">
                        <div style="font-size: 3rem; margin-bottom: 1rem;">💬</div>
                        <h3 style="color: #0A2C27; margin-bottom: 0.5rem;">Start Your Conversation</h3>
                        <p style="color: rgba(0, 0, 0, 0.6); margin: 0;">Ask me anything about your uploaded content!</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        with st.form(key="chat_form", clear_on_submit=True):
            col_input, col_send = st.columns([4, 1])
            with col_input:
                query = st.text_input(
                    "💭 Your Question",
                    placeholder="Ask me anything about your content...",
                    key="chat_input",
                    label_visibility="collapsed"
                )
            with col_send:
                st.markdown("<div style='margin-top: 1.8rem;'>", unsafe_allow_html=True)
                submit_button = st.form_submit_button("🚀", help="Send message")
                st.markdown("</div>", unsafe_allow_html=True)
            if submit_button and query.strip():
                if query.strip() != st.session_state.last_query:
                    st.session_state.last_query = query.strip()
                    st.session_state.processing = True
                    with st.spinner("🤔 ContextBot is thinking..."):
                        try:
                            st.session_state.stats["total_queries"] += 1
                            response = ask_assistant(
                                query,
                                st.session_state.context,
                                st.session_state.session_id,
                                st.session_state.pdf_text
                            )
                            current_time = time.strftime("%H:%M")
                            st.session_state.chat_history.append({
                                "type": "user",
                                "message": query,
                                "timestamp": current_time
                            })
                            st.session_state.chat_history.append({
                                "type": "bot",
                                "message": response,
                                "timestamp": current_time
                            })
                            save_memory(st.session_state.session_id, st.session_state.chat_history)
                            st.session_state.stats["successful_responses"] += 1
                            if st.session_state.emails:
                                try:
                                    for email in st.session_state.emails:
                                        send_email(email, f"New query: {query}", f"Response: {response}")
                                except Exception as e:
                                    logger.warning(f"Failed to send email notification: {e}")
                            st.session_state.processing = False
                            st.rerun()
                        except Exception as e:
                            st.session_state.processing = False
                            st.error(f"❌ Error: {str(e)}")
                            logger.error(f"Error querying assistant: {e}")
                            st.session_state.chat_history.append({
                                "type": "user",
                                "message": query,
                                "timestamp": time.strftime("%H:%M")
                            })
                            st.session_state.chat_history.append({
                                "type": "bot",
                                "message": f"I apologize, but I encountered an error: {str(e)}",
                                "timestamp": time.strftime("%H:%M")
                            })
                            save_memory(st.session_state.session_id, st.session_state.chat_history)

    elif st.session_state.show_chatbot and not context_ready:
        st.markdown(
            """
            <div style="text-align: center; padding: 3rem; background: rgba(255, 152, 0, 0.1); border: 1px solid rgba(255, 152, 0, 0.3); border-radius: 16px; margin: 2rem 0;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">⚠️</div>
                <h3 style="color: #FF9800; margin-bottom: 0.5rem;">Context Required</h3>
                <p style="color: rgba(0, 0, 0, 0.7); margin: 0;">Please add training content or upload a PDF first to start chatting.</p>
            </div>
            """,
            unsafe_allow_html=True
        )

st.markdown("</div>", unsafe_allow_html=True)

# Footer
st.markdown(
    """
    <div class='footer'>
        <div style="display: flex; justify-content: center; align-items: center; gap: 2rem; flex-wrap: wrap;">
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <span>🤖</span>
                <span>Powered by Mixtral-8x7B-Instruct</span>
            </div>
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <span>🔒</span>
                <span>Private & Secure</span>
            </div>
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <span>⚡</span>
                <span>Real-time Responses</span>
            </div>
        </div>
        <p style="margin-top: 1rem; font-size: 0.9rem; opacity: 0.7;">© 2025 ContextBot - Your Intelligent AI Assistant</p>
    </div>
    """,
    unsafe_allow_html=True
)