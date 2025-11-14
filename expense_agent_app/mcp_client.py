"""MCP Client for Expenses Agent using HTTP transport.

This module provides a clean interface for the Gradio UI to interact with OpenAI's
Chat Completions API, which uses function calling to invoke tools on the Expenses API.
"""
import json
import logging
import pathlib
import os
from typing import Dict, Any, List

import requests
from dotenv import load_dotenv
from openai import OpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file in project root
env_path = pathlib.Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

# Load system prompt
SYSTEM_PROMPT_PATH = pathlib.Path(__file__).parent / "prompts" / "system_prompt.md"
SYSTEM_PROMPT = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable is required")

client = OpenAI(api_key=api_key)

# API configuration
EXPENSES_API_BASE = os.getenv("EXPENSES_API_BASE", "http://api:9000")
REQUEST_TIMEOUT = 10
MAX_ITERATIONS = 10


# Tool definitions for OpenAI function calling
TOOLS: List[Dict[str, Any]] = [
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


def call_expense_tool(function_name: str, arguments: Dict[str, Any]) -> str:
    """
    Call a tool function on the Expenses API.
    
    Args:
        function_name: Name of the function to call.
        arguments: Function arguments.
    
    Returns:
        str: Result message from the tool execution.
    
    Raises:
        requests.exceptions.RequestException: If the API request fails.
    """
    try:
        if function_name == "add_expense":
            response = requests.post(
                f"{EXPENSES_API_BASE}/expenses",
                json=arguments,
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            result = response.json()
            expense_id = result.get("id", "unknown")
            logger.info(f"Added expense {expense_id}")
            return f"Expense added successfully with ID: {expense_id}"
        
        elif function_name == "list_expenses":
            response = requests.get(
                f"{EXPENSES_API_BASE}/expenses",
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            result = response.json()
            expenses = result.get("expenses", [])
            
            if not expenses:
                return "No expenses found."
            
            formatted_lines = ["Recent expenses:"]
            for exp in expenses:
                line = f"  ID {exp.get('id')}: ${exp.get('amount'):.2f} - {exp.get('category')}"
                if exp.get('description'):
                    line += f" ({exp.get('description')})"
                line += f" - {exp.get('created_at', '')}"
                formatted_lines.append(line)
            
            logger.debug(f"Listed {len(expenses)} expenses")
            return "\n".join(formatted_lines)
        
        elif function_name == "get_expense":
            expense_id = arguments.get("expense_id")
            response = requests.get(
                f"{EXPENSES_API_BASE}/expenses/{expense_id}",
                timeout=REQUEST_TIMEOUT
            )
            
            if response.status_code == 404:
                return f"Expense with ID {expense_id} not found."
            
            response.raise_for_status()
            result = response.json()
            exp = result.get("expense", {})
            
            text = f"Expense ID {exp.get('id')}: ${exp.get('amount'):.2f} - {exp.get('category')}"
            if exp.get('description'):
                text += f" ({exp.get('description')})"
            text += f" - Created: {exp.get('created_at', '')}"
            
            logger.debug(f"Retrieved expense {expense_id}")
            return text
        
        elif function_name == "update_expense":
            expense_id = arguments.get("id")
            fields = {k: v for k, v in arguments.items() if k != "id"}
            
            response = requests.put(
                f"{EXPENSES_API_BASE}/expenses/{expense_id}",
                json=fields,
                timeout=REQUEST_TIMEOUT
            )
            
            if response.status_code == 404:
                return f"Expense with ID {expense_id} not found."
            
            response.raise_for_status()
            logger.info(f"Updated expense {expense_id}")
            return "Expense updated successfully."
        
        elif function_name == "delete_expense":
            expense_id = arguments.get("id")
            response = requests.delete(
                f"{EXPENSES_API_BASE}/expenses/{expense_id}",
                timeout=REQUEST_TIMEOUT
            )
            
            if response.status_code == 404:
                return f"Expense with ID {expense_id} not found."
            
            response.raise_for_status()
            logger.info(f"Deleted expense {expense_id}")
            return "Expense deleted successfully."
        
        else:
            logger.warning(f"Unknown function: {function_name}")
            return f"Unknown function: {function_name}"
    
    except requests.exceptions.Timeout:
        error_msg = f"Request to Expenses API timed out for {function_name}"
        logger.error(error_msg)
        return f"Error: {error_msg}"
    except requests.exceptions.ConnectionError:
        error_msg = f"Cannot connect to Expenses API for {function_name}"
        logger.error(error_msg)
        return f"Error: {error_msg}"
    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP error calling {function_name}: {e}"
        logger.error(error_msg)
        return f"Error: {error_msg}"
    except Exception as e:
        error_msg = f"Unexpected error calling {function_name}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {error_msg}"


def ask_agent(message: str) -> str:
    """
    Send a message to the OpenAI Chat Completions API with tool calling support.
    
    This function handles the conversation loop, including tool calls and responses.
    
    Args:
        message: User's message/question.
    
    Returns:
        str: Assistant's response.
    """
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": message}
    ]
    
    iteration = 0
    
    while iteration < MAX_ITERATIONS:
        try:
            # Call OpenAI API
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.7
            )
            
            message_response = response.choices[0].message
            
            # Add assistant's response to conversation
            assistant_message: Dict[str, Any] = {
                "role": "assistant",
                "content": message_response.content
            }
            
            if message_response.tool_calls:
                assistant_message["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in message_response.tool_calls
                ]
            
            messages.append(assistant_message)
            
            # If no tool calls, return the final response
            if not message_response.tool_calls:
                final_content = message_response.content or "[No response from model]"
                logger.debug(f"Final response: {final_content[:100]}...")
                return final_content
            
            # Handle tool calls
            for tool_call in message_response.tool_calls:
                function_name = tool_call.function.name
                
                try:
                    arguments = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse tool arguments: {e}")
                    arguments = {}
                
                logger.info(f"Calling tool: {function_name} with args: {arguments}")
                
                # Call the tool
                tool_result = call_expense_tool(function_name, arguments)
                
                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": tool_result
                })
            
            iteration += 1
        
        except Exception as e:
            error_msg = f"Error in conversation loop: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"I encountered an error: {str(e)}. Please try again."
    
    logger.warning(f"Maximum iterations ({MAX_ITERATIONS}) reached")
    return "I reached the maximum number of iterations. Please try rephrasing your request."
