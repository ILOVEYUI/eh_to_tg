"""Simple Telegraph API helper."""

from __future__ import annotations

import json
import logging
import os
from typing import Iterable, List, Optional

import requests


LOGGER = logging.getLogger(__name__)


class TelegraphError(RuntimeError):
    """Raised when the Telegraph API returns an error."""


class TelegraphClient:
    """Minimal Telegraph client for uploading images and creating pages."""

    API_ROOT = "https://api.telegra.ph"
    UPLOAD_ROOT = "https://telegra.ph"

    def __init__(
        self,
        access_token: str,
        author_name: Optional[str] = None,
        author_url: Optional[str] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        if not access_token:
            raise ValueError("Telegraph access token must be provided")
        self.access_token = access_token
        self.author_name = author_name
        self.author_url = author_url
        self.session = session or requests.Session()

    def upload_image(self, path: str) -> str:
        LOGGER.debug("Uploading image to Telegraph: %s", path)
        with open(path, "rb") as file_pointer:
            response = self.session.post(
                f"{self.UPLOAD_ROOT}/upload", files={"file": (os.path.basename(path), file_pointer)}
            )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list) or not data:
            raise TelegraphError(f"Unexpected response from Telegraph upload: {data}")
        entry = data[0]
        if "src" not in entry:
            raise TelegraphError(f"Upload response missing src: {entry}")
        return entry["src"]

    def create_gallery_page(self, title: str, content_nodes: Iterable[dict], return_content: bool = False) -> str:
        payload = {
            "access_token": self.access_token,
            "title": title,
            "content": json.dumps(list(content_nodes), ensure_ascii=False),
        }
        if self.author_name:
            payload["author_name"] = self.author_name
        if self.author_url:
            payload["author_url"] = self.author_url
        if return_content:
            payload["return_content"] = True

        LOGGER.debug("Creating Telegraph page with title '%s'", title)
        response = self.session.post(f"{self.API_ROOT}/createPage", data=payload)
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise TelegraphError(data.get("error", "Unknown Telegraph error"))
        result = data.get("result") or {}
        url = result.get("url")
        if not url:
            raise TelegraphError(f"Telegraph did not provide a URL: {result}")
        return url


def build_gallery_nodes(image_sources: List[str]) -> List[dict]:
    """Create Telegraph content nodes for the gallery images."""

    nodes: List[dict] = []
    for index, src in enumerate(image_sources, start=1):
        nodes.append(
            {
                "tag": "figure",
                "children": [
                    {"tag": "img", "attrs": {"src": src}},
                    {"tag": "figcaption", "children": [f"Page {index}"]},
                ],
            }
        )
    return nodes
