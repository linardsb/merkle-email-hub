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


async def verify() -> bool:
    """Verify provider can complete a simple request."""
    settings = get_settings()
    provider_name = settings.ai.provider
    model = settings.ai.model
    api_key = settings.ai.api_key

    print("=== Eval Provider Pre-Flight Check ===")
    print(f"  Provider: {provider_name}")
    print(f"  Model:    {model}")
    print(f"  API Key:  {'configured' if api_key else 'MISSING'}")
    print(f"  Base URL: {settings.ai.base_url or '(default)'}")

    if not api_key:
        print("\nFAIL: AI__API_KEY not set. Export it before running evals.")
        return False

    try:
        registry = get_registry()
        provider = registry.get_llm(provider_name)
    except Exception as e:
        print(f"\nFAIL: Could not initialize provider '{provider_name}': {e}")
        return False

    print(f"\n  Sending test request to {provider_name}/{model}...")
    start = time.monotonic()
    try:
        response = await provider.complete(
            [Message(role="user", content="Respond with exactly: OK")],
            temperature=0.0,
            max_tokens=10,
        )
        elapsed = time.monotonic() - start
        print(f"  Response: {response.content[:100]}")
        print(f"  Latency:  {elapsed:.1f}s")
        if response.usage:
            print(f"  Tokens:   {response.usage.get('total_tokens', 'N/A')}")
        print("\nPASS: Provider is working. Ready for eval execution.")
        return True
    except Exception as e:
        elapsed = time.monotonic() - start
        print(f"  Error after {elapsed:.1f}s: {type(e).__name__}: {e}")
        print("\nFAIL: Provider request failed. Check API key, model, and network.")
        return False


def main() -> None:
    """CLI entrypoint."""
    success = asyncio.run(verify())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
