# Plan: Knowledge Agent

## Context

The Knowledge agent is agent #8 of 9. It provides RAG-powered Q&A from the Hub's knowledge base (20 seeded documents covering CSS support, best practices, and email client quirks). Unlike the other 7 agents which transform or analyse HTML, the Knowledge agent is a **Q&A agent** — it receives a question, searches the knowledge base, and returns a grounded answer with citations.

**Pre-existing assets:**
- `app/ai/agents/knowledge/SKILL.md` — L1+L2 core instructions (already written)
- `app/ai/agents/knowledge/skills/` — 4 L3 skill files (rag_strategies, email_client_engines, can_i_email_reference, citation_rules)
- `app/knowledge/` — Full RAG pipeline (service, repository, schemas, routes) with hybrid search

**Design decisions:**
1. **Not an HTML transformer** — Receives a question, returns an answer. No HTML pass-through.
2. **Requires DB session** — Must call `KnowledgeService.search()` which requires an `AsyncSession`.
3. **Blueprint integration is advisory** — Knowledge node provides context to downstream agents, not a fixer in the recovery loop. It sits outside the QA gate cycle.
4. **No recovery routing** — Knowledge failures (no results, low confidence) don't map to QA check failures. The recovery router does NOT route to knowledge.

## Files to Create

### Core Agent (4 files)
- `app/ai/agents/knowledge/schemas.py` — Request/Response models
- `app/ai/agents/knowledge/prompt.py` — Progressive disclosure prompt builder
- `app/ai/agents/knowledge/service.py` — Orchestration: search → prompt → LLM → parse

### Blueprint Integration (1 file)
- `app/ai/blueprints/nodes/knowledge_node.py` — Advisory node (not in recovery loop)

### Eval Stack (3 files)
- `app/ai/agents/evals/synthetic_data_knowledge.py` — 10 test cases
- `app/ai/agents/evals/judges/knowledge.py` — 5-criteria binary judge

### CLAUDE.md Updates (1 file)
- `app/ai/agents/knowledge/CLAUDE.md` — Agent documentation

## Files to Modify

### Eval Registration (3 files)
- `app/ai/agents/evals/dimensions.py` — Add `KNOWLEDGE_DIMENSIONS`
- `app/ai/agents/evals/runner.py` — Add `run_knowledge_case()` + register in `run_agent()`
- `app/ai/agents/evals/judges/__init__.py` — Add `KnowledgeJudge` to `JUDGE_REGISTRY`

### Mock Traces (1 file)
- `app/ai/agents/evals/mock_traces.py` — Add `KNOWLEDGE_CRITERIA` + update `AGENT_CRITERIA`

### Blueprint Wiring (1 file)
- `app/ai/blueprints/definitions/campaign.py` — Add `KnowledgeNode` (advisory, not in QA loop)

### Tests (1 file)
- `app/ai/blueprints/tests/test_campaign.py` — Update structure assertions for knowledge node

### Documentation (3 files)
- `app/ai/agents/CLAUDE.md` — Move Knowledge from "Planned" to "Implemented"
- `app/ai/agents/evals/CLAUDE.md` — Update status table

## Implementation Steps

### Step 1: Schemas (`app/ai/agents/knowledge/schemas.py`)

```python
"""Knowledge agent request/response schemas."""

from pydantic import BaseModel, Field


class KnowledgeSource(BaseModel):
    """A cited source from the knowledge base."""

    document_id: int
    filename: str
    domain: str
    chunk_content: str
    relevance_score: float


class KnowledgeRequest(BaseModel):
    """Request to the Knowledge agent."""

    question: str = Field(..., min_length=5, max_length=2000)
    domain: str | None = None  # Optional domain filter (css_support, best_practices, client_quirks)
    stream: bool = False


class KnowledgeResponse(BaseModel):
    """Response from the Knowledge agent."""

    answer: str
    sources: list[KnowledgeSource]
    confidence: float  # 0.0–1.0
    skills_loaded: list[str]
    model: str
```

### Step 2: Prompt Builder (`app/ai/agents/knowledge/prompt.py`)

Follow the exact pattern from `code_reviewer/prompt.py`:

