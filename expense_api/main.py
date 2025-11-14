"""FastAPI application for the Expenses API service."""
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, List

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from db import init_db
from repository import (
    create_expense,
    list_expenses,
    get_expense,
    update_expense,
    delete_expense,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ExpenseIn(BaseModel):
    """Request model for creating a new expense."""
    category: str = Field(..., min_length=1, description="Expense category, e.g., 'food', 'transport'")
    amount: float = Field(..., gt=0, description="Expense amount (must be positive)")
    description: str | None = Field(None, description="Optional description of the expense")
    
    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Validate and normalize category."""
        if not v or not v.strip():
            raise ValueError("Category cannot be empty")
        return v.strip()


class ExpenseUpdate(BaseModel):
    """Request model for updating an existing expense."""
    category: str | None = Field(None, min_length=1, description="New category for the expense")
    amount: float | None = Field(None, gt=0, description="New amount for the expense")
    description: str | None = Field(None, description="New description for the expense")
    
    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str | None) -> str | None:
        """Validate and normalize category if provided."""
        if v is not None and (not v or not v.strip()):
            raise ValueError("Category cannot be empty")
        return v.strip() if v else None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("Initializing Expenses API...")
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Expenses API...")


app = FastAPI(
    title="Expenses API",
    description="RESTful API for managing personal expenses with SQLite backend",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint.
    
    Returns:
        Dict[str, str]: Service status information.
    """
    return {
        "status": "healthy",
        "service": "expenses-api",
        "version": "1.0.0"
    }


@app.post("/expenses", status_code=status.HTTP_201_CREATED, tags=["Expenses"])
async def add_expense(expense: ExpenseIn) -> Dict[str, Any]:
    """
    Create a new expense.
    
    Args:
        expense: Expense data to create.
    
    Returns:
        Dict[str, Any]: Created expense ID.
    
    Raises:
        HTTPException: If expense creation fails.
    """
    try:
        expense_id = create_expense(
            category=expense.category,
            amount=expense.amount,
            description=expense.description
        )
        return {
            "id": expense_id,
            "message": "Expense created successfully"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error creating expense: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create expense"
        )


@app.get("/expenses", tags=["Expenses"])
async def get_expenses() -> Dict[str, List[Dict[str, Any]]]:
    """
    Retrieve all expenses, ordered by most recent first.
    
    Returns:
        Dict[str, List[Dict[str, Any]]]: Dictionary containing list of expenses.
    """
    try:
        expenses = list_expenses()
        return {"expenses": expenses, "count": len(expenses)}
    except Exception as e:
        logger.error(f"Unexpected error listing expenses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve expenses"
        )


@app.get("/expenses/{expense_id}", tags=["Expenses"])
async def get_expense_by_id(expense_id: int) -> Dict[str, Any]:
    """
    Retrieve a specific expense by ID.
    
    Args:
        expense_id: The ID of the expense to retrieve.
    
    Returns:
        Dict[str, Any]: Expense data.
    
    Raises:
        HTTPException: If expense is not found.
    """
    try:
        expense = get_expense(expense_id)
        if not expense:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Expense with ID {expense_id} not found"
            )
        return {"expense": expense}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving expense {expense_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve expense"
        )


@app.put("/expenses/{expense_id}", tags=["Expenses"])
async def update_expense_by_id(
    expense_id: int,
    payload: ExpenseUpdate
) -> Dict[str, Any]:
    """
    Update an existing expense by ID.
    
    Args:
        expense_id: The ID of the expense to update.
        payload: Fields to update.
    
    Returns:
        Dict[str, Any]: Success confirmation.
    
    Raises:
        HTTPException: If expense is not found or update fails.
    """
    try:
        fields = payload.model_dump(exclude_unset=True)
        if not fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided for update"
            )
        
        updated = update_expense(expense_id, **fields)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Expense with ID {expense_id} not found"
            )
        
        return {
            "success": True,
            "message": "Expense updated successfully"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error updating expense {expense_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update expense"
        )


@app.delete("/expenses/{expense_id}", tags=["Expenses"])
async def delete_expense_by_id(expense_id: int) -> Dict[str, Any]:
    """
    Delete an expense by ID.
    
    Args:
        expense_id: The ID of the expense to delete.
    
    Returns:
        Dict[str, Any]: Success confirmation.
    
    Raises:
        HTTPException: If expense is not found.
    """
    try:
        deleted = delete_expense(expense_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Expense with ID {expense_id} not found"
            )
        
        return {
            "success": True,
            "message": "Expense deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error deleting expense {expense_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete expense"
        )


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
        port=9000,
        log_level="info"
    )
