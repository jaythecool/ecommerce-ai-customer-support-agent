
import streamlit as st
from agent import agent

# ----------------------------
# Page Configuration
# ----------------------------
st.set_page_config(
    page_title="Order Support AI",
    page_icon="📦",
    layout="centered"
)

# ----------------------------
# Session State
# ----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Hi! 👋 Welcome to Order Support AI. "
                "I can help you check your order status or "
                "assist with cancellations. How can I help?"
            )
        }
    ]

# ----------------------------
# Sidebar
# ----------------------------
with st.sidebar:
    st.title("📦 Order Support AI")

    st.caption("AI-powered customer support")

    st.divider()

    st.markdown("### Available services")

    st.markdown("""
    📦 **Track Order**  
    Check the status of your order.

    ❌ **Cancel Order**  
    Request cancellation of your order.

    💬 **Customer Support**  
    Ask questions in natural language.
    """)

    st.divider()

    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hi! 👋 How can I help you today?"
            }
        ]
        st.rerun()

# ----------------------------
# Header
# ----------------------------
st.title("Customer Support")
st.caption("Your personal order assistance chatbot.")

# ----------------------------
# Display Chat History
# ----------------------------
for message in st.session_state.messages:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ----------------------------
# User Input
# ----------------------------
query = st.chat_input("Ask me about your order...")

if query:

    # Display user message
    st.session_state.messages.append({
        "role": "user",
        "content": query
    })

    with st.chat_message("user"):
        st.markdown(query)

    # Call the imported agent
    with st.chat_message("assistant"):

        with st.spinner("Thinking..."):

            try:
                response = agent(query)

                # Handle AIMessage or plain string responses
                if hasattr(response, "content"):
                    response = response.content

                if not isinstance(response, str):
                    response = str(response)

            except Exception as e:
                response = (
                    "Sorry, something went wrong while processing "
                    "your request. Please try again.\n\n"
                    f"Error: {e}"
                )

        st.markdown(response)

    # Store assistant response
    st.session_state.messages.append({
        "role": "assistant",
        "content": response
    })
