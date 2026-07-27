from abc import ABC, abstractmethod
import requests

from app.utils.config import get_settings
from app.utils.exception import AgentException
from app.utils.logger import logging
import sys

from app.utils.constants import ImageSearchConfig, GraphConfig
import os
import hashlib

logger = logging.getLogger(__name__)


class ImageSourceProvider(ABC):
    """Base class every image source must implement — keeps the aggregator provider-agnostic."""

    @abstractmethod
    def fetch(self, query: str, count: int) -> list[dict]:
        """Returns a list of dicts: {url, source, metadata}"""
        raise NotImplementedError


class UnsplashProvider(ImageSourceProvider):
    def __init__(self):
        self.api_key = get_settings().unsplash_api_key
        self.base_url = "https://api.unsplash.com/search/photos"

    def fetch(self, query: str, count: int) -> list[dict]:
        try:
            resp = requests.get(
                self.base_url,
                params={"query": query, "per_page": count},
                headers={"Authorization": f"Client-ID {self.api_key}"},
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            return [{"url": r["urls"]["regular"], "source": "unsplash", "metadata": r} for r in results]
        except Exception as e:
            raise AgentException(e, sys) from e


class PexelsProvider(ImageSourceProvider):
    def __init__(self):
        self.api_key = get_settings().pexels_api_key
        self.base_url = "https://api.pexels.com/v1/search"

    def fetch(self, query: str, count: int) -> list[dict]:
        try:
            resp = requests.get(
                self.base_url,
                params={"query": query, "per_page": count},
                headers={"Authorization": self.api_key},
            )
            resp.raise_for_status()
            results = resp.json().get("photos", [])
            return [{"url": r["src"]["large"], "source": "pexels", "metadata": r} for r in results]
        except Exception as e:
            raise AgentException(e, sys) from e


class SerpApiProvider(ImageSourceProvider):
    def __init__(self):
        self.api_key = get_settings().serpapi_api_key
        self.base_url = "https://serpapi.com/search"

    def fetch(self, query: str, count: int) -> list[dict]:
        try:
            resp = requests.get(
                self.base_url,
                params={"engine": "google_images", "q": query, "api_key": self.api_key},
            )
            resp.raise_for_status()
            results = resp.json().get("images_results", [])[:count]
            return [{"url": r["original"], "source": "serpapi", "metadata": r} for r in results]
        except Exception as e:
            raise AgentException(e, sys) from e


class PinterestProvider(ImageSourceProvider):
    """
    Unofficial source via Apify's Pinterest Search Scraper actor API.
    Experimental — no ToS-backed guarantee of uptime; treat as best-effort, not core.
    """

    def __init__(self):
        self.api_key = get_settings().apify_api_key
        self.actor_url = "https://api.apify.com/v2/acts/api-empire~pinterest-search-scraper/run-sync-get-dataset-items"

    def fetch(self, query: str, count: int) -> list[dict]:
        try:
            resp = requests.post(
                self.actor_url,
                params={"token": self.api_key},
                json={"searchQueries": [query], "resultsLimit": count},
            )
            resp.raise_for_status()
            results = resp.json()
            return [{"url": r.get("imageUrl"), "source": "pinterest", "metadata": r} for r in results[:count]]
        except Exception as e:
            raise AgentException(e, sys) from e
        
        
class ImageSourceProvider(ABC):
    """Base class every image source must implement."""

    @abstractmethod
    def fetch(self, query: str, count: int) -> list[dict]:
        """Returns a list of dicts: {url, source, metadata}"""
        raise NotImplementedError


# UnsplashProvider, PexelsProvider, SerpApiProvider, PinterestProvider
# stay exactly as already written — unchanged, omitted here for brevity.


class ImageDownloader:
    """Downloads a remote image URL and saves it locally, so nothing downstream depends on a live URL."""

    def __init__(self, save_dir: str = GraphConfig.RAW_IMAGE_DIR):
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)

    def download(self, url: str, source: str) -> str | None:
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            file_hash = hashlib.md5(url.encode()).hexdigest()[:12]
            ext = ".jpg"
            filename = f"{source}_{file_hash}{ext}"
            filepath = os.path.join(self.save_dir, filename)
            with open(filepath, "wb") as f:
                f.write(resp.content)
            logger.info(f"Saved image from {source} -> {filepath}")
            return filepath
        except Exception as e:
            logger.warning(f"Failed to download image from {source}: {url} — {e}")
            return None


class ImageSearchAggregator:
    """
    Calls all configured providers, downloads results locally.
    Isolated from LangGraph so it can be unit-tested standalone.
    """

    def __init__(self):
        self.providers = {
            "unsplash": (UnsplashProvider(), 2),
            "pexels": (PexelsProvider(), 2),
            "serpapi": (SerpApiProvider(), 2),
            "pinterest": (PinterestProvider(), 1),
        }
        self.downloader = ImageDownloader()

    def run(self, query: str) -> list[dict]:
        collected = []
        for name, (provider, count) in self.providers.items():
            try:
                results = provider.fetch(query, count)
                for r in results:
                    local_path = self.downloader.download(r["url"], name)
                    if local_path:
                        r["local_path"] = local_path
                        collected.append(r)
            except AgentException as e:
                logger.warning(f"Provider '{name}' failed, skipping: {e}")
                continue
        return collected


class ImageSearchNode:
    """
    LangGraph node wrapper — OOP style, callable so it plugs straight into graph.add_node().
    Takes graph state in, returns the state update dict LangGraph expects.
    """

    def __init__(self):
        self.aggregator = ImageSearchAggregator()

    def __call__(self, state: dict) -> dict:
        query = state["prompt"]
        images = self.aggregator.run(query)
        logger.info(f"ImageSearchNode collected {len(images)} images for query: {query}")
        return {"search_results": images}