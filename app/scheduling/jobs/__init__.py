"""Scheduled job definitions — imported at startup to register with the engine."""

import app.scheduling.jobs.ontology_sync as _ontology_sync  # pyright: ignore[reportUnusedImport]
import app.scheduling.jobs.qa_sweep as _qa_sweep  # pyright: ignore[reportUnusedImport]
import app.scheduling.jobs.rendering_baselines as _rendering_baselines  # pyright: ignore[reportUnusedImport]
