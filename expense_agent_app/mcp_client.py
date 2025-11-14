import pathlib
import os
import requests
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file in project root
# In Docker, environment variables are set by docker-compose, so this is mainly for local development
env_path = pathlib.Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

SYSTEM_PROMPT = (pathlib.Path(__file__).parent / "prompts" / "system_prompt.md").read_text(
    encoding="utf-8"
)

# Initialize OpenAI client with API key from environment
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable is required")

client = OpenAI(api_key=api_key)

# MCP Server base URL (from docker-compose network or localhost)
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://mcp:8000")

# Define OpenAI function tools for the MCP server
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_expense",
            "description": "Add a new expense with category, amount, and optional description",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Expense category, e.g., 'food', 'transport', 'entertainment'"
                    },
                    "amount": {
                        "type": "number",
                        "description": "Expense amount as a number"
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional description of the expense"
                    }
                },
                "required": ["category", "amount"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_expenses",
            "description": "List all expenses, ordered by most recent first",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_expense",
            "description": "Get details for a specific expense by its ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "expense_id": {
                        "type": "integer",
                        "description": "The ID of the expense to retrieve"
                    }
                },
                "required": ["expense_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_expense",
            "description": "Update an existing expense by ID. Only provide fields to update.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "integer",
                        "description": "The ID of the expense to update"
                    },
                    "category": {
                        "type": "string",
                        "description": "New category for the expense"
                    },
                    "amount": {
                        "type": "number",
                        "description": "New amount for the expense"
                    },
                    "description": {
                        "type": "string",
                        "description": "New description for the expense"
                    }
                },
                "required": ["id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_expense",
            "description": "Delete an expense by its ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "integer",
                        "description": "The ID of the expense to delete"
                    }
                },
                "required": ["id"]
            }
        }
    }
]


def call_mcp_tool(function_name: str, arguments: dict) -> str:
    """Call a tool on the MCP server and return the result."""
    try:
        if function_name == "add_expense":
            response = requests.post(
                f"{MCP_SERVER_URL}/tools/add_expense",
                json=arguments,
                timeout=5
            )
            response.raise_for_status()
            result = response.json()
            return f"Expense added successfully with ID: {result.get('id', 'unknown')}"
        
        elif function_name == "list_expenses":
            response = requests.get(
                f"{MCP_SERVER_URL}/tools/list_expenses",
                timeout=5
            )
            response.raise_for_status()
            result = response.json()
            expenses = result.get("expenses", [])
            if not expenses:
                return "No expenses found."
            # Format expenses nicely
            formatted = "Recent expenses:\n"
            for exp in expenses:
                formatted += f"  ID {exp.get('id')}: ${exp.get('amount')} - {exp.get('category')}"
                if exp.get('description'):
                    formatted += f" ({exp.get('description')})"
                formatted += f" - {exp.get('created_at', '')}\n"
            return formatted
        
        elif function_name == "get_expense":
            expense_id = arguments.get("expense_id")
            response = requests.get(
                f"{MCP_SERVER_URL}/tools/get_expense/{expense_id}",
                timeout=5
            )
            response.raise_for_status()
            result = response.json()
            exp = result.get("expense", {})
            return f"Expense ID {exp.get('id')}: ${exp.get('amount')} - {exp.get('category')}" + \
                   (f" ({exp.get('description')})" if exp.get('description') else "") + \
                   f" - Created: {exp.get('created_at', '')}"
        
        elif function_name == "update_expense":
            response = requests.post(
                f"{MCP_SERVER_URL}/tools/update_expense",
                json=arguments,
                timeout=5
            )
            response.raise_for_status()
            return "Expense updated successfully."
        
        elif function_name == "delete_expense":
            response = requests.post(
                f"{MCP_SERVER_URL}/tools/delete_expense",
                json=arguments,
                timeout=5
            )
            response.raise_for_status()
            return "Expense deleted successfully."
        
        else:
            return f"Unknown function: {function_name}"
    
    except requests.exceptions.RequestException as e:
        return f"Error calling MCP server: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"


def ask_agent(message: str) -> str:
    """Send a message to the OpenAI Chat Completions API with MCP tool calling support."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": message}
    ]
    
    max_iterations = 10  # Prevent infinite loops
    iteration = 0
    
    while iteration < max_iterations:
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=TOOLS,
                tool_choice="auto"
            )
            
            message_response = response.choices[0].message
            
            # Add assistant's response to messages
            messages.append({
                "role": "assistant",
                "content": message_response.content,
                "tool_calls": message_response.tool_calls
            })
            
            # If no tool calls, return the final response
            if not message_response.tool_calls:
                return message_response.content or "[No response from model]"
            
            # Handle tool calls
            for tool_call in message_response.tool_calls:
                function_name = tool_call.function.name
                import json
                try:
                    arguments = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    arguments = {}
                
                # Call the MCP tool
                tool_result = call_mcp_tool(function_name, arguments)
                
                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": tool_result
                })
            
            iteration += 1
        
        except Exception as e:
            return f"Error: {str(e)}"
    
    return "Maximum iterations reached. Please try again."
