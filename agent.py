from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langchain_core.tools import tool
import db_service

load_dotenv()


## tools
@tool
def get_order_status(order_id:str):
    """Get the current status of the order"""
    return db_service.get_order_status(order_id)

@tool
def cancel_order(order_id:str):
    """Cancel the order"""
    return db_service.cancel_order(order_id)

## tools registry
tools = {
    get_order_status.name : get_order_status,
    cancel_order.name : cancel_order
}

## tools binding

model = ChatGroq( model="openai/gpt-oss-20b")


model_tools_binding = model.bind_tools(
    list(tools.values())
)

def agent(query):

    result = model_tools_binding.invoke(query)

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

        result1 = selected_tool.invoke(tool_args)
    

        print("\n--- DATABASE TOOL RESULT ---")
        print(result1)

        tools_result.append(
            f"Tool: {tool_name}\n"
            f"Result: {result1}"
        )

    prompt = f"""
    Customer question: {query}

    Tool results:
    {chr(10).join(tools_result)}

    IMPORTANT RULES:
- Use only the information returned by the tools.
- Never invent order statuses or delivery progress.
- Never interpret numeric status values as shipping stages.
- If the status is numeric or unclear, report the raw value
  and say you cannot determine its meaning.
- Do not invent tracking numbers, delivery dates, or phone numbers.
- Keep the response professional, helpful, and concise.
    """

    final_result = model.invoke(prompt)

    print("\n--- FINAL AI RESPONSE ---")
    print(final_result.content)

    return final_result.content

