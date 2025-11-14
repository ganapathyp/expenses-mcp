"""HTTP-based MCP Server for Expenses Management.

This service acts as a tool proxy, translating MCP tool calls into HTTP requests
to the Expenses API service. It provides a clean interface for AI agents to interact
with the expense management system.
"""
import logging
from typing import Dict, Any, List
import requests
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from config import EXPENSES_API_BASE

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Request timeout in seconds
REQUEST_TIMEOUT = 10

app = FastAPI(
    title="Expenses MCP Server",
    description="HTTP tool proxy for the Expenses API service",
    version="1.0.0",
)


class ToolRequest(BaseModel):
    """Request model for tool execution."""
    name: str = Field(..., description="Name of the tool to execute")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


class ToolResponse(BaseModel):
    """Response model for tool execution."""
    success: bool
    result: str
    data: Dict[str, Any] | None = None


def call_expenses_api(
    method: str,
    endpoint: str,
    json_data: Dict[str, Any] | None = None,
    params: Dict[str, Any] | None = None
) -> requests.Response:
    """
    Make an HTTP request to the Expenses API.
    
    Args:
        method: HTTP method (GET, POST, PUT, DELETE).
        endpoint: API endpoint path.
        json_data: Optional JSON payload for POST/PUT requests.
        params: Optional query parameters.
    
    Returns:
        requests.Response: The HTTP response.
    
    Raises:
        requests.exceptions.RequestException: If the request fails.
    """
    url = f"{EXPENSES_API_BASE.rstrip('/')}/{endpoint.lstrip('/')}"
    
    try:
        response = requests.request(
            method=method,
            url=url,
            json=json_data,
            params=params,
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return response
    except requests.exceptions.Timeout:
        logger.error(f"Request timeout: {method} {url}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Expenses API request timed out"
        )
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error: {method} {url}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cannot connect to Expenses API"
        )
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error: {method} {url} - {e}")
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resource not found"
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Expenses API error: {str(e)}"
        )