```python
"""Progressive disclosure prompt builder for the Knowledge agent."""

from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)

_AGENT_DIR = Path(__file__).parent

# L3 skill files loaded on-demand
SKILL_FILES: dict[str, str] = {
    "rag_strategies": "rag_strategies.md",
    "email_client_engines": "email_client_engines.md",
    "can_i_email_reference": "can_i_email_reference.md",
    "citation_rules": "citation_rules.md",
}


def detect_relevant_skills(question: str) -> list[str]:
    """Detect which L3 skills are relevant to the question."""
    q = question.lower()
    relevant: list[str] = []

    # Always load citation rules (core to Knowledge agent)
    relevant.append("citation_rules")

    # Client/engine questions
    engine_keywords = ["outlook", "gmail", "apple mail", "yahoo", "samsung",
                       "rendering engine", "webkit", "word", "blink", "thunderbird"]
    if any(kw in q for kw in engine_keywords):
        relevant.append("email_client_engines")

    # CSS support / Can I Email questions
    css_keywords = ["css", "support", "can i email", "property", "display",
                    "flex", "grid", "margin", "padding", "background",
                    "border-radius", "box-shadow", "variable", "var("]
    if any(kw in q for kw in css_keywords):
        relevant.append("can_i_email_reference")

    # RAG strategy questions (meta — how to search better)
    rag_keywords = ["search", "find", "knowledge base", "document"]
    if any(kw in q for kw in rag_keywords):
        relevant.append("rag_strategies")

    return relevant


def build_system_prompt(relevant_skills: list[str]) -> str:
    """Build system prompt from SKILL.md + relevant L3 files."""
    skill_path = _AGENT_DIR / "SKILL.md"
    base_prompt = skill_path.read_text()

    for skill_name in relevant_skills:
        filename = SKILL_FILES.get(skill_name)
        if not filename:
            continue
        skill_file = _AGENT_DIR / "skills" / filename
        if skill_file.exists():
            content = skill_file.read_text()
            base_prompt += f"\n\n---\n## Reference: {skill_name}\n\n{content}"
            logger.info(
                "agents.knowledge.skill_loaded",
                skill=skill_name,
            )

    return base_prompt
```

### Step 3: Service (`app/ai/agents/knowledge/service.py`)

Key difference from other agents: requires `AsyncSession` for `KnowledgeService.search()`.

```python
"""Knowledge agent service — RAG-powered Q&A from the email knowledge base."""

from __future__ import annotations

from app.ai.agents.knowledge.prompt import build_system_prompt, detect_relevant_skills
from app.ai.agents.knowledge.schemas import (
    KnowledgeRequest,
    KnowledgeResponse,
    KnowledgeSource,
)
from app.ai.protocols import CompletionResponse
from app.ai.registry import get_registry
from app.ai.shared import extract_confidence, strip_confidence_comment, validate_output
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
            limit=10,
        )
        search_response: SearchResponse = await rag_service.search(search_request)

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
        model = settings.ai.model_standard or settings.ai.model

        try:
            response: CompletionResponse = await provider.complete(
                system_prompt=system_prompt,
                user_message=user_message,
                model=model,
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
        chunks = []
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
```

### Step 4: CLAUDE.md (`app/ai/agents/knowledge/CLAUDE.md`)

```markdown
<claude-mem-context>
# Recent Activity

<!-- This section is auto-generated by claude-mem. Edit content outside the tags. -->

*No recent activity*
</claude-mem-context>

# Knowledge Agent

RAG-powered Q&A agent for email development questions. Searches the Hub's knowledge base (20 documents across css_support, best_practices, client_quirks domains) and generates grounded answers with citations.

## Architecture
- **Not an HTML transformer** — Receives question, returns answer with sources
- **Requires DB session** — `KnowledgeService.search()` needs `AsyncSession`
- **Progressive disclosure** — SKILL.md (L1+L2) + 4 L3 skill files loaded on-demand

## Files
- `schemas.py` — `KnowledgeRequest`, `KnowledgeResponse`, `KnowledgeSource`
- `prompt.py` — `detect_relevant_skills()`, `build_system_prompt()`
- `service.py` — `KnowledgeAgentService.process()` (RAG search → LLM → parse)
- `SKILL.md` — Core instructions (grounding rules, answer structure, confidence)
- `skills/` — 4 L3 files (rag_strategies, email_client_engines, can_i_email_reference, citation_rules)

## Eval
- 10 synthetic test cases in `evals/synthetic_data_knowledge.py`
- 5-criteria judge in `evals/judges/knowledge.py` (answer_accuracy, citation_grounding, code_example_quality, source_relevance, completeness)
```

