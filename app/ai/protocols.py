"""Agent-agnostic Protocol interfaces.

Define what an LLM/embedding/reranker provider must implement.
Users implement these protocols with their preferred framework
(Pydantic AI, LangChain, CrewAI, raw SDK calls, etc.).

Example usage:
    class MyCustomLLM:
        async def complete(self, messages, **kwargs):
            ...
        async def stream(self, messages, **kwargs):
            ...

    assert isinstance(MyCustomLLM(), LLMProvider)  # True at runtime
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class Message:
    """A single message in a conversation.

    Attributes:
        role: The role of the message sender ("user", "assistant", "system").
        content: The text content of the message.
    """

    role: str  # "user", "assistant", "system"
    content: str


@dataclass
class CompletionResponse:
    """Response from an LLM completion call.

    Attributes:
        content: The generated text content.
        model: The model identifier that produced this response.
        usage: Optional token usage statistics (prompt_tokens, completion_tokens, total_tokens).
    """

    content: str
    model: str
    usage: dict[str, int] | None = None


@dataclass
class EmbeddingResponse:
    """Response from an embedding call.

    Attributes:
        embeddings: List of embedding vectors, one per input text.
        model: The model identifier that produced these embeddings.
        usage: Optional token usage statistics.
    """

    embeddings: list[list[float]]
    model: str
    usage: dict[str, int] | None = None


@dataclass
class RankedResult:
    """A single result from a reranking operation.

    Attributes:
        index: Original index of this document in the input list.
        score: Relevance score assigned by the reranker.
        text: The document text.
    """

    index: int
    score: float
    text: str


@dataclass
class ToolDefinition:
    """Metadata for a tool that an LLM can call.

    Attributes:
        name: Unique tool identifier.
        description: Human-readable description for LLM tool selection.
        parameters: JSON Schema describing the tool's parameters.
    """

    name: str
    description: str
    parameters: dict[str, object] = field(default_factory=dict)


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM completion providers.

    Implementations must support both single-shot completion and streaming.
    Any class with matching method signatures satisfies this protocol.

    Examples:
        - OpenAI-compatible APIs (OpenAI, Ollama, vLLM, LiteLLM)
        - Anthropic Claude via proxy
        - Local models via transformers
    """

    async def complete(self, messages: list[Message], **kwargs: object) -> CompletionResponse:
        """Generate a completion from a list of messages.

        Args:
            messages: Conversation history as Message objects.
            **kwargs: Provider-specific options (temperature, max_tokens, etc.).

        Returns:
            CompletionResponse with generated content and metadata.
        """
        ...

    async def stream(self, messages: list[Message], **kwargs: object) -> AsyncIterator[str]:
        """Stream completion tokens as they are generated.

        Args:
            messages: Conversation history as Message objects.
            **kwargs: Provider-specific options.

        Yields:
            Individual text chunks as they are generated.
        """
        ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol for text embedding providers.

    Implementations must support batch embedding and expose the vector dimension.
    """

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors (one per input text).
        """
        ...

    @property
    def dimension(self) -> int:
        """The dimensionality of the embedding vectors produced by this provider."""
        ...


@runtime_checkable
class RerankerProvider(Protocol):
    """Protocol for document reranking providers.

    Rerankers score query-document relevance and return the top-k results.
    """

    async def rerank(self, query: str, documents: list[str], top_k: int) -> list[RankedResult]:
        """Rerank documents by relevance to a query.

        Args:
            query: The search query.
            documents: List of document texts to rerank.
            top_k: Maximum number of results to return.

        Returns:
            List of RankedResult objects sorted by descending relevance score.
        """
        ...


@runtime_checkable
class ToolProvider(Protocol):
    """Protocol for executable tools that an LLM can invoke.

    Each tool has a name, description, and an execute method.
    Tool providers are registered with the agent and made available
    during LLM completion for function calling.
    """

    name: str
    description: str

    async def execute(self, **params: object) -> str:
        """Execute the tool with the given parameters.

        Args:
            **params: Tool-specific keyword arguments.

        Returns:
            String result of the tool execution.
        """
        ...
