import base64
import sys
from abc import ABC, abstractmethod

from groq import Groq
import time

from app.utils.config import get_settings
from app.utils.constants import ImageUnderstandingConfig
from app.utils.exception import AgentException
from app.utils.logger import logging

logger = logging.getLogger(__name__)


class ImageUnderstandingProvider(ABC):
    """Base class every image-understanding (captioning) provider must implement."""

    @abstractmethod
    def describe(self, image_path: str, prompt: str) -> str | None:
        raise NotImplementedError


class GroqVLProvider(ImageUnderstandingProvider):
    """
    Vision-language provider using Groq's API (LPU inference — fast, no cold starts).

    Receives:
        - One reference image (local path, base64-encoded)
        - A detailed analysis prompt

    Returns:
        A rich textual description of the image.
    """

    def __init__(self):
        self.client = Groq(api_key=get_settings().groq_api_key)
        self.model_name = ImageUnderstandingConfig.MODEL_ID  # e.g. "qwen/qwen3.6-27b"

    @staticmethod
    def _encode_image(image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def describe(self, image_path: str, prompt: str) -> str | None:
        try:
            base64_image = self._encode_image(image_path)

            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt,
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ]

            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.2,
                max_tokens=ImageUnderstandingConfig.MAX_TOKENS,
            )

            description = completion.choices[0].message.content.strip()

            logger.info(
                f"Successfully extracted description from image (Groq): {image_path}"
            )

            return description

        except Exception as e:
            logger.warning(
                f"Groq image understanding failed for {image_path}: {e}"
            )
            return None


class ImageUnderstandingNode:
    def __init__(self):
        self.provider = GroqVLProvider()
        self.request_delay_seconds = 2  # pacing between calls, avoids tripping Groq's rate limit

    def __call__(self, state: dict) -> dict:
        image_paths = list(state.get("selected_images", []))
        if state.get("user_uploaded_image"):
            image_paths.append(state["user_uploaded_image"])
        image_paths = image_paths[:ImageUnderstandingConfig.MAX_IMAGES_TO_DESCRIBE]

        prompt = ImageUnderstandingConfig.CAPTION_PROMPT

        descriptions = {}
        for i, path in enumerate(image_paths):
            description = self.provider.describe(path, prompt)
            if description:
                descriptions[path] = description
            if i < len(image_paths) - 1:  # no need to sleep after the last one
                time.sleep(self.request_delay_seconds)

        logger.info(f"ImageUnderstandingNode described {len(descriptions)}/{len(image_paths)} images")
        return {"image_descriptions": descriptions}