### Step 5: Dimensions (`app/ai/agents/evals/dimensions.py`)

Add at the end of the file, following the existing pattern:

```python
KNOWLEDGE_DIMENSIONS = {
    "query_type": {
        "description": "Type of email development question asked",
        "values": [
            "css_property_support",     # "Does Gmail support display:flex?"
            "best_practice_lookup",     # "What's the best way to do responsive images?"
            "client_quirk_diagnosis",   # "Why does my background disappear in Outlook?"
            "comparison_query",         # "Outlook vs Gmail dark mode support?"
            "how_to_with_code",         # "How do I create a bulletproof button?"
            "troubleshooting",          # "My email clips in Gmail — why?"
        ],
    },
    "domain_coverage": {
        "description": "Which knowledge domains the answer requires",
        "values": [
            "single_domain_css",       # Answer from css_support docs alone
            "single_domain_practice",  # Answer from best_practices alone
            "single_domain_quirks",    # Answer from client_quirks alone
            "cross_domain",            # Requires multiple domains
        ],
    },
    "answer_complexity": {
        "description": "Expected depth and format of the answer",
        "values": [
            "yes_no_with_caveat",      # Simple support question with exceptions
            "explanation_with_code",   # Needs code example
            "multi_client_matrix",     # Compare across clients
            "deep_troubleshooting",    # Requires reasoning across multiple facts
        ],
    },
    "source_availability": {
        "description": "How well the knowledge base covers this question",
        "values": [
            "direct_match",            # KB has exact document for this
            "partial_coverage",        # Some relevant docs, needs synthesis
            "edge_case",               # KB barely covers it, confidence should be low
        ],
    },
}
```

### Step 6: Synthetic Test Data (`app/ai/agents/evals/synthetic_data_knowledge.py`)

Create 10 test cases covering the dimension space. Each case has: `id`, `question`, `domain`, `dimensions`, `expected_challenges`.

