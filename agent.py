
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from dotenv import load_dotenv

import os
import streamlit as st
import db_service


# =========================================================
# CONFIGURATION
# =========================================================

load_dotenv()

SYSTEM_PROMPT = """
You are an e-commerce customer support assistant.

Your responsibilities:
- Help customers check order status.
- Help customers cancel orders when cancellation is allowed.
- Understand conversational follow-ups such as "it", "that order",
  "cancel it", and "what about that one".
- Use the conversation history to resolve references to order IDs.

Rules:
- Only report order information supported by database tool results.
- Never invent order statuses, delivery progress, tracking numbers,
  delivery dates, or phone numbers.
- Never interpret numeric or unclear statuses as shipping stages.
- If an order cannot be found, clearly inform the customer.
- If an order is already canceled, say so.
- If an order is delivered and cannot be canceled, explain that.
- Be professional, helpful, and concise.
"""


# =========================================================
# API KEY CONFIGURATION
# Supports local .env and Streamlit Cloud secrets
# =========================================================

groq_api_key = os.getenv("GROQ_API_KEY")

if not groq_api_key:
    try:
        groq_api_key = st.secrets.get("GROQ_API_KEY")
    except Exception:
        groq_api_key = None

if not groq_api_key:
    raise ValueError(
        "GROQ_API_KEY is missing. Configure it in your .env "
        "file or Streamlit Cloud Secrets."
    )


# =========================================================
# LLM
# =========================================================

model = ChatGroq(
    model="openai/gpt-oss-20b",
    api_key=groq_api_key,
)

# =========================================================
# TOOLS
# =========================================================

@tool
def get_order_status(order_id: str):
    """Retrieve the current status and details of an order using its order ID."""
    return db_service.get_order_status(order_id)


@tool
def cancel_order(order_id: str):
    """Cancel an order if it exists and cancellation is allowed."""
    return db_service.cancel_order(order_id)


tools = {
    get_order_status.name: get_order_status,
    cancel_order.name: cancel_order,
}

# Bind tools to the model for the tool-selection call.
model_with_tools = model.bind_tools(list(tools.values()))


# =========================================================
# CONVERSATION HISTORY
# =========================================================

def _convert_history(chat_history):
    """Convert Streamlit chat history into LangChain messages."""

    converted = []

    for item in (chat_history or [])[-10:]:
        role = item.get("role")
        content = item.get("content", "")

        if not content:
            continue

        if role == "user":
            converted.append(HumanMessage(content=str(content)))

        elif role == "assistant":
            converted.append(AIMessage(content=str(content)))

    return converted


# =========================================================
# AGENT
# =========================================================

def agent(query, chat_history=None):

    # Build conversation context
    messages = [
        SystemMessage(content=SYSTEM_PROMPT)
    ]

    messages.extend(_convert_history(chat_history))
    messages.append(HumanMessage(content=query))

    # -----------------------------------------------------
    # 1. Ask the model whether a tool is required
    # -----------------------------------------------------

    try:
        result = model_with_tools.invoke(messages)

    except Exception as e:
        print("--- INITIAL MODEL ERROR ---")
        print(e)
        return "I'm sorry, I'm unable to process your request right now. Please try again."

    print("\n--- INITIAL AI RESPONSE ---")
    print(result)

    # If the model does not request a tool, return its response.
    if not result.tool_calls:
        return result.content or "How can I help you with your order?"

    # -----------------------------------------------------
    # 2. Execute requested tools
    # -----------------------------------------------------

    tools_result = []

    for tool_call in result.tool_calls:

        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        print("\n--- TOOL SELECTED ---")
        print(tool_name)

        print("\n--- TOOL ARGUMENTS ---")
        print(tool_args)

        selected_tool = tools.get(tool_name)

        if selected_tool is None:
            return "I'm sorry, I couldn't process that action."

        try:
            tool_result = selected_tool.invoke(tool_args)

        except Exception as e:
            print("--- TOOL EXECUTION ERROR ---")
            print(e)
            return "I encountered an issue while accessing your order. Please try again."

        print("\n--- DATABASE TOOL RESULT ---")
        print(tool_result)

        tools_result.append(
            f"Tool: {tool_name}\nResult: {tool_result}"
        )

    # -----------------------------------------------------
    # 3. Generate final response WITHOUT tools
    # -----------------------------------------------------

    final_prompt = f"""
{SYSTEM_PROMPT}

Conversation history:
{_convert_history(chat_history)}

Customer's latest message:
{query}

Database/tool results:
{chr(10).join(tools_result)}

Instructions:
- Respond to the customer's latest message.
- Use only the database/tool results above for order-related facts.
- Do not call tools or initiate additional actions.
- Do not claim an action succeeded unless the tool result confirms it.
- If cancellation was successful, clearly confirm the cancellation.
- If cancellation failed or the order was already canceled, explain the actual result.
- Be natural, professional, and concise.
"""

    try:
        # IMPORTANT:
        # This is the plain model, NOT the tool-bound model.
        # It cannot execute our registered tools in this final stage.
        final_result = model.invoke(final_prompt)

        print("\n--- FINAL AI RESPONSE ---")
        print(final_result.content)

        return final_result.content or "Your request has been processed."

    except Exception as e:
        print("--- FINAL RESPONSE ERROR ---")
        print(e)

        # Fallback: return the actual tool result rather than
        # incorrectly claiming the action failed.
        return "\n\n".join(tools_result)
