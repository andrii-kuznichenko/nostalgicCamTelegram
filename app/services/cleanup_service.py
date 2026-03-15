import asyncio
import logging
from datetime import datetime, timedelta

from app.config import Settings

logger = logging.getLogger(__name__)


async def cleanup_temp_files(settings: Settings) -> None:
    cutoff = datetime.utcnow() - timedelta(hours=settings.temp_file_ttl_hours)
    for path in settings.temp_dir.glob("*"):
        if not path.is_file():
            continue
        modified_at = datetime.utcfromtimestamp(path.stat().st_mtime)
        if modified_at < cutoff:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                logger.exception("Failed to delete temp file: %s", path)


async def temp_cleanup_loop(settings: Settings) -> None:
    while True:
        try:
            await cleanup_temp_files(settings)
        except Exception:
            logger.exception("Temp cleanup iteration failed")
        await asyncio.sleep(3600)