```python
"""Synthetic test data for the Knowledge agent evaluation.

10 dimension-based test cases covering CSS property support, best practices,
client quirks, comparison queries, and troubleshooting scenarios.
"""

from typing import Any

KNOWLEDGE_TEST_CASES: list[dict[str, Any]] = [
    # --- CSS Property Support ---
    {
        "id": "kn-001",
        "question": "Does Gmail support the CSS display:flex property in emails?",
        "domain": "css_support",
        "dimensions": {
            "query_type": "css_property_support",
            "domain_coverage": "single_domain_css",
            "answer_complexity": "yes_no_with_caveat",
            "source_availability": "direct_match",
        },
        "expected_challenges": [
            "Correctly state that Gmail does NOT support display:flex",
            "Mention table-based layout as the standard alternative",
            "Cite css_support domain document",
            "High confidence (well-documented topic)",
        ],
    },
    {
        "id": "kn-002",
        "question": "Which email clients support CSS border-radius?",
        "domain": "css_support",
        "dimensions": {
            "query_type": "css_property_support",
            "domain_coverage": "single_domain_css",
            "answer_complexity": "multi_client_matrix",
            "source_availability": "direct_match",
        },
        "expected_challenges": [
            "List supported clients (Apple Mail, iOS, most modern webmail)",
            "Note Outlook Windows does NOT support border-radius",
            "Mention progressive enhancement approach",
            "Cite Can I Email data",
        ],
    },
    # --- Best Practice ---
    {
        "id": "kn-003",
        "question": "What is the recommended approach for responsive email images?",
        "domain": "best_practices",
        "dimensions": {
            "query_type": "best_practice_lookup",
            "domain_coverage": "single_domain_practice",
            "answer_complexity": "explanation_with_code",
            "source_availability": "direct_match",
        },
        "expected_challenges": [
            "Include explicit width/height attributes",
            "Use style='display:block; width:100%; height:auto;'",
            "Mention max-width for fluid layouts",
            "Provide HTML code example with img tag",
            "Cite best_practices document",
        ],
    },
    {
        "id": "kn-004",
        "question": "How do I create a bulletproof button for email?",
        "domain": None,
        "dimensions": {
            "query_type": "how_to_with_code",
            "domain_coverage": "cross_domain",
            "answer_complexity": "explanation_with_code",
            "source_availability": "direct_match",
        },
        "expected_challenges": [
            "Provide VML-based bulletproof button code for Outlook",
            "Include padding-based CSS fallback for modern clients",
            "Show MSO conditional comment wrapping",
            "Code must use placeholder URLs only",
        ],
    },
    # --- Client Quirks ---
    {
        "id": "kn-005",
        "question": "Why does Outlook add extra spacing to my email tables?",
        "domain": "client_quirks",
        "dimensions": {
            "query_type": "client_quirk_diagnosis",
            "domain_coverage": "single_domain_quirks",
            "answer_complexity": "deep_troubleshooting",
            "source_availability": "direct_match",
        },
        "expected_challenges": [
            "Explain Word rendering engine table handling",
            "Mention cellpadding/cellspacing/border='0' attributes",
            "Reference mso-table-lspace/rspace CSS properties",
            "Cite Outlook quirks document",
        ],
    },
    {
        "id": "kn-006",
        "question": "How does Gmail handle dark mode in emails?",
        "domain": None,
        "dimensions": {
            "query_type": "client_quirk_diagnosis",
            "domain_coverage": "cross_domain",
            "answer_complexity": "explanation_with_code",
            "source_availability": "direct_match",
        },
        "expected_challenges": [
            "Explain Gmail's auto-inversion behavior",
            "Mention color-scheme meta tag",
            "Distinguish Gmail web vs Android vs iOS behavior",
            "Reference both dark_mode css_support and client_quirks docs",
        ],
    },
    # --- Comparison ---
    {
        "id": "kn-007",
        "question": "Compare Outlook's and Apple Mail's CSS support for email development",
        "domain": None,
        "dimensions": {
            "query_type": "comparison_query",
            "domain_coverage": "cross_domain",
            "answer_complexity": "multi_client_matrix",
            "source_availability": "direct_match",
        },
        "expected_challenges": [
            "Contrast Word rendering engine (Outlook) vs WebKit (Apple Mail)",
            "List key CSS properties where they differ",
            "Note Apple Mail is most permissive, Outlook most restrictive",
            "Cite multiple source documents",
        ],
    },
    # --- Troubleshooting ---
    {
        "id": "kn-008",
        "question": "My email is getting clipped in Gmail. How do I fix it?",
        "domain": None,
        "dimensions": {
            "query_type": "troubleshooting",
            "domain_coverage": "cross_domain",
            "answer_complexity": "deep_troubleshooting",
            "source_availability": "direct_match",
        },
        "expected_challenges": [
            "Explain the 102KB Gmail clipping threshold",
            "Suggest file size reduction strategies",
            "Mention inlining CSS, removing comments, minifying",
            "Reference file_size best practice document",
        ],
    },
    # --- Edge Cases ---
    {
        "id": "kn-009",
        "question": "Does Samsung Mail support CSS animations in emails?",
        "domain": "css_support",
        "dimensions": {
            "query_type": "css_property_support",
            "domain_coverage": "single_domain_css",
            "answer_complexity": "yes_no_with_caveat",
            "source_availability": "edge_case",
        },
        "expected_challenges": [
            "Acknowledge limited data on Samsung Mail animation support",
            "Low confidence due to sparse knowledge base coverage",
            "Suggest progressive enhancement regardless",
            "Should NOT fabricate specific version support claims",
        ],
    },
    {
        "id": "kn-010",
        "question": "What is the best email client for testing responsive emails?",
        "domain": None,
        "dimensions": {
            "query_type": "best_practice_lookup",
            "domain_coverage": "cross_domain",
            "answer_complexity": "explanation_with_code",
            "source_availability": "partial_coverage",
        },
        "expected_challenges": [
            "Recommend testing across rendering engines (WebKit, Word, Blink)",
            "Suggest specific clients per engine",
            "Medium confidence (opinion-based, partially covered)",
            "Should NOT present opinion as authoritative fact",
        ],
    },
]
```

