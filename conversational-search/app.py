# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "gradio",
#     "azure-identity",
#     "openai",
#     "python-dotenv",
#     "requests",
# ]
# ///

import json
import os
from datetime import datetime
from typing import Any, Dict, List

import gradio as gr
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv(override=True)

token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
)

# Initialize Azure OpenAI client with key or identity based auth
if api_key := os.getenv("AZURE_OPENAI_API_KEY"):
    client = AzureOpenAI(
        azure_ad_token_provider=token_provider,
        api_version="2025-02-01-preview",
        api_key=api_key,
    )
else:
    client = AzureOpenAI(
        azure_ad_token_provider=token_provider,
        api_version="2025-02-01-preview",
        azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
    )


# Define system message with instructions and current date/time
def get_system_message():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "role": "system",
        "content": f"""You are a helpful travel assistant for a travel agency, a travel booking service.
            Current date and time: {current_time}

            INSTRUCTIONS:
            - Help users find travel options based on their requirements
            - Extract information like destinations, dates, number of travelers, and trip types
            - If information is missing, politely ask for the necessary details
            - Be friendly, concise, and helpful in your responses
            - Suggest popular destinations if the user is unsure
            - Provide tips relevant to their chosen destination or trip type
            - Remember that all parameters (participants, departure dates, durations, destinations, and trip type) are optional
            - After each user message, extract the parameters and confirm them in a natural way
            - If the user changes a parameter, acknowledge the change in your response
            - If you are unsure about the users language, assume they speak Dutch or English.
            - User will see the available travel options in a separate interface. Never comment on the actual travel options, prices or bookings.
            """,
    }


# Define the travel search parameters extraction function
travel_search_function = {
    "type": "function",
    "function": {
        "name": "extract_travel_search_parameters",
        "description": "Extract travel search parameters from user query for travel booking",
        "parameters": {
            "type": "object",
            "properties": {
                "destination": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of destination countries or locations the user wants to travel to in ISO 3166-1 alpha-2 format.",
                },
                "departure_date": {
                    "type": "string",
                    "description": "The date when the user wants to start their trip (YYYY-MM-DD format)",
                },
                "duration": {
                    "type": "integer",
                    "description": "The number of days for the trip",
                },
                "participants": {
                    "type": "object",
                    "description": "Information about the travel participants",
                    "properties": {
                        "adults": {
                            "type": "integer",
                            "description": "Number of adults (18+ years old)",
                        },
                        "children": {
                            "type": "integer",
                            "description": "Number of children (2-17 years old)",
                        },
                        "infants": {
                            "type": "integer",
                            "description": "Number of infants (0-1 years old)",
                        },
                    },
                },
                "trip_type": {
                    "type": "string",
                    "description": "Type of trip (sun, wintersport, or cruise)",
                    "enum": ["sun", "wintersport", "cruise"],
                },
            },
            "required": [],
        },
    },
}


def format_extracted_parameters(parameters: Dict[str, Any]) -> str:
    """Format the extracted parameters into a readable string."""
    parts = []

    if "destination" in parameters and parameters["destination"]:
        # Handle destination as a list of strings
        if isinstance(parameters["destination"], list):
            destinations = ", ".join(parameters["destination"])
            parts.append(f"🌍 Destination: {destinations}")
        else:
            # For backward compatibility with older data
            parts.append(f"🌍 Destination: {parameters['destination']}")

    if "departure_date" in parameters and parameters["departure_date"]:
        parts.append(f"🗓️ Departure date: {parameters['departure_date']}")

    if "duration" in parameters and parameters["duration"]:
        parts.append(f"⏱️ Duration: {parameters['duration']} days")

    if "participants" in parameters:
        participant_parts = []
        p = parameters["participants"]

        if "adults" in p and p["adults"]:
            participant_parts.append(f"{p['adults']} adult(s)")

        if "children" in p and p["children"]:
            participant_parts.append(f"{p['children']} child(ren)")

        if "infants" in p and p["infants"]:
            participant_parts.append(f"{p['infants']} infant(s)")

        if participant_parts:
            parts.append(f"👨‍👩‍👧‍👦 Participants: {', '.join(participant_parts)}")

    if "trip_type" in parameters and parameters["trip_type"]:
        emoji_map = {"sun": "☀️", "wintersport": "🏂", "cruise": "🚢"}
        trip_type = parameters["trip_type"]
        emoji = emoji_map.get(trip_type, "")
        parts.append(f"{emoji} Trip type: {trip_type}")

    if not parts:
        return "No search parameters have been specified yet."

    return "\n".join(parts)


