import asyncio
import base64
import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path

import httpx

from app.config import Settings
from app.services.ai.base import AIImageEditingService, AIServiceError

logger = logging.getLogger(__name__)


class FalFluxImageEditingService(AIImageEditingService):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = httpx.AsyncClient(timeout=30.0)

    async def edit_image(
        self,
        image_path: Path,
        prompt: str,
        negative_prompt: str | None = None,
        progress_callback: Callable[[str], Awaitable[None]] | None = None,
    ) -> Path:
        data_uri = self._build_data_uri(image_path)
        model_url = f"{self.settings.ai_api_url.rstrip('/')}/{self.settings.ai_model_name}"
        headers = {
            "Authorization": f"Key {self.settings.ai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "prompt": prompt,
            "image_urls": [data_uri],
            "num_images": 1,
            "output_format": "jpeg",
            "enable_safety_checker": True,
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt

        if progress_callback is not None:
            await progress_callback("Uploading your photo...")

        try:
            submit_response = await self.client.post(model_url, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            raise AIServiceError("fal queue submit timed out.") from exc
        except httpx.HTTPError as exc:
            raise AIServiceError("Could not reach fal queue API.") from exc

        if submit_response.status_code >= 400:
            raise self._build_api_error("fal queue submit failed", submit_response.status_code, submit_response.text)

        submit_data = submit_response.json()
        request_id = submit_data.get("request_id")
        status_url = submit_data.get("status_url")
        response_url = submit_data.get("response_url")
        if not request_id:
            raise AIServiceError("fal queue did not return request_id.")

        if not status_url:
            status_url = f"{model_url}/requests/{request_id}/status"
        if not response_url:
            response_url = f"{model_url}/requests/{request_id}"

        logger.info("Submitted fal request: model=%s request_id=%s", self.settings.ai_model_name, request_id)
        result = await self._poll_for_result(
            status_url=status_url,
            response_url=response_url,
            headers=headers,
            progress_callback=progress_callback,
        )

        response = result.get("response", {})
        images = result.get("images") or response.get("images") or []
        if not images:
            logger.error("fal response did not contain images: %s", result)
            raise AIServiceError("The AI provider returned an unexpected response format.")

        image_url = images[0].get("url")
        if not image_url:
            raise AIServiceError("fal response image did not include URL.")

        if progress_callback is not None:
            await progress_callback("Downloading your result...")

        try:
            image_response = await self.client.get(image_url)
        except httpx.HTTPError as exc:
            raise AIServiceError("Could not download generated image from fal.") from exc

        if image_response.status_code >= 400 or not image_response.content:
            raise AIServiceError("fal returned an invalid generated image.")

        result_path = self.settings.temp_dir / f"fal_result_{uuid.uuid4().hex}.jpg"
        result_path.write_bytes(image_response.content)
        return result_path

    async def _poll_for_result(
        self,
        *,
        status_url: str,
        response_url: str,
        headers: dict[str, str],
        progress_callback: Callable[[str], Awaitable[None]] | None = None,
    ) -> dict:
        deadline = asyncio.get_running_loop().time() + self.settings.fal_timeout_seconds
        last_status_message = ""

        while True:
            if asyncio.get_running_loop().time() > deadline:
                raise AIServiceError("fal request timed out while waiting for result.")

            try:
                response = await self.client.get(f"{status_url}?logs=1", headers=headers)
            except httpx.HTTPError as exc:
                raise AIServiceError("Could not poll fal status endpoint.") from exc

            if response.status_code >= 400:
                raise self._build_api_error(
                    "fal status endpoint returned error",
                    response.status_code,
                    response.text,
                )

            data = response.json()
            status = data.get("status", "UNKNOWN")
            queue_position = data.get("queue_position")
            logs = data.get("logs") or []

            if status == "IN_QUEUE":
                status_message = (
                    f"Your edit is queued"
                    + (f" (position {queue_position})" if queue_position is not None else "...")
                )
            elif status == "IN_PROGRESS":
                latest_log = logs[-1]["message"] if logs else "generation in progress"
                status_message = f"Editing your photo... {latest_log}"
            elif status == "COMPLETED":
                status_message = "Finishing up your result..."
            elif status == "FAILED":
                latest_log = logs[-1]["message"] if logs else "unknown fal error"
                raise AIServiceError(f"fal request failed: {latest_log}")
            else:
                status_message = "Still working on your photo..."

            if progress_callback is not None and status_message != last_status_message:
                await progress_callback(status_message)
                last_status_message = status_message

            if status == "COMPLETED":
                break

            await asyncio.sleep(self.settings.fal_poll_interval_seconds)

        last_error: AIServiceError | None = None
        for attempt in range(3):
            try:
                response = await self.client.get(response_url, headers=headers)
            except httpx.HTTPError as exc:
                last_error = AIServiceError("Could not fetch fal response payload.")
                if attempt == 2:
                    raise last_error from exc
                await asyncio.sleep(1.0 + attempt)
                continue

            if response.status_code < 400:
                return response.json()

            last_error = AIServiceError(
                str(self._build_api_error(
                    "fal response endpoint returned error",
                    response.status_code,
                    response.text,
                ))
            )
            if response.status_code not in {404, 408, 409, 425, 429, 500, 502, 503, 504} or attempt == 2:
                raise last_error

            logger.warning(
                "fal response payload not ready yet: status=%s attempt=%s response_url=%s",
                response.status_code,
                attempt + 1,
                response_url,
            )
            await asyncio.sleep(1.0 + attempt)

        if last_error is not None:
            raise last_error
        raise AIServiceError("fal response endpoint returned an unknown error.")

    def _build_data_uri(self, image_path: Path) -> str:
        content = image_path.read_bytes()
        encoded = base64.b64encode(content).decode("ascii")
        suffix = image_path.suffix.lower()
        content_type = "image/jpeg"
        if suffix == ".png":
            content_type = "image/png"
        elif suffix == ".webp":
            content_type = "image/webp"
        return f"data:{content_type};base64,{encoded}"

    def _format_error_body(self, text: str, max_length: int = 500) -> str:
        compact = " ".join(text.split())
        if "data:image/" in compact and ";base64," in compact:
            prefix, _sep, suffix = compact.partition(";base64,")
            compact = f"{prefix};base64,[omitted]"
            if suffix:
                compact += " ..."
        if len(compact) > max_length:
            return compact[:max_length] + "... [truncated]"
        return compact

    def _build_api_error(self, prefix: str, status_code: int, text: str) -> AIServiceError:
        policy_message = self._extract_content_policy_message(text)
        if policy_message is not None:
            return AIServiceError(policy_message)
        return AIServiceError(f"{prefix} with status {status_code}: {self._format_error_body(text)}")

    def _extract_content_policy_message(self, text: str) -> str | None:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return None

        detail = payload.get("detail")
        if not isinstance(detail, list):
            return None

        for item in detail:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "content_policy_violation":
                return "This photo did not pass the provider moderation check. Please try another image."
        return None

    async def close(self) -> None:
        await self.client.aclose()
