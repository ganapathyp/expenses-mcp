"""Configuration settings for the Expenses MCP Server."""
import os
import logging

logger = logging.getLogger(__name__)

# Expenses API base URL
EXPENSES_API_BASE = os.getenv("EXPENSES_API_BASE", "http://api:9000")

# Log configuration on import
logger.debug(f"Expenses API base URL: {EXPENSES_API_BASE}")
