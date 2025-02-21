# Image Generation - Azure AI Foundry

This sample demonstrates how to use image generation models from Azure AI Foundry via Models as a Service (serverless APIs). This sample supports models from Stability AI and Bria AI and will adapt the configuration based on the model's capabilities.

## Prerequisites

- See [prerequisites to run samples, in the root README](../README.md).
- Azure AI Foundry, with rights to deploy models and access to the model APIs.

## Getting Started

1. Deploy your [image generation models on Azure AI Foundry](https://learn.microsoft.com/en-us/azure/ai-studio/how-to/deploy-models-serverless?tabs=azure-ai-studio). See [Region availabilty for models in serverless API](https://learn.microsoft.com/en-us/azure/ai-studio/how-to/deploy-models-serverless-availability).
1. Copy .env.sample to .env
1. Update the .env file with your Azure AI Foundry model urls and keys. You only have to update the values for the models you want to use.
1. Run sample with `uv run app.py`. This will install all dependencies and start a web server at http://localhost:7860.