import shutil
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path

from app.config import Settings
from app.services.ai.base import AIImageEditingService


class MockAIImageEditingService(AIImageEditingService):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def edit_image(
        self,
        image_path: Path,
        prompt: str,
        progress_callback: Callable[[str], Awaitable[None]] | None = None,
    ) -> Path:
        if progress_callback is not None:
            await progress_callback("Preparing your result...")
        result_path = self.settings.temp_dir / f"mock_result_{uuid.uuid4().hex}{image_path.suffix or '.jpg'}"
        shutil.copyfile(image_path, result_path)
        return result_path
