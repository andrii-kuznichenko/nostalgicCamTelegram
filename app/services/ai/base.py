from collections.abc import Awaitable, Callable
from abc import ABC, abstractmethod
from pathlib import Path


class AIServiceError(Exception):
    pass


class AIImageEditingService(ABC):
    @abstractmethod
    async def edit_image(
        self,
        image_path: Path,
        prompt: str,
        progress_callback: Callable[[str], Awaitable[None]] | None = None,
    ) -> Path:
        raise NotImplementedError

    async def close(self) -> None:
        return None