### Step 7: Judge (`app/ai/agents/evals/judges/knowledge.py`)

```python
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportGeneralTypeIssues=false
"""Binary pass/fail judge for the Knowledge agent."""

from app.ai.agents.evals.judges.base import (
    SYSTEM_PROMPT_TEMPLATE,
    build_criteria_block,
    parse_judge_response,
)
from app.ai.agents.evals.judges.schemas import (
    JudgeCriteria,
    JudgeInput,
    JudgeVerdict,
)

KNOWLEDGE_CRITERIA: list[JudgeCriteria] = [
    JudgeCriteria(
        name="answer_accuracy",
        description=(
            "Is the answer factually correct based on the retrieved context? "
            "Claims about CSS support, email client behavior, or rendering engines "
            "must match the source documents. Fabricated or hallucinated claims "
            "not grounded in the retrieved context are a failure."
        ),
    ),
    JudgeCriteria(
        name="citation_grounding",
        description=(
            "Does the answer cite specific source documents? Every factual claim "
            "should reference the document it came from (by filename or domain). "
            "An answer that states facts without any citation is a failure. "
            "Citations to non-existent documents are also a failure."
        ),
    ),
    JudgeCriteria(
        name="code_example_quality",
        description=(
            "When the question calls for code, does the answer include a working "
            "email-safe HTML/CSS example? Code must use table-based layouts (not "
            "div/flex/grid for layout), inline styles, and placeholder URLs "
            "(placehold.co or example.com). Must NOT contain <script>, on* handlers, "
            "or javascript: protocol. If no code is needed, this criterion passes."
        ),
    ),
    JudgeCriteria(
        name="source_relevance",
        description=(
            "Are the retrieved sources relevant to the question? The top sources "
            "should come from the expected domain(s). If the question is about CSS "
            "support, sources should be from css_support domain. If sources are "
            "irrelevant or no sources were retrieved for a well-covered topic, "
            "this criterion fails."
        ),
    ),
    JudgeCriteria(
        name="completeness",
        description=(
            "Does the answer address all aspects of the question? Compare against "
            "the expected_challenges list. Missing a major aspect (e.g., not "
            "mentioning Outlook fallback when discussing a CSS property) is a "
            "failure. The answer should also include a confidence indicator "
            "appropriate to the source coverage level."
        ),
    ),
]


class KnowledgeJudge:
    """Binary judge for Knowledge agent outputs."""

    agent_name: str = "knowledge"
    criteria: list[JudgeCriteria] = KNOWLEDGE_CRITERIA

    def build_prompt(self, judge_input: JudgeInput) -> str:
        """Build evaluation prompt with question, sources, and answer."""
        criteria_block = build_criteria_block(self.criteria)
        system = SYSTEM_PROMPT_TEMPLATE.format(criteria_block=criteria_block)

        question = ""
        domain = "any"
        if judge_input.input_data:
            question = str(judge_input.input_data.get("question", ""))
            domain = str(judge_input.input_data.get("domain", "any"))

        answer_output = ""
        sources_output = ""
        if judge_input.output_data:
            answer_output = str(judge_input.output_data.get("answer", ""))
            sources = judge_input.output_data.get("sources", [])
            if isinstance(sources, list):
                for src in sources:
                    if isinstance(src, dict):
                        sources_output += (
                            f"- {src.get('filename', '?')} "
                            f"(domain: {src.get('domain', '?')}, "
                            f"score: {src.get('relevance_score', '?')})\n"
                        )

        expected = ""
        if judge_input.expected_challenges:
            expected = "\n".join(f"- {c}" for c in judge_input.expected_challenges)

        user_content = (
            f"## QUESTION\n{question}\n\n"
            f"## DOMAIN FILTER\n{domain}\n\n"
            f"## EXPECTED CHALLENGES\n{expected}\n\n"
            f"## AGENT OUTPUT (Answer)\n{answer_output}\n\n"
            f"## RETRIEVED SOURCES\n{sources_output}"
        )
        return f"{system}\n\n---\n\n{user_content}"

    def parse_response(self, raw: str, judge_input: JudgeInput) -> JudgeVerdict:
        """Parse LLM JSON response into JudgeVerdict."""
        return parse_judge_response(raw, judge_input, self.agent_name)
```

