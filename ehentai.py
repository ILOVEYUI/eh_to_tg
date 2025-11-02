"""Utilities for downloading galleries from E-Hentai/ExHentai."""

from __future__ import annotations

import logging
import os
import random
import re
import time
from dataclasses import dataclass
from tempfile import NamedTemporaryFile
from typing import Iterable, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


LOGGER = logging.getLogger(__name__)


E_HENTAI_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/114.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


class GalleryProcessingError(Exception):
    """Raised when a gallery cannot be processed."""


@dataclass
class GalleryImage:
    """Represents a single gallery image."""

    index: int
    source_url: str
    temp_path: str


class EhentaiGalleryDownloader:
    """Downloads image galleries from E-Hentai/ExHentai."""

    def __init__(
        self,
        delay_range: Tuple[float, float] = (1.5, 3.5),
        session: Optional[requests.Session] = None,
    ) -> None:
        if delay_range[0] < 0 or delay_range[1] < delay_range[0]:
            raise ValueError("Invalid delay range")
        self.delay_range = delay_range
        self.session = session or requests.Session()

    def _random_delay(self) -> None:
        delay = random.uniform(*self.delay_range)
        LOGGER.debug("Sleeping for %.2f seconds between requests", delay)
        time.sleep(delay)

    def _request(self, url: str) -> requests.Response:
        LOGGER.debug("Fetching URL: %s", url)
        response = self.session.get(url, headers=E_HENTAI_HEADERS)
        response.raise_for_status()
        return response

    def _collect_page_links(self, soup: BeautifulSoup) -> List[str]:
        links: List[str] = []
        for anchor in soup.select("#gdt .gdtm a, #gdt .gdtl a"):
            href = anchor.get("href")
            if href:
                links.append(href)
        LOGGER.debug("Found %d image page links", len(links))
        return links

    def _find_next_page(self, soup: BeautifulSoup, current_url: str) -> Optional[str]:
        for anchor in soup.select(".ptt a"):
            if anchor.get_text(strip=True) in {">", "»", "›", "Next ›"}:
                href = anchor.get("href")
                if href:
                    next_url = urljoin(current_url, href)
                    LOGGER.debug("Next page detected: %s", next_url)
                    return next_url
        return None

    def _extract_title(self, soup: BeautifulSoup) -> str:
        title_elem = soup.select_one("#gn") or soup.select_one("h1")
        if not title_elem:
            return "Untitled Gallery"
        return title_elem.get_text(strip=True)

    def _extract_image_url(self, soup: BeautifulSoup) -> Optional[str]:
        image = soup.select_one("#img")
        if image and image.get("src"):
            return image["src"]
        # Fallback: try to find image within #i3 or by attribute data-src
        image = soup.select_one("#i3 img")
        if image:
            return image.get("src") or image.get("data-src")
        return None

    def _download_image(self, url: str, index: int) -> GalleryImage:
        LOGGER.info("Downloading image %d: %s", index, url)
        response = self._request(url)
        suffix = os.path.splitext(urlparse(url).path)[1] or ".jpg"
        with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(response.content)
            temp_path = temp_file.name
        return GalleryImage(index=index, source_url=url, temp_path=temp_path)

    def _normalize_gallery_url(self, url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path

        match_gallery = re.match(r"/g/([0-9]+)/([0-9a-fA-F]+)/", path)
        if match_gallery:
            base = f"{parsed.scheme or 'https'}://{parsed.netloc or 'e-hentai.org'}"
            gallery_id, token = match_gallery.groups()
            normalized = f"{base}/g/{gallery_id}/{token}/"
            if normalized != url:
                LOGGER.debug("Normalized gallery URL %s to %s", url, normalized)
            return normalized

        match_page = re.match(r"/s/([0-9a-fA-F]+)/([0-9]+)-", path)
        if match_page:
            base = f"{parsed.scheme or 'https'}://{parsed.netloc or 'e-hentai.org'}"
            token, gallery_id = match_page.groups()
            normalized = f"{base}/g/{gallery_id}/{token}/"
            LOGGER.debug("Normalized single-page URL %s to %s", url, normalized)
            return normalized
        raise GalleryProcessingError("Unsupported E-Hentai URL")

    def iter_image_pages(self, gallery_url: str) -> Tuple[str, List[str]]:
        """Return the gallery title and ordered list of image page URLs."""

        normalized_url = self._normalize_gallery_url(gallery_url)
        current_url = normalized_url
        title: Optional[str] = None
        image_pages: List[str] = []

        while True:
            response = self._request(current_url)
            soup = BeautifulSoup(response.text, "html.parser")

            if title is None:
                title = self._extract_title(soup)

            new_links = self._collect_page_links(soup)
            for link in new_links:
                if link not in image_pages:
                    image_pages.append(link)

            next_url = self._find_next_page(soup, current_url)
            if not next_url:
                break
            current_url = next_url
            self._random_delay()

        if not image_pages:
            raise GalleryProcessingError("No images were found in the gallery")

        assert title is not None
        LOGGER.info("Collected %d image pages for gallery '%s'", len(image_pages), title)
        return title, image_pages

    def download_gallery(self, gallery_url: str) -> Tuple[str, List[GalleryImage]]:
        title, image_pages = self.iter_image_pages(gallery_url)
        images: List[GalleryImage] = []
        for idx, page_url in enumerate(image_pages, start=1):
            self._random_delay()
            response = self._request(page_url)
            soup = BeautifulSoup(response.text, "html.parser")
            image_url = self._extract_image_url(soup)
            if not image_url:
                raise GalleryProcessingError(f"Failed to locate image for page {page_url}")
            self._random_delay()
            images.append(self._download_image(image_url, idx))

        return title, images

    def cleanup_images(self, images: Iterable[GalleryImage]) -> None:
        for image in images:
            try:
                os.remove(image.temp_path)
            except OSError as exc:
                LOGGER.warning("Failed to remove temp file %s: %s", image.temp_path, exc)
