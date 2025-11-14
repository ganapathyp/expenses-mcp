import gradio as gr
from mcp_client import ask_agent


def chat_fn(message, history):
    """Gradio chat handler."""
    if not message:
        return history, history

    reply = ask_agent(message)
    # Append user message and assistant reply
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": reply})
    return history, history


with gr.Blocks(title="ExpensesMCP Agent") as demo:
    gr.Markdown(
        """# 💸 ExpensesMCP Agent

Chat with your expenses assistant.

Behind the scenes:
- This UI talks to OpenAI's APIs.
- The model uses MCP tools that call an Expenses MCP server.
- The MCP server calls a Python FastAPI expenses service backed by SQLite.
"""
    )

    chatbot = gr.Chatbot(height=480, type="messages")
    msg = gr.Textbox(
        placeholder="e.g., Add a $15 lunch expense in 'food' category",
        label="Your message",
    )

    send_btn = gr.Button("Send")

    msg.submit(chat_fn, [msg, chatbot], [chatbot, chatbot])
    send_btn.click(chat_fn, [msg, chatbot], [chatbot, chatbot])

demo.launch(server_name="0.0.0.0", server_port=7860)