# Store conversation history and extracted parameters
class ConversationState:
    def __init__(self):
        self.message_history = []
        self.current_parameters = {}
        self.formatted_parameters = "No search parameters have been specified yet."
        self.json_parameters = "{}"

    def reset(self):
        self.message_history = []
        self.current_parameters = {}
        self.formatted_parameters = "No search parameters have been specified yet."
        self.json_parameters = "{}"


conversation_state = ConversationState()


def chat_with_travel_assistant(user_message: str, history: List[List[str]]) -> tuple:
    """Process the user message, update the chat history, and extract parameters."""
    global conversation_state

    if not user_message.strip():
        return (
            "",
            history,
            conversation_state.formatted_parameters,
            conversation_state.json_parameters,
        )

    # Initialize conversation with system message if this is the first message
    if not conversation_state.message_history:
        conversation_state.message_history.append(get_system_message())

    # Add user message to history
    conversation_state.message_history.append({"role": "user", "content": user_message})

    # Get response from OpenAI with function calling - Force function call by setting tool_choice
    response = client.chat.completions.create(
        model=os.environ.get("AZURE_OPENAI_MODEL", "gpt-4o-mini"),
        messages=conversation_state.message_history,
        tools=[travel_search_function],
        tool_choice={
            "type": "function",
            "function": {"name": "extract_travel_search_parameters"},
        },
        temperature=0.2,
    )

    # Extract the response and function calls
    message = response.choices[0].message

    # Add assistant's response to history
    conversation_state.message_history.append(message.model_dump())

    # Extract parameters if function was called
    if message.tool_calls:
        # Find the tool call for parameter extraction
        for tool_call in message.tool_calls:
            if tool_call.function.name == "extract_travel_search_parameters":
                # Extract parameters
                parameters = json.loads(tool_call.function.arguments)

                # Update current parameters, merging with existing ones
                if (
                    "participants" in parameters
                    and "participants" in conversation_state.current_parameters
                ):
                    # Special handling for participants to merge rather than replace
                    for key, value in parameters["participants"].items():
                        if value is not None:
                            conversation_state.current_parameters["participants"][
                                key
                            ] = value

                    # Remove the participants from the new parameters to avoid double processing
                    parameters_without_participants = {
                        k: v for k, v in parameters.items() if k != "participants"
                    }
                    conversation_state.current_parameters.update(
                        {
                            k: v
                            for k, v in parameters_without_participants.items()
                            if v is not None
                        }
                    )
                else:
                    # For the first time or when completely replacing participants
                    if "participants" in parameters:
                        # If participants is in the new parameters but not current, initialize it
                        if "participants" not in conversation_state.current_parameters:
                            conversation_state.current_parameters["participants"] = {}
                        # Update each participant value that is not None
                        for key, value in parameters["participants"].items():
                            if value is not None:
                                conversation_state.current_parameters["participants"][
                                    key
                                ] = value
                        # Remove participants from parameters to avoid double processing
                        parameters = {
                            k: v for k, v in parameters.items() if k != "participants"
                        }

                    # Update other parameters
                    conversation_state.current_parameters.update(
                        {k: v for k, v in parameters.items() if v is not None}
                    )

                # Format parameters for display
                conversation_state.formatted_parameters = format_extracted_parameters(
                    conversation_state.current_parameters
                )
                conversation_state.json_parameters = json.dumps(
                    conversation_state.current_parameters, indent=2
                )

                # Add tool response to history
                conversation_state.message_history.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_call.function.name,
                        "content": conversation_state.formatted_parameters,
                    }
                )

    # Get the final response after function call
    final_response = client.chat.completions.create(
        model=os.environ.get("AZURE_OPENAI_MODEL", "gpt-4o-mini"),
        messages=conversation_state.message_history,
        temperature=0.2,
    )

    assistant_message = final_response.choices[0].message.content
    conversation_state.message_history.append(
        {
            "role": "assistant",
            "content": assistant_message,
        }
    )

    # Update the chat history
    history.append([user_message, assistant_message])

    return (
        "",
        history,
        conversation_state.formatted_parameters,
        conversation_state.json_parameters,
    )


