from __future__ import annotations

import logging

from app.services.outfit_scraper import scrape_all_users

logger = logging.getLogger(__name__)


async def scheduled_scrape_all_users() -> None:
    logger.info("Starting scheduled outfit scrape for all users")
    await scrape_all_users()
    logger.info("Scheduled outfit scrape complete")
