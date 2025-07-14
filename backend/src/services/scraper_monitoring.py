"""
Monitoring and alerting for the Discogs marketplace scraper.

This module provides monitoring capabilities for production scraping operations,
including metrics collection, error tracking, and alerting.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

from src.core.logging import get_logger

logger = get_logger(__name__)


class ScraperMonitor:
    """Monitor scraper performance and health."""

    def __init__(self) -> None:
        self.metrics: dict[str, Any] = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_items_scraped": 0,
            "average_response_time": 0.0,
            "last_success_time": None,
            "last_failure_time": None,
            "consecutive_failures": 0,
            "error_types": {},
        }
        self._response_times: list[float] = []
        self._max_response_times = 100  # Keep last 100 response times

    async def record_request_start(self) -> float:
        """Record the start of a scraping request."""
        self.metrics["total_requests"] += 1
        return datetime.now(UTC).timestamp()

    async def record_request_success(self, start_time: float, items_count: int, query: str) -> None:
        """Record a successful scraping request."""
        end_time = datetime.now(UTC).timestamp()
        response_time = end_time - start_time

        self.metrics["successful_requests"] += 1
        self.metrics["total_items_scraped"] += items_count
        self.metrics["last_success_time"] = datetime.now(UTC)
        self.metrics["consecutive_failures"] = 0

        # Update response times
        self._response_times.append(response_time)
        if len(self._response_times) > self._max_response_times:
            self._response_times.pop(0)

        # Calculate average response time
        if self._response_times:
            self.metrics["average_response_time"] = sum(self._response_times) / len(self._response_times)

        logger.info(f"Scraping success - Query: {query}, Items: {items_count}, Response time: {response_time:.2f}s")

    async def record_request_failure(self, start_time: float, error: str, error_type: str, query: str) -> None:
        """Record a failed scraping request."""
        self.metrics["failed_requests"] += 1
        self.metrics["last_failure_time"] = datetime.now(UTC)
        self.metrics["consecutive_failures"] += 1

        # Track error types
        if error_type not in self.metrics["error_types"]:
            self.metrics["error_types"][error_type] = 0
        self.metrics["error_types"][error_type] += 1

        logger.error(
            f"Scraping failure - Query: {query}, Error type: {error_type}, "
            f"Error: {error}, Consecutive failures: {self.metrics['consecutive_failures']}"
        )

        # Check if we need to alert
        await self._check_alert_conditions()

    async def _check_alert_conditions(self) -> None:
        """Check if any alert conditions are met."""
        # Alert if too many consecutive failures
        if self.metrics["consecutive_failures"] >= 5:
            await self._send_alert(
                "High consecutive failures", f"Scraper has failed {self.metrics['consecutive_failures']} times in a row"
            )

        # Alert if failure rate is too high
        if self.metrics["total_requests"] > 10:
            failure_rate = self.metrics["failed_requests"] / self.metrics["total_requests"]
            if failure_rate > 0.3:  # More than 30% failure rate
                await self._send_alert("High failure rate", f"Scraper failure rate is {failure_rate:.1%}")

        # Alert if response time is too high
        if self.metrics["average_response_time"] > 10.0:  # More than 10 seconds average
            await self._send_alert(
                "High response time", f"Average response time is {self.metrics['average_response_time']:.1f} seconds"
            )

    async def _send_alert(self, alert_type: str, message: str) -> None:
        """Send an alert (implement actual alerting mechanism)."""
        logger.critical(f"ALERT - {alert_type}: {message}")
        # In production, this would send to:
        # - Email
        # - Slack/Discord
        # - PagerDuty
        # - Monitoring service (Datadog, New Relic, etc.)

    def get_metrics(self) -> dict[str, Any]:
        """Get current metrics."""
        return self.metrics.copy()

    def get_health_status(self) -> dict[str, Any]:
        """Get current health status of the scraper."""
        if self.metrics["total_requests"] == 0:
            success_rate = 0.0
        else:
            success_rate = self.metrics["successful_requests"] / self.metrics["total_requests"]

        # Determine health status
        if self.metrics["consecutive_failures"] >= 5:
            status = "critical"
        elif self.metrics["consecutive_failures"] >= 3:
            status = "warning"
        elif success_rate < 0.7:
            status = "degraded"
        else:
            status = "healthy"

        return {
            "status": status,
            "success_rate": success_rate,
            "consecutive_failures": self.metrics["consecutive_failures"],
            "average_response_time": self.metrics["average_response_time"],
            "last_success": self.metrics["last_success_time"],
            "last_failure": self.metrics["last_failure_time"],
            "total_requests": self.metrics["total_requests"],
        }


# Global instance for monitoring
scraper_monitor = ScraperMonitor()


async def log_scraper_metrics_periodically() -> None:
    """Log scraper metrics periodically for monitoring."""
    while True:
        await asyncio.sleep(300)  # Log every 5 minutes
        metrics = scraper_monitor.get_metrics()
        health = scraper_monitor.get_health_status()

        logger.info(
            f"Scraper metrics - Status: {health['status']}, "
            f"Success rate: {health['success_rate']:.1%}, "
            f"Total requests: {metrics['total_requests']}, "
            f"Items scraped: {metrics['total_items_scraped']}"
        )
