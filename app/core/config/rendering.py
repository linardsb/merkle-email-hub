"""Cross-client rendering, sandbox, calibration, and change-detection settings."""

from pydantic import BaseModel


class SandboxConfig(BaseModel):
    """Headless email sandbox settings."""

    enabled: bool = False
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    mailpit_url: str = "http://localhost:8025"
    roundcube_url: str = "http://localhost:9080"
    playwright_timeout_ms: int = 15000
    from_addr: str = "sandbox@test.local"
    to_addr: str = "inbox@test.local"


class CalibrationConfig(BaseModel):
    """Emulator calibration loop settings."""

    enabled: bool = False
    rate_per_client_per_day: int = 3
    monthly_budget: float = 0.0  # 0 = disabled
    regression_threshold: float = 10.0  # % drop that triggers warning
    ema_alpha: float = 0.3
    max_history: int = 100


class RenderingConfig(BaseModel):
    """Cross-client rendering test settings."""

    provider: str = "litmus"  # litmus, eoa, mock
    litmus_api_key: str = ""
    eoa_api_key: str = ""
    poll_interval_seconds: int = 10
    poll_timeout_seconds: int = 300
    max_concurrent_tests: int = 5
    screenshot_storage_path: str = "data/screenshots"
    screenshots_enabled: bool = False
    screenshot_max_clients: int = 5
    screenshot_timeout_ms: int = 15000
    screenshot_npx_path: str = "npx"
    visual_diff_enabled: bool = False
    visual_diff_threshold: float = 0.01  # 1% pixel diff triggers regression
    visual_regression_threshold: float = 0.5  # % pixel diff that flags regression
    confidence_enabled: bool = True
    sandbox: SandboxConfig = SandboxConfig()
    calibration: CalibrationConfig = CalibrationConfig()
    # Gate settings (Phase 27.3)
    gate_mode: str = "warn"  # enforce | warn | skip
    gate_tier1_threshold: float = 85.0
    gate_tier2_threshold: float = 70.0
    gate_tier3_threshold: float = 60.0


class ChangeDetectionConfig(BaseModel):
    """Email client rendering change detection settings."""

    enabled: bool = False  # CHANGE_DETECTION__ENABLED
    interval_hours: int = 168  # Weekly default — CHANGE_DETECTION__INTERVAL_HOURS
    diff_threshold: float = 0.02  # 2% pixel diff = rendering change
    clients: list[str] = [
        "gmail_web",
        "outlook_2019",
        "apple_mail",
        "outlook_dark",
        "mobile_ios",
    ]