### Step 8: Register in Judge Registry (`app/ai/agents/evals/judges/__init__.py`)

Add import and registry entry:

```python
# Add import
from app.ai.agents.evals.judges.knowledge import KnowledgeJudge

# Add to JUDGE_REGISTRY dict
"knowledge": KnowledgeJudge,

# Add to type union in JUDGE_REGISTRY annotation
# Add to __all__
"KnowledgeJudge",
```

### Step 9: Register in Runner (`app/ai/agents/evals/runner.py`)

**Add import** at top with other synthetic data imports:
```python
from app.ai.agents.evals.synthetic_data_knowledge import KNOWLEDGE_TEST_CASES
```

**Add runner function** (after `run_code_reviewer_case`, before `run_agent`):
```python
async def run_knowledge_case(case: dict[str, Any]) -> dict[str, Any]:
    """Run a single knowledge test case and return the trace."""
    from app.ai.agents.knowledge.schemas import KnowledgeRequest
    from app.ai.agents.knowledge.service import KnowledgeAgentService

    from app.core.database import get_db_context
    from app.knowledge.service import KnowledgeService as RAGService

    service = KnowledgeAgentService()
    question: str = str(case["question"])
    domain: str | None = case.get("domain")
    request = KnowledgeRequest(question=question, domain=domain)

    start = time.monotonic()
    try:
        async with get_db_context() as db:
            rag_service = RAGService(db)
            response = await service.process(request, rag_service)
        elapsed = time.monotonic() - start
        return {
            "id": case["id"],
            "agent": "knowledge",
            "dimensions": case["dimensions"],
            "input": {
                "question": question,
                "domain": domain,
            },
            "output": {
                "answer": response.answer,
                "sources": [s.model_dump() for s in response.sources],
                "confidence": response.confidence,
                "skills_loaded": response.skills_loaded,
                "model": response.model,
            },
            "expected_challenges": case["expected_challenges"],
            "elapsed_seconds": round(elapsed, 2),
            "error": None,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        elapsed = time.monotonic() - start
        return {
            "id": case["id"],
            "agent": "knowledge",
            "dimensions": case["dimensions"],
            "input": {
                "question": question,
                "domain": domain,
            },
            "output": None,
            "expected_challenges": case["expected_challenges"],
            "elapsed_seconds": round(elapsed, 2),
            "error": f"{type(e).__name__}: {e}",
            "timestamp": datetime.now(UTC).isoformat(),
        }
```

**Add to `run_agent()` dispatch** (after code_reviewer elif):
```python
elif agent == "knowledge":
    cases = KNOWLEDGE_TEST_CASES
    runner = run_knowledge_case
```

**Update the `--agent` choices** in the argparser to include `"knowledge"`.

### Step 10: Mock Traces (`app/ai/agents/evals/mock_traces.py`)

Add after `CODE_REVIEWER_CRITERIA`:
```python
KNOWLEDGE_CRITERIA: list[dict[str, str]] = [
    {"criterion": "answer_accuracy", "description": "Answer factually correct from context"},
    {"criterion": "citation_grounding", "description": "Claims cite source documents"},
    {"criterion": "code_example_quality", "description": "Code uses email-safe patterns"},
    {"criterion": "source_relevance", "description": "Retrieved sources match question domain"},
    {"criterion": "completeness", "description": "Answer addresses all aspects of question"},
]
```

Update `AGENT_CRITERIA` dict:
```python
"knowledge": KNOWLEDGE_CRITERIA,
```

