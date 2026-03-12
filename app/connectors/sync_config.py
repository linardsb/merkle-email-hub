"""Configuration for ESP sync providers."""

from __future__ import annotations

from pydantic import BaseModel


class ESPSyncConfig(BaseModel):
    """Base URLs for ESP sync providers (mock or production)."""

    braze_base_url: str = "http://mock-esp:3002/braze"
    sfmc_base_url: str = "http://mock-esp:3002/sfmc"
    adobe_base_url: str = "http://mock-esp:3002/adobe"
    taxi_base_url: str = "http://mock-esp:3002/taxi"
