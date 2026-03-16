"""Query router — intent classification and entity extraction for knowledge queries."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from app.core.config import get_settings
from app.core.logging import get_logger
from app.knowledge.ontology.query import _property_id_from_css
from app.knowledge.ontology.registry import load_ontology

logger = get_logger(__name__)

# Pre-compiled pattern for CSS property:value mentions (e.g. "display: flex")
_CSS_VALUE_PATTERN = re.compile(r"([\w-]+)\s*:\s*([\w-]+)")


class QueryIntent(Enum):
    """Classified intent of a knowledge query."""

    COMPATIBILITY = "compatibility"
    HOW_TO = "how_to"
    TEMPLATE = "template"
    DEBUG = "debug"
    GENERAL = "general"


@dataclass(frozen=True)
class ExtractedEntity:
    """An entity resolved from the query to an ontology ID."""

    raw_text: str
    entity_type: str  # "client" or "property"
    ontology_id: str


@dataclass(frozen=True)
class ClassifiedQuery:
    """Result of query classification."""

    intent: QueryIntent
    original_query: str
    extracted_entities: tuple[ExtractedEntity, ...] = ()
    confidence: float = 1.0


class QueryRouter:
    """Two-tier query classifier: regex-first with optional LLM fallback.

    The router:
    1. Pre-compiles regex patterns from the ontology registry
       (client names/families, CSS property names/IDs)
    2. Runs fast regex classification against incoming queries
    3. Falls back to LLM classification for ambiguous queries
       (when enabled and confidence < threshold)
    """

    # Confidence threshold below which LLM fallback is triggered
    _CONFIDENCE_THRESHOLD = 0.6

    def __init__(self) -> None:
        self._client_patterns: list[tuple[re.Pattern[str], str]] = []
        self._property_patterns: list[tuple[re.Pattern[str], str]] = []
        self._intent_patterns: dict[QueryIntent, list[re.Pattern[str]]] = {}
        self._compiled = False

    def _ensure_compiled(self) -> None:
        """Lazily compile regex patterns from ontology on first use."""
        if self._compiled:
            return

        ontology = load_ontology()

        # Build client name → client_id patterns
        seen_patterns: set[str] = set()
        for client_id in ontology.client_ids():
            client = ontology.get_client(client_id)
            if client is None:
                continue
            alternatives: list[str] = []
            name_escaped = re.escape(client.name)
            if name_escaped.lower() not in seen_patterns:
                alternatives.append(name_escaped)
                seen_patterns.add(name_escaped.lower())
            family_escaped = re.escape(client.family)
            if family_escaped.lower() not in seen_patterns and client.family != client.name:
                alternatives.append(family_escaped)
                seen_patterns.add(family_escaped.lower())

            if alternatives:
                pattern = re.compile(
                    r"\b(?:" + "|".join(alternatives) + r")\b",
                    re.IGNORECASE,
                )
                self._client_patterns.append((pattern, client_id))

        # Build property name → property_id patterns
        seen_props: set[str] = set()
        for prop_id in ontology.property_ids():
            prop = ontology.get_property(prop_id)
            if prop is None:
                continue
            css_name = prop.property_name
            if css_name.lower() not in seen_props:
                pattern = re.compile(
                    r"\b" + re.escape(css_name) + r"\b",
                    re.IGNORECASE,
                )
                self._property_patterns.append((pattern, prop_id))
                seen_props.add(css_name.lower())

        # Intent classification patterns (ordered by specificity)
        self._intent_patterns = {
            QueryIntent.COMPATIBILITY: [
                re.compile(
                    r"\b(?:support|compatible|work(?:s|ing)?)\b.*\b(?:in|on|with|across)\b",
                    re.IGNORECASE,
                ),
                re.compile(
                    r"\b(?:does|do|can|will|is)\b.*\b(?:support|render|display|show)\b",
                    re.IGNORECASE,
                ),
                re.compile(r"\b(?:supported|compatibility|compat)\b", re.IGNORECASE),
                re.compile(r"\bcan\s+i\s+(?:use|email)\b", re.IGNORECASE),
                re.compile(
                    r"\b(?:fallback|workaround|alternative)\b.*\b(?:for|to)\b", re.IGNORECASE
                ),
            ],
            QueryIntent.TEMPLATE: [
                re.compile(r"\b(?:template|section|component|block)\b", re.IGNORECASE),
                re.compile(
                    r"\b(?:hero|header|footer|cta|banner|card)\b.*\b(?:section|block|template)\b",
                    re.IGNORECASE,
                ),
            ],
            QueryIntent.DEBUG: [
                re.compile(r"\b(?:broken|bug|issue|problem|error|wrong)\b", re.IGNORECASE),
                re.compile(r"\b(?:fix|fixing)\b", re.IGNORECASE),
                re.compile(
                    r"\b(?:why|how come)\b.*\b(?:not|doesn'?t|isn'?t|won'?t)\b", re.IGNORECASE
                ),
                re.compile(
                    r"\b(?:render(?:ing)?)\b.*\b(?:wrong|incorrect(?:ly)?|broken|weird)\b",
                    re.IGNORECASE,
                ),
                re.compile(r"\bincorrect(?:ly)?\b", re.IGNORECASE),
            ],
            QueryIntent.HOW_TO: [
                re.compile(
                    r"\b(?:how\s+(?:to|do|can|should)|best\s+(?:way|practices?))\b",
                    re.IGNORECASE,
                ),
                re.compile(
                    r"\b(?:guide|tutorial|example|implement|create|build|make)\b", re.IGNORECASE
                ),
                re.compile(
                    r"\b(?:what(?:'s|\s+is)\s+the\s+(?:best|recommended|correct))\b",
                    re.IGNORECASE,
                ),
                re.compile(r"\bhow\s+do\s+i\b", re.IGNORECASE),
            ],
        }

        self._compiled = True

    def classify(self, query: str) -> ClassifiedQuery:
        """Classify a query by intent and extract entities (regex tier only).

        Args:
            query: The raw user query string.

        Returns:
            ClassifiedQuery with intent, entities, and confidence.
        """
        self._ensure_compiled()

        entities = self._extract_entities(query)
        intent, confidence = self._classify_intent(query, entities)

        return ClassifiedQuery(
            intent=intent,
            original_query=query,
            extracted_entities=tuple(entities),
            confidence=confidence,
        )

    async def classify_with_fallback(self, query: str) -> ClassifiedQuery:
        """Classify with optional LLM fallback for low-confidence results.

        Falls back to LLM only when:
        - router_llm_fallback is enabled in config
        - Regex confidence < _CONFIDENCE_THRESHOLD
        """
        result = self.classify(query)

        settings = get_settings()
        if (
            result.confidence < self._CONFIDENCE_THRESHOLD
            and settings.knowledge.router_llm_fallback
        ):
            llm_result = await self._llm_classify(query, result.extracted_entities)
            if llm_result is not None:
                return llm_result

        return result

    def _extract_entities(self, query: str) -> list[ExtractedEntity]:
        """Extract client and property entities from query text."""
        entities: list[ExtractedEntity] = []

        for pattern, client_id in self._client_patterns:
            match = pattern.search(query)
            if match:
                entities.append(
                    ExtractedEntity(
                        raw_text=match.group(0),
                        entity_type="client",
                        ontology_id=client_id,
                    )
                )

        for pattern, prop_id in self._property_patterns:
            match = pattern.search(query)
            if match:
                entities.append(
                    ExtractedEntity(
                        raw_text=match.group(0),
                        entity_type="property",
                        ontology_id=prop_id,
                    )
                )

        # Also try _property_id_from_css for CSS-like mentions
        for m in _CSS_VALUE_PATTERN.finditer(query):
            prop_name, prop_value = m.group(1), m.group(2)
            prop_id = _property_id_from_css(prop_name, prop_value)
            if not any(e.ontology_id == prop_id for e in entities):
                entities.append(
                    ExtractedEntity(
                        raw_text=m.group(0),
                        entity_type="property",
                        ontology_id=prop_id,
                    )
                )

        return entities

    def _classify_intent(
        self, query: str, entities: list[ExtractedEntity]
    ) -> tuple[QueryIntent, float]:
        """Classify query intent using regex patterns and entity hints.

        Returns:
            (intent, confidence) tuple.
        """
        scores: dict[QueryIntent, float] = dict.fromkeys(QueryIntent, 0.0)

        for intent, patterns in self._intent_patterns.items():
            for pattern in patterns:
                if pattern.search(query):
                    scores[intent] += 1.0

        # Cross-intent suppression: DEBUG keywords override TEMPLATE
        if scores[QueryIntent.DEBUG] > 0 and scores[QueryIntent.TEMPLATE] > 0:
            scores[QueryIntent.TEMPLATE] *= 0.5

        # HOW_TO suppresses COMPATIBILITY when both match (question form)
        if scores[QueryIntent.HOW_TO] > 0 and scores[QueryIntent.COMPATIBILITY] > 0:
            scores[QueryIntent.COMPATIBILITY] *= 0.5

        # Entity-based boosting
        has_client = any(e.entity_type == "client" for e in entities)
        has_property = any(e.entity_type == "property" for e in entities)

        if has_client and has_property:
            # Entity boost is weaker when DEBUG keywords are present
            if scores[QueryIntent.DEBUG] > 0:
                scores[QueryIntent.DEBUG] += 1.0
            else:
                scores[QueryIntent.COMPATIBILITY] += 2.0
        elif has_property and scores[QueryIntent.COMPATIBILITY] > 0:
            scores[QueryIntent.COMPATIBILITY] += 1.0

        best_intent = max(scores, key=lambda k: scores[k])
        best_score = scores[best_intent]

        if best_score == 0:
            return QueryIntent.GENERAL, 0.4

        confidence = min(best_score / 3.0, 1.0)
        confidence = max(confidence, 0.5)

        return best_intent, confidence

    async def _llm_classify(
        self, query: str, entities: tuple[ExtractedEntity, ...]
    ) -> ClassifiedQuery | None:
        """LLM-based intent classification (fallback tier).

        Returns None if LLM call fails (failure-safe).
        """
        from app.ai.protocols import CompletionResponse, Message
        from app.ai.registry import get_registry
        from app.ai.sanitize import sanitize_prompt

        settings = get_settings()

        entity_context = ""
        if entities:
            entity_strs = [f"{e.entity_type}:{e.ontology_id}" for e in entities]
            entity_context = f"\nExtracted entities: {', '.join(entity_strs)}"

        system_prompt = (
            "You are a query intent classifier for an email development knowledge base.\n"
            "Classify the user's query into exactly one of these intents:\n"
            "- compatibility: Questions about CSS/HTML support in email clients\n"
            "- how_to: How-to questions, best practices, guides\n"
            "- template: Questions about email templates, layouts, components\n"
            "- debug: Debugging rendering issues, broken layouts\n"
            "- general: General questions that don't fit above categories\n\n"
            "Respond with ONLY the intent name (one word), nothing else."
        )

        user_message = sanitize_prompt(f"Query: {query}{entity_context}")

        try:
            registry = get_registry()
            provider = registry.get_llm(settings.ai.provider)
            response: CompletionResponse = await provider.complete(
                [
                    Message(role="system", content=system_prompt),
                    Message(role="user", content=user_message),
                ],
                model_override=settings.knowledge.router_llm_model,
                max_tokens=20,
            )
            intent_str = response.content.strip().lower()
            try:
                intent = QueryIntent(intent_str)
            except ValueError:
                logger.warning(
                    "knowledge.router.llm_invalid_intent",
                    raw=intent_str,
                )
                return None

            return ClassifiedQuery(
                intent=intent,
                original_query=query,
                extracted_entities=entities,
                confidence=0.8,
            )
        except Exception:
            logger.warning("knowledge.router.llm_failed", exc_info=True)
            return None


# Module-level singleton
_router: QueryRouter | None = None


def get_query_router() -> QueryRouter:
    """Get or create the query router singleton."""
    global _router
    if _router is None:
        _router = QueryRouter()
    return _router
