from sqlalchemy.ext.asyncio import AsyncSession

from app.models.generation import Generation


class GenerationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: int,
        source_file_path: str,
        prompt_used: str,
        status: str = "pending",
        result_file_path: str | None = None,
        error_message: str | None = None,
    ) -> Generation:
        generation = Generation(
            user_id=user_id,
            source_file_path=source_file_path,
            prompt_used=prompt_used,
            status=status,
            result_file_path=result_file_path,
            error_message=error_message,
        )
        self.session.add(generation)
        await self.session.flush()
        return generation

    async def mark_success(self, generation: Generation, result_file_path: str) -> Generation:
        generation.status = "completed"
        generation.result_file_path = result_file_path
        generation.error_message = None
        await self.session.flush()
        return generation

    async def mark_failed(self, generation: Generation, error_message: str) -> Generation:
        generation.status = "failed"
        generation.error_message = error_message
        await self.session.flush()
        return generation
