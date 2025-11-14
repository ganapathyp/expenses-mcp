from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from db import init_db
from repository import (
    create_expense,
    list_expenses,
    get_expense,
    update_expense,
    delete_expense,
)


class ExpenseIn(BaseModel):
    category: str = Field(..., description="Expense category, e.g., 'food'")
    amount: float = Field(..., description="Expense amount")
    description: Optional[str] = Field(None, description="Description of the expense")


class ExpenseUpdate(BaseModel):
    category: Optional[str] = None
    amount: Optional[float] = None
    description: Optional[str] = None


app = FastAPI(title="Expenses API", version="0.1.0")


@app.on_event("startup")
def startup_event():
    init_db()


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "service": "expenses-api"}


@app.post("/expenses")
def add_expense(exp: ExpenseIn) -> Dict[str, Any]:
    new_id = create_expense(exp.category, exp.amount, exp.description)
    return {"id": new_id}


@app.get("/expenses")
def get_expenses() -> Dict[str, List[Dict[str, Any]]]:
    rows = list_expenses()
    return {"expenses": rows}


@app.get("/expenses/{expense_id}")
def get_expense_by_id(expense_id: int) -> Dict[str, Any]:
    exp = get_expense(expense_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Expense not found")
    return {"expense": exp}


@app.put("/expenses/{expense_id}")
def update_expense_by_id(expense_id: int, payload: ExpenseUpdate) -> Dict[str, Any]:
    fields = payload.dict(exclude_unset=True)
    ok = update_expense(expense_id, **fields)
    if not ok:
        raise HTTPException(status_code=404, detail="Expense not found or no changes")
    return {"success": True}


@app.delete("/expenses/{expense_id}")
def delete_expense_by_id(expense_id: int) -> Dict[str, Any]:
    ok = delete_expense(expense_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Expense not found")
    return {"success": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=9000)
