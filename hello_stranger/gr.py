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

    return messages, "", character_tabs_markdown  # Return the formatted character_tabs string


# Function to compute the image (for demonstration, we'll just return a placeholder URL)
def compute_image():
    # Replace this with actual image computation if available
    computed_image_url = "https://via.placeholder.com/300"  # Placeholder for computed image
    return computed_image_url


with gr.Blocks() as demo:
    # Main layout with two columns
    with gr.Row():
        # Left side - Chat Interface
        with gr.Column(scale=3):
            gr.Markdown("# Hello Stranger")
            chatbox = gr.Chatbot(messages, elem_id="chatbot", type="messages")
            user_input = gr.Textbox(
                label="Ask me anything...",
                placeholder="Type your question here and press enter"
            )

            # Placeholder for character tabs
            character_tabs_display = gr.Markdown("### Items in a list")

            user_input.submit(respond, inputs=[user_input], outputs=[chatbox, user_input, character_tabs_display])

        # Right side - Placeholder image with a button below it
        with gr.Column(scale=1):
            gr.Markdown("### Placeholder for an image")
            image_display = gr.Image("https://via.placeholder.com/150", elem_id="placeholder_image",
                                     label="Image Placeholder")

            # Button to compute the image
            compute_button = gr.Button("Compute Image")
            compute_button.click(compute_image, inputs=None, outputs=image_display)

# Launch the Gradio app
demo.launch()
