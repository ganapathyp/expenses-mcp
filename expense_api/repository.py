from typing import List, Dict, Any, Optional
from db import get_connection


def create_expense(category: str, amount: float, description: Optional[str] = None) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO expenses (category, amount, description) VALUES (?, ?, ?)",
        (category, amount, description),
    )
    conn.commit()
    exp_id = cur.lastrowid
    conn.close()
    return exp_id


def list_expenses() -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM expenses ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_expense(expense_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def update_expense(expense_id: int, **fields) -> bool:
    if not fields:
        return False

    conn = get_connection()
    cur = conn.cursor()
    columns = ", ".join(f"{k}=?" for k in fields.keys())
    values = list(fields.values()) + [expense_id]

    cur.execute(f"UPDATE expenses SET {columns} WHERE id = ?", values)
    conn.commit()
    updated = cur.rowcount > 0
    conn.close()
    return updated


def delete_expense(expense_id: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted
