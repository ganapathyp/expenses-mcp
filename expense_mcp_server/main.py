from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import requests

from config import EXPENSES_API_BASE


app = FastAPI(
    title="Expenses MCP Server",
    description="HTTP tool proxy to the Expenses API service",
    version="0.1.0",
)


class AddExpenseInput(BaseModel):
    category: str = Field(..., description="Expense category, e.g. 'food'")
    amount: float = Field(..., description="Expense amount")
    description: Optional[str] = Field(None, description="Description of the expense")


class UpdateExpenseInput(BaseModel):
    id: int = Field(..., description="ID of the expense to update")
    category: Optional[str] = None
    amount: Optional[float] = None
    description: Optional[str] = None


class DeleteExpenseInput(BaseModel):
    id: int = Field(..., description="ID of the expense to delete")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "service": "expenses-mcp", "api_base": EXPENSES_API_BASE}


@app.post("/tools/add_expense")
def tool_add_expense(payload: AddExpenseInput) -> Dict[str, Any]:
    r = requests.post(
        f"{EXPENSES_API_BASE}/expenses",
        json=payload.dict(),
        timeout=5,
    )
    r.raise_for_status()
    return r.json()


@app.get("/tools/list_expenses")
def tool_list_expenses() -> Dict[str, Any]:
    r = requests.get(f"{EXPENSES_API_BASE}/expenses", timeout=5)
    r.raise_for_status()
    return r.json()


@app.get("/tools/get_expense/{expense_id}")
def tool_get_expense(expense_id: int) -> Dict[str, Any]:
    r = requests.get(f"{EXPENSES_API_BASE}/expenses/{expense_id}", timeout=5)
    if r.status_code == 404:
        raise HTTPException(status_code=404, detail="Expense not found")
    r.raise_for_status()
    return r.json()


@app.post("/tools/update_expense")
def tool_update_expense(payload: UpdateExpenseInput) -> Dict[str, Any]:
    fields = payload.dict(exclude_unset=True)
    expense_id = fields.pop("id")
    r = requests.put(
        f"{EXPENSES_API_BASE}/expenses/{expense_id}",
        json=fields,
        timeout=5,
    )
    if r.status_code == 404:
        raise HTTPException(status_code=404, detail="Expense not found")
    r.raise_for_status()
    return r.json()


@app.post("/tools/delete_expense")
def tool_delete_expense(payload: DeleteExpenseInput) -> Dict[str, Any]:
    r = requests.delete(
        f"{EXPENSES_API_BASE}/expenses/{payload.id}",
        timeout=5,
    )
    if r.status_code == 404:
        raise HTTPException(status_code=404, detail="Expense not found")
    r.raise_for_status()
    return r.json()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
