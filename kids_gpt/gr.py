import uuid
import gradio as gr
from agent import Agent

# Initialize agent and necessary variables
agent_runnable = Agent()
thread_id = uuid.uuid4()

# Initialize chat history with required format
messages = [{"role": "assistant", "content": "Hello! How can I help you today?"}]


def respond(user_input):
    global messages  # Use the global messages variable
    # Append user message to history
    messages.append({"role": "user", "content": user_input})

    # Assistant's response (dummy response for now)
    response = agent_runnable.run(user_input, thread_id=thread_id)
    ai_message = response["messages"][-1].content

    # Update character_tabs based on the response
    character_tabs = response["characteristics"]

    messages.append({"role": "assistant", "content": ai_message})

    # Format character_tabs as a Markdown string
    character_tabs_markdown = "\n".join(f"- {item}" for item in character_tabs)

    return messages, "", character_tabs_markdown

with gr.Blocks() as demo:
    # Main layout with two columns
    with gr.Row():
        # Left side - Chat Interface
        with gr.Column(scale=3):
            gr.Markdown("# Kids-GPT")
            chatbox = gr.Chatbot(messages, elem_id="chatbot", type="messages")
            user_input = gr.Textbox(
                label="Ask me anything...",
                placeholder="Type your question here and press enter"
            )

            # Placeholder for character tabs
            character_tabs_display = gr.Markdown("### Characteristics")

            user_input.submit(respond, inputs=[user_input], outputs=[chatbox, user_input, character_tabs_display])

# Launch the Gradio app
demo.launch()