### Step 11: Blueprint Node (`app/ai/blueprints/nodes/knowledge_node.py`)

The Knowledge node is **advisory** — it enriches context for downstream nodes but does NOT sit in the QA→recovery loop. It can be invoked explicitly when a blueprint needs knowledge lookup.

```python
"""Knowledge node — RAG-powered Q&A for blueprint context enrichment.

Advisory node: provides knowledge base context to downstream agents.
Not part of the QA → recovery router loop.
"""

from app.ai.agents.knowledge.prompt import build_system_prompt, detect_relevant_skills
from app.ai.agents.knowledge.schemas import KnowledgeSource
from app.ai.blueprints.protocols import (
    AgentHandoff,
    BlueprintNode,
    HandoffStatus,
    NodeContext,
    NodeResult,
    NodeType,
)
from app.ai.protocols import CompletionResponse
from app.ai.registry import get_registry
from app.ai.shared import extract_confidence, strip_confidence_comment, validate_output
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
        model = settings.ai.model_standard or settings.ai.model

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
        rag_service = context.metadata.get("rag_service")
        if rag_service:
            try:
                search_request = SearchRequest(query=str(question), limit=7)
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

        try:
            response: CompletionResponse = await provider.complete(
                system_prompt=system_prompt,
                user_message=user_message,
                model=model,
            )
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
```

### Step 12: Campaign Blueprint Wiring (`app/ai/blueprints/definitions/campaign.py`)

Add import and node registration. **Do NOT add to recovery router loop** — Knowledge is advisory.

Add import:
```python
from app.ai.blueprints.nodes.knowledge_node import KnowledgeNode
```

In `build_campaign_blueprint()`, after creating code_reviewer:
```python
knowledge = KnowledgeNode()
```

Add to nodes dict:
```python
knowledge.name: knowledge,
```

**Do NOT add edges** for knowledge in the QA→recovery loop. The knowledge node is available for future blueprint definitions that need it (e.g., a "research" blueprint). For now it's registered but not wired into campaign edges. This keeps the campaign graph unchanged while making the node available.

### Step 13: Update Test (`app/ai/blueprints/tests/test_campaign.py`)

Update the structure test to verify knowledge node exists:
- Add `assert "knowledge" in definition.nodes`
- Add `assert definition.nodes["knowledge"].node_type == "agentic"`
- **Do NOT change edge count** (knowledge has no edges in campaign blueprint)

### Step 14: Update Eval CLAUDE.md Files

**`app/ai/agents/CLAUDE.md`**: Move Knowledge from "Planned Agents" to "Implemented Agents (V2)" section with description matching the pattern.

**`app/ai/agents/evals/CLAUDE.md`**: Add Knowledge agent row to the status table with "10 cases" and "5 criteria".

### Step 15: Update Documentation

Update runner CLI usage comment at top of `runner.py` to include `knowledge` in the example list.

## Security Checklist

The Knowledge agent does NOT add new HTTP endpoints (it uses existing `/api/v1/knowledge/search` for RAG and is accessed via blueprint engine or service layer). Security applies to:

- [x] No new routes — agent invoked via blueprint engine or direct service call
- [x] `KnowledgeService.search()` already has auth + rate limiting on its route
- [x] Input validation via Pydantic (`KnowledgeRequest` with `min_length=5, max_length=2000`)
- [x] Error responses use `ServiceUnavailableError` (auto-sanitized via `AppError` hierarchy)
- [x] No secrets/credentials in logs (structured logging with field lengths, not content)
- [x] SKILL.md security rules: no `<script>`, no `on*` handlers, no `javascript:` protocol
- [x] Synthetic test data uses only `placehold.co` and `example.com` URLs
- [x] Judge does not expose agent system prompt

## Verification

- [ ] `make check` passes (lint + types + tests + security-check)
- [ ] `make eval-dry-run` exercises knowledge agent through mock pipeline
- [ ] Knowledge agent returns grounded answers with citations when RAG has data
- [ ] Low confidence emitted when no sources found
- [ ] Blueprint structure test passes with knowledge node
- [ ] Judge registry has 8 agents (was 7)
- [ ] Runner accepts `--agent knowledge` flag
