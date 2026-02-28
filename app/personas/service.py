"""Business logic for test persona engine."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.personas.exceptions import PersonaNotFoundError
from app.personas.models import Persona
from app.personas.schemas import PersonaCreate, PersonaResponse

logger = get_logger(__name__)


class PersonaService:
    """Business logic for test personas."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_personas(self) -> list[PersonaResponse]:
        result = await self.db.execute(select(Persona).order_by(Persona.name))
        return [PersonaResponse.model_validate(p) for p in result.scalars().all()]

    async def get_persona(self, persona_id: int) -> PersonaResponse:
        result = await self.db.execute(select(Persona).where(Persona.id == persona_id))
        persona = result.scalar_one_or_none()
        if not persona:
            raise PersonaNotFoundError(f"Persona {persona_id} not found")
        return PersonaResponse.model_validate(persona)

    async def create_persona(self, data: PersonaCreate) -> PersonaResponse:
        logger.info("personas.create_started", name=data.name)
        persona = Persona(**data.model_dump(), is_preset=False)
        self.db.add(persona)
        await self.db.commit()
        await self.db.refresh(persona)
        return PersonaResponse.model_validate(persona)
