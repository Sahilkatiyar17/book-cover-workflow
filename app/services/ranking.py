import os
import sys
import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor
from groq import Groq
from app.utils.constants import GraphConfig
from app.utils.exception import AgentException
from app.utils.logger import logging

from app.utils.config import get_settings

logger = logging.getLogger(__name__)

groq_client = Groq(api_key=get_settings().groq_api_key_1)

class ClipEmbedder:
    def __init__(self, model_name: str = "openai/clip-vit-base-patch32"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        logger.info(f"CLIP model '{model_name}' loaded on {self.device}")

    def embed_text(self, text: str) -> np.ndarray:
        # Summarize long prompts so CLIP (77-token limit) doesn't truncate/crash
        if len(text.split()) > 50:
            summary = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": f"Summarize this image prompt in under 60 words, keeping all key visual details: {text}"}],
                temperature=0.3,
            )
            text = summary.choices[0].message.content.strip()

        inputs = self.processor(text=[text], return_tensors="pt", padding=True, truncation=True).to(self.device)
        with torch.no_grad():
            features = self.model.get_text_features(**inputs)
        return features.cpu().numpy()[0]

    def embed_image(self, image_path: str) -> np.ndarray:
        try:
            image = Image.open(image_path).convert("RGB")
            inputs = self.processor(images=image, return_tensors="pt", truncation=True).to(self.device)
            with torch.no_grad():
                features = self.model.get_image_features(**inputs)
            return features.cpu().numpy()[0]
        except Exception as e:
            raise AgentException(e, sys) from e

class EmbeddingCache:
    """
    Simple file-based cache — one .npy file per image, saved next to the image itself.
    Prototype-level caching: sufficient at this scale, not concurrency-safe.
    A production version would move this to SQLite or a vector DB.
    """

    def __init__(self, cache_dir: str = GraphConfig.RAW_IMAGE_DIR):
        self.cache_dir = cache_dir

    def _embedding_path(self, image_path: str) -> str:
        base, _ = os.path.splitext(image_path)
        return f"{base}.npy"

    def load(self, image_path: str) -> np.ndarray | None:
        emb_path = self._embedding_path(image_path)
        if os.path.exists(emb_path):
            return np.load(emb_path)
        return None

    def save(self, image_path: str, embedding: np.ndarray) -> None:
        emb_path = self._embedding_path(image_path)
        np.save(emb_path, embedding)


class RankingEngine:
    """
    Ranks a batch of downloaded images against a text query using CLIP + cosine similarity.
    Reuses cached embeddings where available instead of recomputing.
    """

    def __init__(self):
        self.embedder = ClipEmbedder()
        self.cache = EmbeddingCache()

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def rank(self, query: str, images: list[dict]) -> list[dict]:
        query_embedding = self.embedder.embed_text(query)

        scored = []
        for item in images:
            image_path = item["local_path"]
            try:
                cached = self.cache.load(image_path)
                if cached is not None:
                    embedding = cached
                else:
                    embedding = self.embedder.embed_image(image_path)
                    self.cache.save(image_path, embedding)
                item["score"] = self._cosine_similarity(query_embedding, embedding)
                scored.append(item)
            except AgentException as e:
                logger.warning(f"Skipping unreadable image {image_path}: {e}")
                continue

        ranked = sorted(scored, key=lambda x: x["score"], reverse=True)
        logger.info(f"Ranked {len(ranked)} images for query: {query}")
        return ranked


class RankingNode:
    """LangGraph node wrapper — OOP style, callable, plugs into graph.add_node()."""

    def __init__(self):
        self.engine = RankingEngine()

    def __call__(self, state: dict) -> dict:
        ranked = self.engine.rank(state["prompt"], state["search_results"])
        return {"ranked_results": ranked}