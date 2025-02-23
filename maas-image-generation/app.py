# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "gradio",
#     "pillow",
#     "python-dotenv",
#     "requests",
# ]
# ///

from __future__ import annotations

import base64
import json
import logging
import os
from io import BytesIO

import gradio as gr
import requests
from dotenv import load_dotenv
from PIL import Image

logger = logging.getLogger(__name__)
load_dotenv(override=True)
logging.basicConfig(level=logging.INFO)

MODEL_CONFIGS = {}

# Add Stable Diffusion 3.5 if both endpoint and key are provided
if os.getenv("STABLE_DIFFUSION_35_ENDPOINT") and os.getenv("STABLE_DIFFUSION_35_KEY"):
    MODEL_CONFIGS["Stable Diffusion 3.5"] = {
        "endpoint": os.getenv("STABLE_DIFFUSION_35_ENDPOINT"),
        "key": os.getenv("STABLE_DIFFUSION_35_KEY"),
        "provider": "Stability AI",
    }

# Add Stable Image Core if both endpoint and key are provided
if os.getenv("STABLE_IMAGE_CORE_ENDPOINT") and os.getenv("STABLE_IMAGE_CORE_KEY"):
    MODEL_CONFIGS["Stable Image Core"] = {
        "endpoint": os.getenv("STABLE_IMAGE_CORE_ENDPOINT"),
        "key": os.getenv("STABLE_IMAGE_CORE_KEY"),
        "provider": "Stability AI",
    }

# Add Stable Image Ultra if both endpoint and key are provided
if os.getenv("STABLE_IMAGE_ULTRA_ENDPOINT") and os.getenv("STABLE_IMAGE_ULTRA_KEY"):
    MODEL_CONFIGS["Stable Image Ultra"] = {
        "endpoint": os.getenv("STABLE_IMAGE_ULTRA_ENDPOINT"),
        "key": os.getenv("STABLE_IMAGE_ULTRA_KEY"),
        "provider": "Stability AI",
    }

# Add Bria 2.3 Fast if both endpoint and key are provided
if os.getenv("BRIA_23_FAST_ENDPOINT") and os.getenv("BRIA_23_FAST_KEY"):
    MODEL_CONFIGS["Bria 2.3 Fast"] = {
        "endpoint": os.getenv("BRIA_23_FAST_ENDPOINT"),
        "key": os.getenv("BRIA_23_FAST_KEY"),
        "provider": "Bria",
    }

SAMPLES = {
    "serene": {
        "prompt": "A serene mountain landscape during sunset with a clear sky and vibrant colors",
        "negative_prompt": "stormy weather, dark clouds",
    },
    "portrait": {
        "prompt": "A portrait of a Beautiful and playful ethereal singer, golden designs, highly detailed, blurry background",
        "negative_prompt": "Logo,Watermark,Text,Ugly,Morbid,Extra fingers,Poorly drawn hands,Mutation,Blurry,Extra limbs,Gross proportions,Missing arms,Mutated hands,Long neck,Duplicate,Mutilated,Mutilated hands,Poorly drawn face,Deformed,Bad anatomy,Cloned face,Malformed,limbs,Missing legs,Too many fingers",
    },
    "self-portrait": {
        "prompt": "Self-portrait in the style of Rembrandt",
        "negative_prompt": "",
    },
}


def generate_image(
    model_choice: str,
    prompt: str,
    output_format: str,
    negative_prompt: str,
    size: str,
    seed: int | None = None,
    diffusion_steps: int | None = None,
    guidance_scale: float | None = None,
    image_prompt: str | None = None,
    image_strength: float | None = None,
) -> Image.Image:
    """
    Generate an image based on the provided configuration and prompt parameters.
    """
    # Get configuration for selected model
    model_config = MODEL_CONFIGS[model_choice]

    params = {
        "prompt": prompt,
        "output_format": output_format,
        "size": size,
    }

    if seed:
        params["seed"] = seed

    if model_config["provider"] == "Bria":
        if diffusion_steps:
            params["diffusion_steps"] = diffusion_steps
        if guidance_scale:
            params["guidance_scale"] = guidance_scale

    if negative_prompt:
        params["negative_prompt"] = negative_prompt

    # Only add image_prompt for Stable Diffusion 3.5
    if model_choice == "Stable Diffusion 3.5" and image_prompt is not None:
        buffered = BytesIO()
        image_prompt.save(buffered, format="PNG")
        encoded_string = base64.b64encode(buffered.getvalue()).decode("utf-8")

        if image_strength:
            params["image_prompt"] = {
                "image": encoded_string,
                "strength": image_strength,
            }
        else:
            params["image_prompt"] = {"image": encoded_string}

    logger.info(f"Using model: {model_choice}")
    logger.info(
        f"Sending request with params: {json.dumps({**params, 'image_prompt': '<image data>' if 'image_prompt' in params else params.get('image_prompt', None)}, indent=2)}"
    )

    headers = {
        "Authorization": f"{model_config['key']}",
        "Accept": "application/json",
        "extra-parameters": "pass-through",
    }

    response = requests.post(
        model_config["endpoint"] + "/images/generations", headers=headers, json=params
    )

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTPError: {e}")
        logger.error(f"Response content: {response.content}")

        raise gr.Error(f"Error: {str(e)}\n{response.content.decode()}") from e

    # Decode response based on the provider
    response_json = response.json()
    if model_config["provider"] == "Bria":
        image_data = base64.b64decode(response_json["data"][0]["b64_json"])
    else:
        image_data = base64.b64decode(response_json["image"])

    output_image = Image.open(BytesIO(image_data))
    return output_image


