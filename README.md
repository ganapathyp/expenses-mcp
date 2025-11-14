# ExpensesMCP (Multi-Container + Gradio UI, expense_ folders)

This repo contains a 3-service setup:

- `expense_api`          – FastAPI + SQLite expenses REST API
- `expense_mcp_server`   – MCP-style HTTP tool proxy to the API
- `expense_agent_app`    – Gradio UI + OpenAI SDK agent

Use `docker-compose.yml` to bring everything up.

```bash
export OPENAI_API_KEY=sk-...
docker compose up --build
```

Then visit:

- API:   http://localhost:9000/docs
- MCP:   http://localhost:8000/docs
- Agent: http://localhost:7860
