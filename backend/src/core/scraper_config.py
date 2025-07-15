"""
Configuration for the Discogs marketplace scraper.

This module provides configuration settings for the web scraper,
allowing customization of timeouts, retries, and rate limiting.
"""

from pydantic import BaseModel, ConfigDict, Field


class ScraperConfig(BaseModel):
    """Configuration for marketplace scraper."""

    # Rate limiting
    min_request_interval: float = Field(
        default=2.0, description="Minimum seconds between requests to respect rate limits", ge=0.5, le=10.0
    )

    # Retry configuration
    max_retries: int = Field(default=3, description="Maximum number of retry attempts for failed requests", ge=1, le=5)
    retry_delay: float = Field(default=5.0, description="Seconds to wait between retry attempts", ge=1.0, le=60.0)

    # Timeouts
    page_load_timeout: int = Field(default=30000, description="Page load timeout in milliseconds", ge=10000, le=60000)
    selector_timeout: int = Field(
        default=20000, description="Element selector timeout in milliseconds", ge=5000, le=30000
    )

    # Browser configuration
    headless: bool = Field(default=True, description="Run browser in headless mode")
    block_resources: bool = Field(default=True, description="Block images, CSS, and fonts to speed up scraping")

    # Monitoring
    enable_monitoring: bool = Field(default=True, description="Enable performance monitoring and alerting")
    alert_consecutive_failures: int = Field(
        default=5, description="Number of consecutive failures before alerting", ge=3, le=10
    )
    alert_failure_rate: float = Field(
        default=0.3, description="Failure rate threshold for alerting (0.0-1.0)", ge=0.1, le=0.5
    )

    model_config = ConfigDict(validate_assignment=True)


# Default configuration instance
default_scraper_config = ScraperConfig()


def get_scraper_config() -> ScraperConfig:
    """
    Get scraper configuration.

    In production, this could load from:
    - Environment variables
    - Configuration file
    - Database settings
    - Remote configuration service
    """
    # For now, return default configuration
    # In production, implement loading from external sources
    return default_scraper_config
