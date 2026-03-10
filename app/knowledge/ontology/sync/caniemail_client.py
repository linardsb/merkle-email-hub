"""Fetch and parse Can I Email feature data from GitHub."""

from __future__ import annotations

import re
from typing import Any

import httpx
import yaml

from app.core.config import get_settings
from app.core.logging import get_logger
from app.knowledge.ontology.sync.schemas import CanIEmailFeature

logger = get_logger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


class CanIEmailClient:
    """Fetches feature support data from the Can I Email GitHub repository."""

    def __init__(self) -> None:
        settings = get_settings()
        self._repo = settings.ontology_sync.github_repo
        self._branch = settings.ontology_sync.github_branch
        self._timeout = settings.ontology_sync.request_timeout_seconds
        self._max_features = settings.ontology_sync.max_features_per_sync
        self._headers: dict[str, str] = {
            "Accept": "application/vnd.github.v3+json",
        }
        if settings.ontology_sync.github_token:
            self._headers["Authorization"] = f"Bearer {settings.ontology_sync.github_token}"

    async def get_latest_commit_sha(self) -> str:
        """Get the HEAD commit SHA of the target branch."""
        url = f"https://api.github.com/repos/{self._repo}/branches/{self._branch}"
        async with httpx.AsyncClient(timeout=self._timeout, headers=self._headers) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return str(resp.json()["commit"]["sha"])

    async def list_feature_files(self) -> list[dict[str, Any]]:
        """List all files in _features/ directory via GitHub Trees API."""
        url = f"https://api.github.com/repos/{self._repo}/git/trees/{self._branch}?recursive=1"
        async with httpx.AsyncClient(timeout=self._timeout, headers=self._headers) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            tree = resp.json().get("tree", [])
            return [
                item
                for item in tree
                if item["path"].startswith("_features/")
                and item["path"].endswith(".md")
                and not item["path"].endswith("_template.md")
            ]

    async def fetch_all_features(self) -> list[CanIEmailFeature]:
        """Fetch all feature files with concurrency-limited batch fetching."""
        file_list = await self.list_feature_files()

        if len(file_list) > self._max_features:
            logger.warning(
                "ontology.sync.feature_cap_reached",
                total=len(file_list),
                cap=self._max_features,
            )
            file_list = file_list[: self._max_features]

        features: list[CanIEmailFeature] = []
        batch_size = 20
        for i in range(0, len(file_list), batch_size):
            batch = file_list[i : i + batch_size]
            async with httpx.AsyncClient(timeout=self._timeout, headers=self._headers) as client:
                for item in batch:
                    try:
                        url = (
                            f"https://raw.githubusercontent.com/"
                            f"{self._repo}/{self._branch}/{item['path']}"
                        )
                        resp = await client.get(url)
                        resp.raise_for_status()
                        feature = self._parse_feature(item["path"], resp.text)
                        if feature:
                            features.append(feature)
                    except Exception:
                        logger.warning(
                            "ontology.sync.feature_fetch_failed",
                            path=item["path"],
                            exc_info=True,
                        )
        return features

    def _parse_feature(self, path: str, content: str) -> CanIEmailFeature | None:
        """Parse frontmatter from a Can I Email feature file."""
        match = _FRONTMATTER_RE.match(content)
        if not match:
            return None

        raw_yaml = match.group(1)
        # Clean up trailing commas before closing braces (JS-style syntax)
        cleaned = re.sub(r",\s*}", "}", raw_yaml)
        cleaned = re.sub(r",\s*\n\s*}", "\n}", cleaned)

        try:
            data = yaml.safe_load(cleaned)
        except yaml.YAMLError:
            logger.warning("ontology.sync.yaml_parse_failed", path=path, exc_info=True)
            return None

        if not data or "stats" not in data:
            return None

        slug = path.rsplit("/", 1)[-1].removesuffix(".md")
        return CanIEmailFeature(
            slug=slug,
            title=str(data.get("title", slug)),
            category=str(data.get("category", "css")),
            last_test_date=str(data.get("last_test_date", "")),
            stats=data.get("stats", {}),
            notes={str(k): str(v) for k, v in (data.get("notes_by_num") or {}).items()},
        )
