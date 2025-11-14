"""Gradio UI for the Expenses Agent application.

This module provides a web-based chat interface for interacting with the
expenses management agent powered by OpenAI's GPT models.
"""
import logging
import gradio as gr
from mcp_client import ask_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def chat_handler(message: str, history: list) -> tuple[list, list]:
    """
    Handle chat messages from the user.
    
    Args:
        message: User's message.
        history: Conversation history.
    
    Returns:
        tuple[list, list]: Updated history (for both chatbot components).
    """
    if not message or not message.strip():
        return history, history
    
    try:
        # Get response from agent
        reply = ask_agent(message.strip())
        
        # Append user message and assistant reply
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": reply})
        
        logger.debug(f"User message: {message[:50]}... | Response length: {len(reply)}")
        
    except Exception as e:
        error_msg = f"I encountered an error: {str(e)}. Please try again."
        logger.error(f"Error in chat handler: {e}", exc_info=True)
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": error_msg})
    
    return history, history


def create_ui() -> gr.Blocks:
    """
    Create and configure the Gradio UI.
    
    Returns:
        gr.Blocks: Configured Gradio interface.
    """
    with gr.Blocks(
        title="ExpensesMCP Agent",
        theme=gr.themes.Soft(),
        css="""
        .gradio-container {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .main-header {
            text-align: center;
            padding: 20px;
        }
        """
    ) as demo:
        gr.Markdown(
            """
            # 💸 ExpensesMCP Agent
            
            Chat with your intelligent expenses assistant powered by OpenAI GPT-4o-mini.
            
            **Capabilities:**
            - ➕ Add new expenses with category, amount, and description
            - 📋 List all your expenses
            - 🔍 Get details for a specific expense
            - ✏️ Update existing expenses
            - 🗑️ Delete expenses
            
            **How it works:**
            - This UI communicates with OpenAI's Chat Completions API
            - The model uses function calling to invoke tools on the Expenses API
            - All expenses are stored in a SQLite database
            
            **Try asking:**
            - "Add a $15 lunch expense in the food category"
            - "Show me all my expenses"
            - "What's my total spending on food?"
            """,
            elem_classes=["main-header"]
        )
        
        chatbot = gr.Chatbot(
            height=500,
            type="messages",
            label="Conversation",
            show_copy_button=True,
            avatar_images=(None, "🤖")
        )
        
        with gr.Row():
            msg = gr.Textbox(
                placeholder="e.g., Add a $15 lunch expense in 'food' category",
                label="Your message",
                scale=4,
                show_label=False
            )
            send_btn = gr.Button("Send", variant="primary", scale=1)
        
        gr.Examples(
            examples=[
                "Add a $15 lunch expense in the food category",
                "List all my expenses",
                "Show me expenses from the food category",
                "What's my total spending?",
            ],
            inputs=msg
        )
        
        # Event handlers
        def respond_and_clear(message, history):
            """Handle message submission and clear input."""
            if message:
                new_history, _ = chat_handler(message, history)
                return "", new_history, new_history
            return "", history, history
        
        msg.submit(respond_and_clear, [msg, chatbot], [msg, chatbot, chatbot])
        send_btn.click(respond_and_clear, [msg, chatbot], [msg, chatbot, chatbot])
    
    return demo


if __name__ == "__main__":
    logger.info("Starting ExpensesMCP Agent UI...")
    demo = create_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )
