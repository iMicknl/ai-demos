# Conversational Search

A simple demonstration of how function calling can extract parameters to search for destinations in a travel agency scenario, in a chat scenario.

## Prerequisites

- See [prerequisites to run samples, in the root README](../README.md).
- Azure OpenAI, with gpt-4o-mini or gpt-4o model deployed.

## Getting Started

1. Navigate to the `function-calling-search` directory (if you haven't already).
2. Copy the `.env.sample` file to `.env`.
3. Update the `.env` file with your Azure OpenAI model URL and (optionally) your key.
    - To use identity-based authentication, log in with `az login` and select your subscription. Ensure your user has the 'OpenAI Contributor' role assigned.
4. Run the sample with `uv run app.py`. This will install all dependencies and start a web server at http://localhost:7860.