@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint.
    
    Returns:
        Dict[str, str]: Service status information.
    """
    # Check connectivity to Expenses API
    try:
        response = requests.get(
            f"{EXPENSES_API_BASE}/health",
            timeout=5
        )
        api_status = "connected" if response.status_code == 200 else "disconnected"
    except Exception:
        api_status = "disconnected"
    
    return {
        "status": "healthy",
        "service": "expenses-mcp-server",
        "version": "1.0.0",
        "expenses_api": api_status
    }


@app.post("/tools/add_expense", tags=["Tools"])
async def add_expense_tool(request: ToolRequest) -> ToolResponse:
    """
    Add a new expense.
    
    Args:
        request: Tool request with expense data.
    
    Returns:
        ToolResponse: Result of the operation.
    """
    if request.name != "add_expense":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tool name mismatch: expected 'add_expense', got '{request.name}'"
        )
    
    try:
        response = call_expenses_api("POST", "/expenses", json_data=request.arguments)
        result_data = response.json()
        expense_id = result_data.get("id")
        
        logger.info(f"Added expense {expense_id}")
        return ToolResponse(
            success=True,
            result=f"Expense added successfully with ID: {expense_id}",
            data=result_data
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding expense: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add expense: {str(e)}"
        )


@app.post("/tools/list_expenses", tags=["Tools"])
async def list_expenses_tool(request: ToolRequest) -> ToolResponse:
    """
    List all expenses.
    
    Args:
        request: Tool request (no arguments needed).
    
    Returns:
        ToolResponse: List of expenses.
    """
    if request.name != "list_expenses":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tool name mismatch: expected 'list_expenses', got '{request.name}'"
        )
    
    try:
        response = call_expenses_api("GET", "/expenses")
        result_data = response.json()
        expenses = result_data.get("expenses", [])
        
        if not expenses:
            return ToolResponse(
                success=True,
                result="No expenses found.",
                data=result_data
            )
        
        # Format expenses for display
        formatted_lines = ["Recent expenses:"]
        for exp in expenses:
            line = f"  ID {exp.get('id')}: ${exp.get('amount'):.2f} - {exp.get('category')}"
            if exp.get('description'):
                line += f" ({exp.get('description')})"
            line += f" - {exp.get('created_at', '')}"
            formatted_lines.append(line)
        
        result_text = "\n".join(formatted_lines)
        logger.debug(f"Listed {len(expenses)} expenses")
        
        return ToolResponse(
            success=True,
            result=result_text,
            data=result_data
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing expenses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list expenses: {str(e)}"
        )


@app.post("/tools/get_expense", tags=["Tools"])
async def get_expense_tool(request: ToolRequest) -> ToolResponse:
    """
    Get a specific expense by ID.
    
    Args:
        request: Tool request with expense_id.
    
    Returns:
        ToolResponse: Expense details.
    """
    if request.name != "get_expense":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tool name mismatch: expected 'get_expense', got '{request.name}'"
        )
    
    expense_id = request.arguments.get("expense_id")
    if not expense_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required argument: expense_id"
        )
    
    try:
        response = call_expenses_api("GET", f"/expenses/{expense_id}")
        result_data = response.json()
        exp = result_data.get("expense", {})
        
        # Format expense for display
        text = f"Expense ID {exp.get('id')}: ${exp.get('amount'):.2f} - {exp.get('category')}"
        if exp.get('description'):
            text += f" ({exp.get('description')})"
        text += f" - Created: {exp.get('created_at', '')}"
        
        logger.debug(f"Retrieved expense {expense_id}")
        return ToolResponse(
            success=True,
            result=text,
            data=result_data
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting expense {expense_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get expense: {str(e)}"
        )


@app.post("/tools/update_expense", tags=["Tools"])
async def update_expense_tool(request: ToolRequest) -> ToolResponse:
    """
    Update an existing expense.
    
    Args:
        request: Tool request with expense ID and fields to update.
    
    Returns:
        ToolResponse: Result of the operation.
    """
    if request.name != "update_expense":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tool name mismatch: expected 'update_expense', got '{request.name}'"
        )
    
    expense_id = request.arguments.get("id")
    if not expense_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required argument: id"
        )
    
    # Extract fields to update (exclude 'id')
    fields = {k: v for k, v in request.arguments.items() if k != "id"}
    if not fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update"
        )
    
    try:
        response = call_expenses_api("PUT", f"/expenses/{expense_id}", json_data=fields)
        result_data = response.json()
        
        logger.info(f"Updated expense {expense_id} with fields: {list(fields.keys())}")
        return ToolResponse(
            success=True,
            result="Expense updated successfully.",
            data=result_data
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating expense {expense_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update expense: {str(e)}"
        )


@app.post("/tools/delete_expense", tags=["Tools"])
async def delete_expense_tool(request: ToolRequest) -> ToolResponse:
    """
    Delete an expense by ID.
    
    Args:
        request: Tool request with expense ID.
    
    Returns:
        ToolResponse: Result of the operation.
    """
    if request.name != "delete_expense":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tool name mismatch: expected 'delete_expense', got '{request.name}'"
        )
    
    expense_id = request.arguments.get("id")
    if not expense_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required argument: id"
        )
    
    try:
        response = call_expenses_api("DELETE", f"/expenses/{expense_id}")
        result_data = response.json()
        
        logger.info(f"Deleted expense {expense_id}")
        return ToolResponse(
            success=True,
            result="Expense deleted successfully.",
            data=result_data
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting expense {expense_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete expense: {str(e)}"
        )


@app.get("/tools", tags=["Tools"])
async def list_tools() -> Dict[str, List[Dict[str, Any]]]:
    """
    List all available tools.
    
    Returns:
        Dict[str, List[Dict[str, Any]]]: Available tools with their schemas.
    """
    tools = [
        {
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
        },
        {
            "name": "list_expenses",
            "description": "List all expenses, ordered by most recent first",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        },
        {
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
        },
        {
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
        },
        {
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
    ]
    
    return {"tools": tools, "count": len(tools)}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
