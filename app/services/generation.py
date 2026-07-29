import base64
import os
import sys
from abc import ABC, abstractmethod

from google import genai
from google.genai import types
from huggingface_hub import InferenceClient
from openai import OpenAI

from app.utils.config import get_settings
from app.utils.constants import GenerationConfig, GraphConfig, FeedbackBranch
from app.utils.exception import AgentException
from app.utils.logger import logging

logger = logging.getLogger(__name__)


class ImageGenerationProvider(ABC):
    """Base class every generation model must implement."""

    @abstractmethod
    def generate(self, prompt: str, reference_image_paths: list[str], output_path: str) -> str | None:
        raise NotImplementedError


class HuggingFaceProvider(ImageGenerationProvider):
    """
    Primary provider — free serverless inference via Hugging Face.
    Text-to-image only: reference images are NOT sent to the model, since
    multi-reference conditioning isn't standardized on HF's free tier.
    The prompt (already built by PromptAssembler from search prompt + feedback)
    is what drives generation here.
    """

    def __init__(self):
        self.client = InferenceClient(
            model=GenerationConfig.HF_MODEL_ID,
            token=get_settings().huggingface_api_key,
        )

    def generate(self, prompt: str, reference_image_paths: list[str], output_path: str) -> str | None:
        try:
            image = self.client.text_to_image(prompt)
            image.save(output_path)
            logger.info(f"Hugging Face generated cover -> {output_path}")
            return output_path
        except Exception as e:
            logger.warning(f"Hugging Face generation failed, skipping: {e}")
            return None


class GeminiProvider(ImageGenerationProvider):
    """
    DISABLED — not removed. Correctly implemented, but blocked by Google's
    policy requiring a billed project even for free-tier image quota, confirmed
    via testing (see logs: limit: 0 on generate_content_free_tier_requests for
    gemini-2.5-flash-image, even via direct SDK with no LangChain aliasing bug
    involved). Re-enable once billing is attached, or if Google changes policy.
    """

    def __init__(self):
        self.client = genai.Client(api_key=get_settings().gemini_api_key)
        self.model_name = GenerationConfig.GEMINI_MODEL_ID

    def generate(self, prompt: str, reference_image_paths: list[str], output_path: str) -> str | None:
        try:
            reference_parts = []
            for path in reference_image_paths[: GenerationConfig.MAX_REFERENCE_IMAGES]:
                with open(path, "rb") as f:
                    reference_parts.append(types.Part.from_bytes(data=f.read(), mime_type="image/jpeg"))

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[prompt, *reference_parts],
            )

            image_bytes = None
            for part in response.candidates[0].content.parts:
                if part.inline_data is not None:
                    image_bytes = part.inline_data.data
                    break

            if image_bytes is None:
                raise ValueError("No image returned from Gemini")

            with open(output_path, "wb") as f:
                f.write(image_bytes)
            logger.info(f"Gemini generated cover -> {output_path}")
            return output_path
        except Exception as e:
            logger.warning(f"Gemini generation failed, skipping: {e}")
            return None


class QwenEditProvider(ImageGenerationProvider):
    """
    Via NVIDIA NIM. PENDING VERIFICATION — the exact hosted endpoint/request
    format below is unconfirmed; the docs example is for self-hosted NIM
    containers, not the public integrate.api.nvidia.com catalog. Replace this
    with the real code sample from your build.nvidia.com model page's
    'View Code' panel before trusting this provider.
    """

    def __init__(self):
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=get_settings().nvidia_api_key,
        )
        self.model_name = GenerationConfig.QWEN_EDIT_MODEL_ID

    def generate(self, prompt: str, reference_image_paths: list[str], output_path: str) -> str | None:
        if not reference_image_paths:
            logger.warning("QwenEditProvider requires at least one reference image, skipping")
            return None
        try:
            base_image_path = reference_image_paths[0]
            with open(base_image_path, "rb") as image_file:
                response = self.client.images.edit(
                    model=self.model_name,
                    image=image_file,
                    prompt=prompt,
                    n=1,
                    response_format="b64_json",
                )

            image_bytes = base64.b64decode(response.data[0].b64_json)
            with open(output_path, "wb") as f:
                f.write(image_bytes)
            logger.info(f"Qwen-Image-Edit generated cover -> {output_path}")
            return output_path
        except Exception as e:
            logger.warning(f"Qwen-Image-Edit generation failed, skipping: {e}")
            return None


class PromptAssembler:
    """
    Builds the final generation prompt. Now delegates the heavy lifting to
    SummarizationNode's output (state["summarized_prompt"]) — image captions
    and user feedback are already merged and condensed there. This method just
    adds generation-specific framing on top.
    """

    def assemble(self, state: dict) -> str:
        summarized = state.get("summarized_prompt")

        if not summarized:
            # fallback if summarization was skipped/failed upstream
            summarized = f"Book cover theme: {state['prompt']}"

        prompt = (
            f"Professional book cover design. {summarized} "
            f"High-quality, print-ready illustration with strong visual composition, "
            f"balanced negative space for title text, and genre-appropriate color grading."
        )

        logger.info(f"Final generation prompt: {prompt}")
        return prompt
    
class GenerationService:
    """Runs all configured providers — one failing doesn't block the others."""

    def __init__(self):
        self.providers = {
            "huggingface": HuggingFaceProvider(),
            # "gemini": GeminiProvider(),   # disabled — requires billing, see class docstring
            # "qwen_edit": QwenEditProvider(),  # pending endpoint verification
        }
        os.makedirs(GraphConfig.GENERATED_COVER_DIR, exist_ok=True)

    def generate_all(self, prompt: str, reference_image_paths: list[str]) -> dict:
        results = {}
        for name, provider in self.providers.items():
            output_path = os.path.join(GraphConfig.GENERATED_COVER_DIR, f"cover_{name}.jpg")
            path = provider.generate(prompt, reference_image_paths, output_path)
            if path:
                results[name] = path
        return results


class GenerationNode:
    """LangGraph node wrapper — OOP style, callable, plugs into graph.add_node()."""

    def __init__(self):
        self.assembler = PromptAssembler()
        self.service = GenerationService()

    def __call__(self, state: dict) -> dict:
        generation_prompt = self.assembler.assemble(state)

        reference_paths = list(state.get("selected_images", []))
        if state.get("user_uploaded_image"):
            reference_paths.append(state["user_uploaded_image"])

        generated_covers = self.service.generate_all(generation_prompt, reference_paths)

        return {
            "generation_prompt": generation_prompt,
            "generated_cover_path": generated_covers.get("huggingface") or generated_covers.get("qwen_edit"),
            "generated_covers": generated_covers,
        }