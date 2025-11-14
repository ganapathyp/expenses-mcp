"""Repository layer for expense data operations."""
import logging
from typing import List, Dict, Any, Optional
import sqlite3

from db import get_connection

logger = logging.getLogger(__name__)


def create_expense(category: str, amount: float, description: Optional[str] = None) -> int:
    """
    Create a new expense record.
    
    Args:
        category: Expense category (e.g., 'food', 'transport').
        amount: Expense amount as a float.
        description: Optional description of the expense.
    
    Returns:
        int: The ID of the newly created expense.
    
    Raises:
        sqlite3.Error: If database operation fails.
        ValueError: If amount is negative.
    """
    if amount < 0:
        raise ValueError("Expense amount cannot be negative")
    
    if not category or not category.strip():
        raise ValueError("Category cannot be empty")
    
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO expenses (category, amount, description) VALUES (?, ?, ?)",
            (category.strip(), amount, description.strip() if description else None),
        )
        conn.commit()
        exp_id = cur.lastrowid
        conn.close()
        logger.info(f"Created expense {exp_id}: {category} - ${amount}")
        return exp_id
    except sqlite3.Error as e:
        logger.error(f"Failed to create expense: {e}")
        raise


def list_expenses() -> List[Dict[str, Any]]:
    """
    Retrieve all expenses, ordered by most recent first.
    
    Returns:
        List[Dict[str, Any]]: List of expense dictionaries.
    
    Raises:
        sqlite3.Error: If database operation fails.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM expenses ORDER BY created_at DESC")
        rows = cur.fetchall()
        conn.close()
        expenses = [dict(row) for row in rows]
        logger.debug(f"Retrieved {len(expenses)} expenses")
        return expenses
    except sqlite3.Error as e:
        logger.error(f"Failed to list expenses: {e}")
        raise


def get_expense(expense_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve a specific expense by ID.
    
    Args:
        expense_id: The ID of the expense to retrieve.
    
    Returns:
        Optional[Dict[str, Any]]: Expense dictionary if found, None otherwise.
    
    Raises:
        sqlite3.Error: If database operation fails.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            logger.debug(f"Retrieved expense {expense_id}")
            return dict(row)
        logger.debug(f"Expense {expense_id} not found")
        return None
    except sqlite3.Error as e:
        logger.error(f"Failed to get expense {expense_id}: {e}")
        raise


def update_expense(expense_id: int, **fields: Any) -> bool:
    """
    Update an existing expense by ID.
    
    Args:
        expense_id: The ID of the expense to update.
        **fields: Fields to update (category, amount, description).
    
    Returns:
        bool: True if the expense was updated, False if not found or no changes.
    
    Raises:
        sqlite3.Error: If database operation fails.
        ValueError: If amount is negative.
    """
    if not fields:
        return False
    
    if "amount" in fields and fields["amount"] is not None and fields["amount"] < 0:
        raise ValueError("Expense amount cannot be negative")
    
    if "category" in fields and (not fields["category"] or not fields["category"].strip()):
        raise ValueError("Category cannot be empty")
    
    try:
        # Clean up fields
        cleaned_fields = {}
        for key, value in fields.items():
            if value is not None:
                if key == "category":
                    cleaned_fields[key] = value.strip()
                elif key == "description":
                    cleaned_fields[key] = value.strip() if value else None
                else:
                    cleaned_fields[key] = value
        
        if not cleaned_fields:
            return False
        
        conn = get_connection()
        cur = conn.cursor()
        columns = ", ".join(f"{k}=?" for k in cleaned_fields.keys())
        values = list(cleaned_fields.values()) + [expense_id]
        
        cur.execute(f"UPDATE expenses SET {columns} WHERE id = ?", values)
        conn.commit()
        updated = cur.rowcount > 0
        conn.close()
        
        if updated:
            logger.info(f"Updated expense {expense_id} with fields: {list(cleaned_fields.keys())}")
        else:
            logger.debug(f"Expense {expense_id} not found for update")
        
        return updated
    except sqlite3.Error as e:
        logger.error(f"Failed to update expense {expense_id}: {e}")
        raise


def delete_expense(expense_id: int) -> bool:
    """
    Delete an expense by ID.
    
    Args:
        expense_id: The ID of the expense to delete.
    
    Returns:
        bool: True if the expense was deleted, False if not found.
    
    Raises:
        sqlite3.Error: If database operation fails.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        conn.commit()
        deleted = cur.rowcount > 0
        conn.close()
        
        if deleted:
            logger.info(f"Deleted expense {expense_id}")
        else:
            logger.debug(f"Expense {expense_id} not found for deletion")
        
        return deleted
    except sqlite3.Error as e:
        logger.error(f"Failed to delete expense {expense_id}: {e}")
        raise
