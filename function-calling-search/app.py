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
from typing import Any, Dict

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
                    "description": "The destination countries or locations the user wants to travel to in ISO 3166-1 alpha-2 format. Can be multiple destinations.",
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

# Message history to maintain conversation context
message_history = []


def format_extracted_parameters(parameters: Dict[str, Any]) -> str:
    """Format the extracted parameters into a readable string."""
    parts = []

    if "destination" in parameters and parameters["destination"]:
        if isinstance(parameters["destination"], list):
            destinations = ", ".join(parameters["destination"])
            parts.append(f"🌍 Destinations: {destinations}")
        else:
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
        return "No search parameters were found in your input."

    return "\n".join(parts)


def process_search_query(query: str) -> tuple:
    """Process the search query using Azure OpenAI function calling."""
    global message_history

    # Initialize conversation with system message if this is the first message
    if not message_history:
        message_history.append(get_system_message())

    # Add user message to history
    message_history.append({"role": "user", "content": query})

    # Get response from OpenAI with function calling
    response = client.chat.completions.create(
        model=os.environ.get("AZURE_OPENAI_MODEL", "gpt-4o-mini"),
        messages=message_history,
        tools=[travel_search_function],
        tool_choice={
            "type": "function",
            "function": {"name": "extract_travel_search_parameters"},
        },
        temperature=0,
    )

    # Extract the function call and parameters
    message = response.choices[0].message

    # Add assistant's response to history
    message_history.append(
        {
            "role": "assistant",
            "content": message.content or None,
            "tool_calls": message.tool_calls,
        }
    )

    # Extract and format the parameters
    if message.tool_calls:
        function_call = message.tool_calls[0].function
        tool_call_id = message.tool_calls[0].id
        parameters = json.loads(function_call.arguments)

        # Format the parameters for display
        formatted_parameters = format_extracted_parameters(parameters)

        # Format the raw JSON for display
        json_parameters = json.dumps(parameters, indent=2)

        # Add tool response to history with the corresponding tool_call_id
        message_history.append(
            {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": "extract_travel_search_parameters",
                "content": formatted_parameters,
            }
        )

        return formatted_parameters, json_parameters

    else:
        return ("No parameters could be extracted from your query.", "{}")


def search_interface(query):
    if not query.strip():
        return "", "{}"

    extracted_params, json_params = process_search_query(query)

    return extracted_params, json_params


# Example search queries
def set_example_1():
    return "I want to book a sun vacation to Spain for 2 adults and 1 child, departing on July 15th for 7 days."


def set_example_2():
    return "Looking for a winter ski holiday in the Swiss Alps this December for a family of 4, preferably for 10 days."


def set_example_3():
    return "Ik wil graag een cruise boeken naar de Middellandse Zee voor 2 volwassenen in augustus voor 14 dagen."


# Create the Gradio interface
with gr.Blocks(title="Travel Search") as demo:
    gr.Markdown("""
    # Travel Search
    Enter your travel requirements in natural language. The system will generate a search query for you.
    """)

    with gr.Row():
        search_input = gr.Textbox(
            label="Search",
            placeholder="e.g., I'm looking for a beach holiday to Greece for 2 adults and 1 child in July for 10 days",
            lines=2,
        )

    with gr.Row():
        search_button = gr.Button("Search", variant="primary")

    # Add example buttons in a row with 3 columns
    with gr.Row():
        with gr.Column(scale=1):
            example_1_button = gr.Button("Example 1: Sun vacation", variant="secondary")
        with gr.Column(scale=1):
            example_2_button = gr.Button(
                "Example 2: Winter holiday", variant="secondary"
            )
        with gr.Column(scale=1):
            example_3_button = gr.Button("Example 3: Dutch cruise", variant="secondary")

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### Extracted Parameters")
            extracted_params_output = gr.Textbox(label="", lines=10)

        with gr.Column(scale=1):
            gr.Markdown("### Parameters (JSON)")
            json_output = gr.JSON()

    # Set up click handlers for the search button and input
    search_button.click(
        fn=search_interface,
        inputs=search_input,
        outputs=[extracted_params_output, json_output],
    )

    # Allow Enter key to submit
    search_input.submit(
        fn=search_interface,
        inputs=search_input,
        outputs=[extracted_params_output, json_output],
    )

    # Set up click handlers for example buttons
    example_1_button.click(fn=set_example_1, outputs=search_input)
    example_2_button.click(fn=set_example_2, outputs=search_input)
    example_3_button.click(fn=set_example_3, outputs=search_input)

# Launch the app
if __name__ == "__main__":
    demo.launch()