def clear_conversation():
    """Reset the conversation state and clear the interface."""
    global conversation_state
    conversation_state.reset()
    return [], "No search parameters have been specified yet.", "{}"


# Example prompts for the user to start with
sample_prompts = [
    "I want to book a sun vacation to Spain for 2 adults and 1 child, departing on July 15th for 7 days.",
    "Looking for a winter ski holiday in the Swiss Alps this December for a family of 4, preferably for 10 days.",
    "Ik wil graag een cruise boeken naar de Middellandse Zee voor 2 volwassenen in augustus voor 14 dagen.",
    "I need to change my trip - I want to go to Greece instead of Spain.",
    "Can you recommend a good destination for a beach holiday in November?",
]


# Create the Gradio interface - using default theme
with gr.Blocks(title="Travel Assistant") as demo:
    gr.Markdown("""
    # Travel Assistant
    Chat with the travel assistant to find your perfect vacation. The system will extract your travel preferences as you chat.
    """)

    with gr.Row():
        # Left column - Chat interface
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(
                height=500,
                show_copy_button=True,
                render_markdown=True,
                bubble_full_width=False,
                label="Travel Assistant Chat",
                # type="messages",
            )

            with gr.Row():
                user_input = gr.Textbox(
                    placeholder="Ask me about planning your trip...",
                    label=None,
                    show_label=False,
                    lines=2,
                    scale=8,
                )
                submit_button = gr.Button("Send", variant="primary", scale=1)

            with gr.Row():
                clear_button = gr.Button("New Conversation")

            gr.Markdown("### Sample Starting Points")
            sample_prompts_buttons = []
            with gr.Row():
                for i, prompt in enumerate(sample_prompts[:3]):
                    button = gr.Button(f"Example {i + 1}")
                    button.click(lambda p=prompt: p, inputs=[], outputs=[user_input])
                    sample_prompts_buttons.append(button)
            with gr.Row():
                for i, prompt in enumerate(sample_prompts[3:], start=3):
                    button = gr.Button(f"Example {i + 1}")
                    button.click(lambda p=prompt: p, inputs=[], outputs=[user_input])
                    sample_prompts_buttons.append(button)

        # Right column - Extracted parameters
        with gr.Column(scale=2):
            gr.Markdown("### Extracted Parameters")
            extracted_params_output = gr.Textbox(
                label="",
                lines=10,
                value="No search parameters have been specified yet.",
                interactive=False,
            )

            gr.Markdown("### Parameters (JSON)")
            json_output = gr.JSON(value="{}")

    # Set up event handlers
    submit_button.click(
        fn=chat_with_travel_assistant,
        inputs=[user_input, chatbot],
        outputs=[user_input, chatbot, extracted_params_output, json_output],
        queue=True,
    )

    user_input.submit(
        fn=chat_with_travel_assistant,
        inputs=[user_input, chatbot],
        outputs=[user_input, chatbot, extracted_params_output, json_output],
        queue=True,
    )

    clear_button.click(
        fn=clear_conversation,
        inputs=[],
        outputs=[chatbot, extracted_params_output, json_output],
        queue=False,
    )

# Launch the app
if __name__ == "__main__":
    demo.launch()