def fill_sample(sample_type: str) -> tuple[str, str]:
    """
    Return prompt and negative prompt based on the specified sample type from SAMPLES.
    """
    if sample_type in SAMPLES:
        return SAMPLES[sample_type]["prompt"], SAMPLES[sample_type]["negative_prompt"]

    return ("", "")


with gr.Blocks(title="Image Generation - Azure AI Foundry") as demo:
    gr.Markdown("# Image Generation - Azure AI Foundry")

    with gr.Row():
        with gr.Column():
            model_choice = gr.Dropdown(
                choices=list(MODEL_CONFIGS.keys()),
                label="Model",
                value=list(MODEL_CONFIGS.keys())[0],
            )
            prompt = gr.Textbox(
                label="Image Prompt", placeholder="Describe your image..."
            )

            # (visible only for Stable Diffusion 3.5)
            image_prompt = gr.Image(
                label="Initial image (optional)",
                type="pil",
                height=200,
            )

            with gr.Accordion("Advanced", open=False):
                negative_prompt = gr.Textbox(
                    label="Negative Prompt (optional)",
                    placeholder="What to avoid in the image",
                )
                size = gr.Radio(
                    choices=[
                        "672x1566",
                        "768x1366",
                        "836x1254",
                        "916x1145",
                        "1024x1024",
                        "1145x916",
                        "1254x836",
                        "1366x768",
                        "1566x672",
                    ],
                    label="Image Size",
                    value="1024x1024",
                )
                output_format = gr.Radio(
                    choices=["jpeg", "png"],
                    label="Output Format",
                    value="png",
                )
                # (visible only for Stable Diffusion 3.5)
                image_strength = gr.Slider(
                    minimum=0,
                    maximum=1,
                    step=0.01,
                    label="Image Strength (optional)",
                    value=lambda: None,
                )

                seed = gr.Slider(
                    minimum=0,
                    maximum=1000,
                    step=1,
                    label="Seed (optional)",
                    value=lambda: None,
                )
                # Optional Bria-specific parameters (hidden by default)
                diffusion_steps = gr.Slider(
                    minimum=8,
                    maximum=12,
                    step=1,
                    label="Number of Diffusion Steps",
                    visible=False,
                    value=lambda: None,
                )
                guidance_scale = gr.Slider(
                    minimum=1.0,
                    maximum=5.0,
                    step=0.1,
                    label="Guidance Scale",
                    visible=False,
                    value=lambda: None,
                )

            generate_btn = gr.Button("Generate Image", variant="primary")

            with gr.Row():
                sample_btn_1 = gr.Button("Sample: Serene Mountain")
                sample_btn_2 = gr.Button("Sample: Portrait")
                sample_btn_3 = gr.Button("Sample: Self-Portrait")
        with gr.Column():
            output_image = gr.Image(label="Generated Image")

    # Update the visibility of fields based on model provider and model choice
    def update_inputs(selected_model: str):
        if MODEL_CONFIGS[selected_model]["provider"] == "Bria":
            return (
                gr.update(visible=False),  # output_format hidden for Bria
                gr.update(visible=True),  # diffusion_steps shown for Bria
                gr.update(visible=True),  # guidance_scale shown for Bria
                gr.update(visible=False),  # image_prompt hidden for Bria
                gr.update(visible=False),  # image_strength hidden for Bria
            )
        else:
            # Only show image_prompt and image_strength for Stable Diffusion 3.5
            visible = True if selected_model == "Stable Diffusion 3.5" else False
            return (
                gr.update(visible=True),  # output_format visible for non-Bria
                gr.update(visible=False),  # diffusion_steps hidden for non-Bria
                gr.update(visible=False),  # guidance_scale hidden for non-Bria
                gr.update(visible=visible),  # image_prompt visible only for SD 3.5
                gr.update(visible=visible),  # image_strength visible only for SD 3.5
            )

    model_choice.change(
        fn=update_inputs,
        inputs=model_choice,
        outputs=[
            output_format,
            diffusion_steps,
            guidance_scale,
            image_prompt,
            image_strength,
        ],
    )

    generate_btn.click(
        fn=generate_image,
        inputs=[
            model_choice,
            prompt,
            output_format,
            negative_prompt,
            size,
            seed,
            diffusion_steps,
            guidance_scale,
            image_prompt,
            image_strength,
        ],
        outputs=output_image,
    )

    sample_btn_1.click(
        fn=lambda: fill_sample("serene"),
        inputs=[],
        outputs=[prompt, negative_prompt],
    )

    sample_btn_2.click(
        fn=lambda: fill_sample("portrait"),
        inputs=[],
        outputs=[prompt, negative_prompt],
    )

    sample_btn_3.click(
        fn=lambda: fill_sample("self-portrait"),
        inputs=[],
        outputs=[prompt, negative_prompt],
    )

if __name__ == "__main__":
    demo.launch()
