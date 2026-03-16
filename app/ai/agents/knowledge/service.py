"""Knowledge agent service — RAG-powered Q&A from the email knowledge base."""

from __future__ import annotations

from app.ai.agents.knowledge.prompt import build_system_prompt, detect_relevant_skills
from app.ai.agents.knowledge.schemas import (
    KnowledgeRequest,
    KnowledgeResponse,
    KnowledgeSource,
)
from app.ai.protocols import CompletionResponse, Message
from app.ai.registry import get_registry
from app.ai.routing import resolve_model
from app.ai.sanitize import sanitize_prompt, validate_output
from app.ai.shared import extract_confidence, strip_confidence_comment
from app.core.config import get_settings
from app.core.exceptions import ServiceUnavailableError
from app.core.logging import get_logger
from app.knowledge.schemas import SearchRequest, SearchResponse
from app.knowledge.service import KnowledgeService as RAGService

logger = get_logger(__name__)


class KnowledgeAgentService:
    """Orchestrates RAG search → LLM answer generation."""

    async def process(
        self,
        request: KnowledgeRequest,
        rag_service: RAGService,
    ) -> KnowledgeResponse:
        """Process a knowledge question.

        Args:
            request: The question and optional domain filter.
            rag_service: Injected RAG service (requires DB session).

        Returns:
            Grounded answer with citations and confidence.
        """
        logger.info(
            "agents.knowledge.process_started",
            question_length=len(request.question),
            domain=request.domain,
        )

        # 1. Search knowledge base
        search_request = SearchRequest(
            query=request.question,
            domain=request.domain,
            language=None,
            limit=10,
        )
        search_response: SearchResponse = await rag_service.search_routed(search_request)

        # 2. Build sources list
        sources = [
            KnowledgeSource(
                document_id=r.document_id,
                filename=r.document_filename,
                domain=r.domain,
                chunk_content=r.chunk_content,
                relevance_score=r.score,
            )
            for r in search_response.results
        ]

        # 3. Detect skills and build prompt
        relevant_skills = detect_relevant_skills(request.question)
        system_prompt = build_system_prompt(relevant_skills)

        # 4. Build user message with retrieved context
        user_message = _build_user_message(request.question, search_response)

        # 5. Call LLM
        settings = get_settings()
        registry = get_registry()
        provider = registry.get_llm(settings.ai.provider)
        model = resolve_model("standard")

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        try:
            response: CompletionResponse = await provider.complete(
                messages, model_override=model, max_tokens=4096
            )
        except Exception as exc:
            logger.error("agents.knowledge.llm_failed", error=str(exc))
            raise ServiceUnavailableError("Knowledge service temporarily unavailable") from exc

        # 6. Validate and extract confidence
        raw_answer = validate_output(response.content)
        confidence = extract_confidence(raw_answer)
        answer = strip_confidence_comment(raw_answer)

        # If no sources found, lower confidence
        if not sources:
            confidence = min(confidence or 0.3, 0.3)

        logger.info(
            "agents.knowledge.process_completed",
            source_count=len(sources),
            confidence=confidence,
            model=response.model,
        )

        return KnowledgeResponse(
            answer=answer,
            sources=sources[:5],  # Top 5 sources in response
            confidence=confidence or 0.5,
            skills_loaded=relevant_skills,
            model=response.model,
        )


def _build_user_message(question: str, search_response: SearchResponse) -> str:
    """Build the user message with question and retrieved context."""
    context_block = ""
    if search_response.results:
        chunks: list[str] = []
        for i, result in enumerate(search_response.results[:7], 1):
            chunks.append(
                f"### Source {i}: {result.document_filename} "
                f"(domain: {result.domain}, score: {result.score:.2f})\n"
                f"{result.chunk_content}"
            )
        context_block = "\n\n".join(chunks)
    else:
        context_block = (
            "No relevant documents found in the knowledge base. "
            "Answer based on general email development knowledge, but clearly "
            "state that no authoritative sources were found."
        )

    return (
        f"## QUESTION\n{question}\n\n"
        f"## RETRIEVED CONTEXT\n{context_block}\n\n"
        "## INSTRUCTIONS\n"
        "Answer the question using the retrieved context above. "
        "Cite specific sources by filename. Include code examples when applicable. "
        "End with a confidence comment: <!-- CONFIDENCE: 0.XX -->"
    )


def get_knowledge_agent_service() -> KnowledgeAgentService:
    """Get singleton Knowledge agent service."""
    return KnowledgeAgentService()
