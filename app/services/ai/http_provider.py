import logging
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path

import httpx

from app.config import Settings
from app.services.ai.base import AIImageEditingService, AIServiceError

logger = logging.getLogger(__name__)


class HttpAIImageEditingService(AIImageEditingService):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = httpx.AsyncClient(timeout=90.0)

    async def edit_image(
        self,
        image_path: Path,
        prompt: str,
        progress_callback: Callable[[str], Awaitable[None]] | None = None,
    ) -> Path:
        if progress_callback is not None:
            await progress_callback("Uploading your photo...")
        try:
            with image_path.open("rb") as source_file:
                files = {
                    "image": (image_path.name, source_file, "image/jpeg"),
                }
                data = {
                    "prompt": prompt,
                    "model": self.settings.ai_model_name,
                }
                response = await self.client.post(
                    self.settings.ai_api_url,
                    headers={"Authorization": f"Bearer {self.settings.ai_api_key}"},
                    data=data,
                    files=files,
                )
        except httpx.TimeoutException as exc:
            raise AIServiceError("The AI API did not respond in time.") from exc
        except httpx.HTTPError as exc:
            raise AIServiceError("Could not reach the AI API.") from exc

        if response.status_code >= 500:
            raise AIServiceError("The AI API is temporarily unavailable.")
        if response.status_code >= 400:
            raise AIServiceError(f"The AI API returned error {response.status_code}.")
        if not response.content:
            raise AIServiceError("The AI API returned an empty response.")

        content_type = response.headers.get("content-type", "")
        if "image" not in content_type and "octet-stream" not in content_type:
            logger.warning("Unexpected AI API content-type: %s", content_type)

        if progress_callback is not None:
            await progress_callback("Downloading your result...")
        result_path = self.settings.temp_dir / f"result_{uuid.uuid4().hex}.jpg"
        result_path.write_bytes(response.content)
        return result_path

    async def close(self) -> None:
        await self.client.aclose()
