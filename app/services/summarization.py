import sys
import time

from groq import Groq

from app.utils.config import get_settings
from app.utils.constants import SummarizationConfig
from app.utils.exception import AgentException
from app.utils.logger import logging

logger = logging.getLogger(__name__)


class GroqSummarizerProvider:
    """
    Text-only Groq call — summarizes combined image captions + user feedback
    into a compact prompt before it goes to the (token-limited) HF generation model.
    Same Groq API key as GroqVLProvider (image understanding) — a deliberate delay
    is added before this call to avoid stacking requests on the free tier.
    """

    def __init__(self):
        self.client = Groq(api_key=get_settings().groq_api_key)
        self.model_name = SummarizationConfig.MODEL_ID

    def summarize(self, text: str) -> str | None:
        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": text}],
                temperature=0.3,
            )
            summary = completion.choices[0].message.content.strip()
            logger.info("Summarization successful (Groq)")
            return summary
        except Exception as e:
            logger.warning(f"Summarization failed, falling back to unsummarized text: {e}")
            return None


class SummarizationNode:
    """LangGraph node wrapper — combines image captions + feedback, summarizes via Groq."""

    def __init__(self):
        self.provider = GroqSummarizerProvider()

    def __call__(self, state: dict) -> dict:
        base_prompt = state["prompt"]
        descriptions = state.get("image_descriptions", {})
        feedback = state.get("feedback", [])

        feedback_by_path = {f["image_local_path"]: f["liked_attributes"] for f in feedback}

        combined_lines = [f"Book cover theme: {base_prompt}"]
        for i, (path, caption) in enumerate(descriptions.items(), start=1):
            note = feedback_by_path.get(path)
            line = f"Reference image {i}: {caption}"
            if note:
                line += f" (User specifically liked: {note})"
            combined_lines.append(line)

        combined_text = (
            "Summarize the following into a single, concise, vivid book cover generation prompt "
            "under 1000 words. Preserve the theme, mood, and specific user preferences:\n\n"
            + "\n".join(combined_lines)
        )

        logger.info(f"Pausing {SummarizationConfig.PRE_REQUEST_DELAY_SECONDS}s before Groq summarization call")
        time.sleep(SummarizationConfig.PRE_REQUEST_DELAY_SECONDS)

        summary = self.provider.summarize(combined_text)
        final_prompt = summary if summary else "\n".join(combined_lines)  # fallback: unsummarized

        logger.info(f"SummarizationNode produced generation prompt: {final_prompt}")
        return {"summarized_prompt": final_prompt}