from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
import db_service

load_dotenv()

SYSTEM_PROMPT = """You are an e-commerce customer support assistant.
Use the conversation history to understand follow-up questions and references such as 'it', 'that order', or 'the same one'.
When an order ID is available in the current message or recent conversation, use it as needed for order tools.
Only state order details that are supported by tool results. Never invent order statuses or delivery progress.
Never interpret numeric status values as shipping stages. If a status is numeric or unclear, report the raw value and say you cannot determine its meaning.
Do not invent tracking numbers, delivery dates, or phone numbers. Keep responses professional, helpful, and concise.
"""

# Tools
@tool
def get_order_status(order_id: str):
    """Get the current status and details of an order by its order ID."""
    return db_service.get_order_status(order_id)



@tool
def cancel_order(order_id: str):
    """Cancel an order by its order ID, if the database cancellation rules allow it."""
    return db_service.cancel_order(order_id)



tools = {
    get_order_status.name: get_order_status,
    cancel_order.name: cancel_order,
}



model = ChatGroq(model="openai/gpt-oss-20b")
model_tools_binding = model.bind_tools(list(tools.values()))


def _convert_history(chat_history):
    """Convert Streamlit history dictionaries into LangChain messages."""
    converted = []
    for item in (chat_history or [])[-10:]:  # keep only the most recent 10 messages
        role = item.get("role")
        content = item.get("content", "")
        if not content:
            continue
        if role == "user":
            converted.append(HumanMessage(content=content))
        elif role == "assistant":
            converted.append(AIMessage(content=content))
    return converted



def agent(query, chat_history=None):
    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    messages.extend(_convert_history(chat_history))
    messages.append(HumanMessage(content=query))

    result = model_tools_binding.invoke(messages)

    print("\n--- INITIAL AI RESPONSE ---")
    print(result)

    if not result.tool_calls:
        return result.content

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
            return f"Unknown tool: {tool_name}"

        tool_result = selected_tool.invoke(tool_args)
        print("\n--- DATABASE TOOL RESULT ---")
        print(tool_result)
        tools_result.append(f"Tool: {tool_name}\nResult: {tool_result}")

    # Keep the conversation context in the final response-generation call too.
    final_messages = [SystemMessage(content=SYSTEM_PROMPT)]
    final_messages.extend(_convert_history(chat_history))
    final_messages.append(HumanMessage(content=query))
    final_messages.append(HumanMessage(content="Tool results:\n" + "\n\n".join(tools_result)))

    final_result = model.invoke(final_messages)
    print("\n--- FINAL AI RESPONSE ---")
    print(final_result.content)
    return final_result.content
