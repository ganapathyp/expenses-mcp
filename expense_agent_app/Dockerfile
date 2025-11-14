FROM python:3.11-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy and install agent app requirements
COPY expense_agent_app/requirements.txt ./expense_agent_app/
RUN uv pip install --system --no-cache -r expense_agent_app/requirements.txt

# Copy agent app code
COPY expense_agent_app/ ./expense_agent_app/

WORKDIR /app/expense_agent_app

EXPOSE 7860

CMD ["python", "client.py"]
