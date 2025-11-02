"""Telegram bot that mirrors E-Hentai galleries to Telegraph."""

from __future__ import annotations

import asyncio
import logging
import random
import re
import requests
from typing import Dict, List, Tuple

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (ApplicationBuilder, CommandHandler, ContextTypes,
                          MessageHandler, filters)

from ehentai import EhentaiGalleryDownloader, GalleryProcessingError
from telegraph_client import TelegraphClient, TelegraphError, build_gallery_nodes
from config import BotConfig, TelegraphSettings, load_config


LOGGER = logging.getLogger(__name__)

URL_PATTERN = re.compile(r"https?://(?:e-hentai|exhentai)\.org/(?:g|s)/[^\s]+", re.IGNORECASE)


def _prepare_runtime(config: BotConfig) -> TelegraphSettings:
    return config.telegraph


def _create_telegraph_client(settings: TelegraphSettings) -> TelegraphClient:
    token = random.choice(settings.access_tokens)
    return TelegraphClient(
        access_token=token,
        author_name=settings.author_name,
        author_url=settings.author_url,
    )


def _extract_gallery_urls(text: str) -> List[str]:
    return list(dict.fromkeys(URL_PATTERN.findall(text)))


def _process_gallery(
    url: str,
    telegraph_settings: TelegraphSettings,
    cookies: Dict[str, str],
) -> Tuple[str, str]:
    LOGGER.info("Processing gallery: %s", url)
    downloader = EhentaiGalleryDownloader(cookies=cookies)
    title, images = downloader.download_gallery(url)
    telegraph_client = _create_telegraph_client(telegraph_settings)
    try:
        sources = [telegraph_client.upload_image(image.temp_path) for image in images]
        nodes = build_gallery_nodes(sources)
        page_url = telegraph_client.create_gallery_page(title, nodes)
    finally:
        downloader.cleanup_images(images)
    return title, page_url


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "发送 E-Hentai/ExHentai 画廊链接给我，我会下载并上传到 Telegraph。"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    urls = _extract_gallery_urls(update.message.text)
    if not urls:
        return

    await update.message.reply_text("开始处理链接，请稍候……")

    loop = asyncio.get_running_loop()
    results: List[Tuple[str, str, str]] = []
    errors: List[str] = []

    telegraph_settings: TelegraphSettings = context.bot_data["telegraph_settings"]
    cookies: Dict[str, str] = context.bot_data["ehentai_cookies"]

    for url in urls:
        try:
            title, page_url = await loop.run_in_executor(
                None,
                _process_gallery,
                url,
                telegraph_settings,
                dict(cookies),
            )
            results.append((url, title, page_url))
        except (
            GalleryProcessingError,
            TelegraphError,
            RuntimeError,
            requests.exceptions.RequestException,
        ) as exc:
            LOGGER.exception("Failed to process %s", url)
            errors.append(f"❌ {url}\n{exc}")

    messages: List[str] = []
    for _, title, page in results:
        messages.append(f"✅ {title}\n<a href=\"{page}\">{page}</a>")
    messages.extend(errors)

    if messages:
        await update.message.reply_text("\n\n".join(messages), parse_mode=ParseMode.HTML, disable_web_page_preview=False)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    config = load_config()
    telegraph_settings = _prepare_runtime(config)

    application = ApplicationBuilder().token(config.telegram_bot_token).build()
    application.bot_data["telegraph_settings"] = telegraph_settings
    application.bot_data["ehentai_cookies"] = config.ehentai_cookies

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    LOGGER.info("Bot started")
    application.run_polling()


if __name__ == "__main__":
    main()
