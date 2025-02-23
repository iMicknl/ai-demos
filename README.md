# (Gen)AI demos

A collection of (Gen)AI demos, used in various customer presentations, workshop and events.

## Quick Demos

Quick Demos are single-file Python scripts designed to quickly showcase a concept. Each demo includes a brief description and instructions on requirements and execution.

| Demo                                                                 | Description                                                                      |
| -------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| [Image Generation - Azure AI Foundry](/maas-image-generation#readme) | Generate images with Stable Diffusion or Bria AI models via Models as a Service. |


### Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) - an extremely fast package manager for Python

Run a demo with `uv run <script.py>`. This installs dependencies and executes the script automatically.
If you don't wish to use `uv`, you can install the script dependencies with `pip` manually and run the script with `python <script.py>`.

## Complete Solutions

Complete solutions are detailed, multi-file examples that guide you through full scenarios. They are stored in external repositories, ready to be cloned and run with their own instructions and requirements.

| Accelerator                                                                                 | Description                                                                                                                                             |
| ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Azure Genesys Audiohook](https://github.com/iMicknl/azure-genesys-audiohook)               | A reference implementation of a WebSocket server on Azure, designed to integrate with Genesys AudioHooks for real-time transcription and summarization. |
| [Azure Podcast Generator](https://github.com/iMicknl/azure-podcast-generator)               | Generate engaging podcasts based on your document using Azure OpenAI and Azure Speech.                                                                  |
| [Azure Telephony AI Voice Agent](https://github.com/iMicknl/azure-telephony-ai-voice-agent) | AI Voice agent built with Azure Communication Services and GPT-4o-realtime.                                                                             |

## License

MIT