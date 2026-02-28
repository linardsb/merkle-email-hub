"""Provider registry for resolving AI backends from configuration.

Register providers by name, resolve at runtime based on configuration.
Supports LLM, embedding, and reranker provider types.

Example usage:
    registry = get_registry()
    registry.register_llm("openai", OpenAICompatProvider)
    provider = registry.get_llm("openai")
"""

from typing import TypeVar

from app.ai.protocols import EmbeddingProvider, LLMProvider, RerankerProvider
from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class ProviderNotFoundError(KeyError):
    """Raised when a requested provider is not registered."""

    pass


class ProviderRegistry:
    """Registry for AI provider implementations.

    Stores provider classes (not instances) by name for each provider type.
    Resolution creates new instances on demand so providers can read
    current configuration at instantiation time.
    """

    def __init__(self) -> None:
        """Initialize empty registries for all provider types."""
        self._llm_providers: dict[str, type[LLMProvider]] = {}
        self._embedding_providers: dict[str, type[EmbeddingProvider]] = {}
        self._reranker_providers: dict[str, type[RerankerProvider]] = {}

    # ── LLM ──

    def register_llm(self, name: str, provider_class: type[LLMProvider]) -> None:
        """Register an LLM provider class by name.

        Args:
            name: Provider identifier (e.g., "openai", "anthropic", "ollama").
            provider_class: Class that implements the LLMProvider protocol.
        """
        self._llm_providers[name] = provider_class
        logger.debug("ai.registry.llm_registered", provider=name)

    def get_llm(self, name: str) -> LLMProvider:
        """Create and return an LLM provider instance by name.

        Args:
            name: Provider identifier to resolve.

        Returns:
            A new instance of the registered LLM provider.

        Raises:
            ProviderNotFoundError: If no provider is registered with the given name.
        """
        provider_class = self._llm_providers.get(name)
        if provider_class is None:
            available = ", ".join(sorted(self._llm_providers.keys())) or "(none)"
            msg = f"LLM provider '{name}' not found. Available: {available}"
            raise ProviderNotFoundError(msg)
        return provider_class()

    def list_llm_providers(self) -> list[str]:
        """List all registered LLM provider names.

        Returns:
            Sorted list of registered LLM provider identifiers.
        """
        return sorted(self._llm_providers.keys())

    # ── Embedding ──

    def register_embedding(self, name: str, provider_class: type[EmbeddingProvider]) -> None:
        """Register an embedding provider class by name.

        Args:
            name: Provider identifier (e.g., "openai", "jina", "local").
            provider_class: Class that implements the EmbeddingProvider protocol.
        """
        self._embedding_providers[name] = provider_class
        logger.debug("ai.registry.embedding_registered", provider=name)

    def get_embedding(self, name: str) -> EmbeddingProvider:
        """Create and return an embedding provider instance by name.

        Args:
            name: Provider identifier to resolve.

        Returns:
            A new instance of the registered embedding provider.

        Raises:
            ProviderNotFoundError: If no provider is registered with the given name.
        """
        provider_class = self._embedding_providers.get(name)
        if provider_class is None:
            available = ", ".join(sorted(self._embedding_providers.keys())) or "(none)"
            msg = f"Embedding provider '{name}' not found. Available: {available}"
            raise ProviderNotFoundError(msg)
        return provider_class()

    def list_embedding_providers(self) -> list[str]:
        """List all registered embedding provider names.

        Returns:
            Sorted list of registered embedding provider identifiers.
        """
        return sorted(self._embedding_providers.keys())

    # ── Reranker ──

    def register_reranker(self, name: str, provider_class: type[RerankerProvider]) -> None:
        """Register a reranker provider class by name.

        Args:
            name: Provider identifier (e.g., "cohere", "jina", "local").
            provider_class: Class that implements the RerankerProvider protocol.
        """
        self._reranker_providers[name] = provider_class
        logger.debug("ai.registry.reranker_registered", provider=name)

    def get_reranker(self, name: str) -> RerankerProvider:
        """Create and return a reranker provider instance by name.

        Args:
            name: Provider identifier to resolve.

        Returns:
            A new instance of the registered reranker provider.

        Raises:
            ProviderNotFoundError: If no provider is registered with the given name.
        """
        provider_class = self._reranker_providers.get(name)
        if provider_class is None:
            available = ", ".join(sorted(self._reranker_providers.keys())) or "(none)"
            msg = f"Reranker provider '{name}' not found. Available: {available}"
            raise ProviderNotFoundError(msg)
        return provider_class()

    def list_reranker_providers(self) -> list[str]:
        """List all registered reranker provider names.

        Returns:
            Sorted list of registered reranker provider identifiers.
        """
        return sorted(self._reranker_providers.keys())


# ── Module-level singleton ──

_registry: ProviderRegistry | None = None


def get_registry() -> ProviderRegistry:
    """Get or create the provider registry singleton.

    On first call, creates the registry and registers the built-in
    OpenAI-compatible LLM provider.

    Returns:
        Singleton ProviderRegistry instance.
    """
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
        _register_builtin_providers(_registry)
    return _registry


def _register_builtin_providers(registry: ProviderRegistry) -> None:
    """Register the built-in providers that ship with the template.

    Args:
        registry: The registry to populate.
    """
    from app.ai.adapters.openai_compat import OpenAICompatProvider

    registry.register_llm("openai", OpenAICompatProvider)
    # "ollama", "vllm", "litellm" all use the same OpenAI-compatible API
    registry.register_llm("ollama", OpenAICompatProvider)
    registry.register_llm("vllm", OpenAICompatProvider)
    registry.register_llm("litellm", OpenAICompatProvider)
