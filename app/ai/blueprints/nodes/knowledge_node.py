# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
"""Knowledge node — RAG-powered Q&A for blueprint context enrichment.

Advisory node: provides knowledge base context to downstream agents.
Not part of the QA → recovery router loop.
"""

from app.ai.agents.knowledge.prompt import build_system_prompt, detect_relevant_skills
from app.ai.agents.knowledge.schemas import KnowledgeSource
from app.ai.blueprints.protocols import (
    AgentHandoff,
    HandoffStatus,
    NodeContext,
    NodeResult,
    NodeType,
)
from app.ai.protocols import CompletionResponse, Message
from app.ai.registry import get_registry
from app.ai.routing import resolve_model
from app.ai.sanitize import sanitize_prompt, validate_output
from app.ai.shared import extract_confidence, strip_confidence_comment
from app.core.config import get_settings
from app.core.logging import get_logger
from app.knowledge.schemas import SearchRequest

logger = get_logger(__name__)


class KnowledgeNode:
    """Advisory blueprint node for RAG-powered knowledge retrieval."""

    @property
    def name(self) -> str:
        return "knowledge"

    @property
    def node_type(self) -> NodeType:
        return "agentic"

    async def execute(self, context: NodeContext) -> NodeResult:
        """Execute knowledge lookup for the current brief/context.

        Reads the brief as the question. Returns knowledge context
        in AgentHandoff.decisions for downstream agents to consume.
        """
        settings = get_settings()
        registry = get_registry()
        provider = registry.get_llm(settings.ai.provider)
        model = resolve_model("standard")

        question = context.brief or context.metadata.get("knowledge_query", "")
        if not question:
            return NodeResult(
                status="skipped",
                html=context.html,
                details="No question provided for knowledge lookup",
            )

        # Search knowledge base (requires DB — use context metadata if available)
        sources: list[KnowledgeSource] = []
        search_context = ""
        rag_service: object | None = context.metadata.get("rag_service")
        if rag_service and hasattr(rag_service, "search"):
            try:
                search_request = SearchRequest(
                    query=str(question), domain=None, language=None, limit=7
                )
                search_response = await rag_service.search(search_request)
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
                search_context = "\n\n".join(
                    f"### {s.filename} ({s.domain}, score={s.relevance_score:.2f})\n{s.chunk_content}"
                    for s in sources[:5]
                )
            except Exception:
                logger.warning("agents.knowledge.search_failed", exc_info=True)

        # Build prompt
        relevant_skills = detect_relevant_skills(str(question))
        system_prompt = build_system_prompt(relevant_skills)

        user_message = (
            f"## QUESTION\n{question}\n\n"
            f"## RETRIEVED CONTEXT\n{search_context or 'No context retrieved.'}\n\n"
            "Answer the question with citations. End with <!-- CONFIDENCE: 0.XX -->"
        )

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=sanitize_prompt(user_message)),
        ]

        try:
            response: CompletionResponse = await provider.complete(messages, model=model)
        except Exception as exc:
            logger.error("agents.knowledge.node_failed", error=str(exc))
            return NodeResult(
                status="failed",
                html=context.html,
                error=f"Knowledge lookup failed: {exc}",
            )

        raw_answer = validate_output(response.content)
        confidence = extract_confidence(raw_answer)
        answer = strip_confidence_comment(raw_answer)

        # Pack answer and sources into handoff for downstream nodes
        source_refs = tuple(s.filename for s in sources[:5])
        handoff = AgentHandoff(
            status=HandoffStatus.OK,
            agent_name="knowledge",
            artifact=answer,
            decisions=(f"knowledge_answer: {answer[:200]}",),
            warnings=() if sources else ("knowledge: no sources found for query",),
            component_refs=source_refs,
            confidence=confidence,
        )

        return NodeResult(
            status="success",
            html=context.html,  # Pass through unchanged
            handoff=handoff,
            usage=response.usage,
        )
