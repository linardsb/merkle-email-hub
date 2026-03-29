# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownMemberType=false
"""Pre-flight check: verify LLM provider is configured and responding.

Usage:
    python -m app.ai.agents.evals.verify_provider
    make eval-verify
"""

import asyncio
import sys
import time

from app.ai.protocols import Message
from app.ai.registry import get_registry
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def verify() -> bool:
    """Verify provider can complete a simple request."""
    settings = get_settings()
    provider_name = settings.ai.provider
    model = settings.ai.model
    api_key = settings.ai.api_key

    logger.info("=== Eval Provider Pre-Flight Check ===")
    logger.info(f"  Provider: {provider_name}")
    logger.info(f"  Model:    {model}")
    logger.info(f"  API Key:  {'configured' if api_key else 'MISSING'}")
    logger.info(f"  Base URL: {settings.ai.base_url or '(default)'}")

    if not api_key:
        logger.error("FAIL: AI__API_KEY not set. Export it before running evals.")
        return False

    try:
        registry = get_registry()
        provider = registry.get_llm(provider_name)
    except Exception as e:
        logger.error(f"FAIL: Could not initialize provider '{provider_name}': {e}")
        return False

    logger.info(f"  Sending test request to {provider_name}/{model}...")
    start = time.monotonic()
    try:
        response = await provider.complete(
            [Message(role="user", content="Respond with exactly: OK")],
            temperature=0.0,
            max_tokens=10,
        )
        elapsed = time.monotonic() - start
        logger.info(f"  Response: {response.content[:100]}")
        logger.info(f"  Latency:  {elapsed:.1f}s")
        if response.usage:
            logger.info(f"  Tokens:   {response.usage.get('total_tokens', 'N/A')}")
        logger.info("PASS: Provider is working. Ready for eval execution.")
        return True
    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error(f"  Error after {elapsed:.1f}s: {type(e).__name__}: {e}")
        logger.error("FAIL: Provider request failed. Check API key, model, and network.")
        return False


def main() -> None:
    """CLI entrypoint."""
    success = asyncio.run(verify())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
