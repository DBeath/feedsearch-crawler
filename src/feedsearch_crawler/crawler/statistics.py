"""
Statistics collection and management for web crawler.

This module provides a thread-safe, memory-efficient statistics collector
that can track crawler performance metrics in real-time.
"""

import asyncio
import csv
import json
import logging
import math
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class StatisticsLevel(Enum):
    """Level of detail for statistics collection."""

    MINIMAL = "minimal"  # Only counters, no memory overhead
    STANDARD = "standard"  # Counters + streaming aggregates
    DETAILED = "detailed"  # Full tracking with percentiles


class ErrorCategory(Enum):
    """Categories of errors that can occur during crawling."""

    NETWORK = "network"  # DNS, connection errors
    TIMEOUT = "timeout"  # Request timeouts
    HTTP_CLIENT = "http_client"  # 4xx errors
    HTTP_SERVER = "http_server"  # 5xx errors
    PARSING = "parsing"  # Content parsing errors
    VALIDATION = "validation"  # Content validation errors
    ROBOTS = "robots"  # Blocked by robots.txt
    OTHER = "other"  # Uncategorized errors


@dataclass
class StreamingStats:
    """Streaming statistics calculator for memory-efficient aggregates."""

    count: int = 0
    sum_: float = 0.0
    sum_squares: float = 0.0
    min_: float = float("inf")
    max_: float = float("-inf")

    def add(self, value: float) -> None:
        """Add a value to the streaming statistics."""
        self.count += 1
        self.sum_ += value
        self.sum_squares += value * value
        self.min_ = min(self.min_, value)
        self.max_ = max(self.max_, value)

    @property
    def mean(self) -> float:
        """Calculate arithmetic mean."""
        return self.sum_ / self.count if self.count > 0 else 0.0

    @property
    def variance(self) -> float:
        """Calculate variance."""
        if self.count < 2:
            return 0.0
        mean_sq = (self.sum_ / self.count) ** 2
        sq_mean = self.sum_squares / self.count
        return sq_mean - mean_sq

    @property
    def stddev(self) -> float:
        """Calculate standard deviation."""
        return math.sqrt(self.variance)


@dataclass
class PercentileTracker:
    """Track values for percentile calculation with bounded memory."""

    max_samples: int = 10000
    samples: List[float] = field(default_factory=list)
    total_count: int = 0

    def add(self, value: float) -> None:
        """Add a value, maintaining max_samples limit."""
        import random

        self.total_count += 1
        if len(self.samples) < self.max_samples:
            self.samples.append(value)
        else:
            # Reservoir sampling: randomly replace with decreasing probability
            idx = random.randint(0, self.total_count - 1)
            if idx < self.max_samples:
                self.samples[idx] = value

    def percentile(self, p: float) -> float:
        """Calculate percentile (0-100)."""
        if not self.samples:
            return 0.0
        sorted_samples = sorted(self.samples)
        k = (len(sorted_samples) - 1) * (p / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_samples[int(k)]
        d0 = sorted_samples[int(f)] * (c - k)
        d1 = sorted_samples[int(c)] * (k - f)
        return d0 + d1

    def get_percentiles(self) -> Dict[str, float]:
        """Get common percentiles."""
        if not self.samples:
            return {"p50": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0}
        return {
            "p50": self.percentile(50),
            "p90": self.percentile(90),
            "p95": self.percentile(95),
            "p99": self.percentile(99),
        }


class StatsCollector:
    """
    Thread-safe statistics collector for web crawler.

    Collects performance metrics, error information, and throughput data
    with configurable detail level and minimal performance impact.
    """

    def __init__(
        self,
        level: StatisticsLevel = StatisticsLevel.STANDARD,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        callback_interval: float = 5.0,
        max_samples: int = 10000,
    ):
        """
        Initialize statistics collector.

        Args:
            level: Level of detail for statistics collection
            callback: Optional callback function for real-time stats updates
            callback_interval: Seconds between callback invocations
            max_samples: Maximum samples to keep for percentile calculations
        """
        self.level = level
        self.callback = callback
        self.callback_interval = callback_interval
        self.max_samples = max_samples

        # Lock for thread-safe updates (minimal contention with batching)
        self._lock = asyncio.Lock()

        # Basic counters (all levels)
        self.requests_queued = 0
        self.requests_successful = 0
        self.requests_failed = 0
        self.requests_retried = 0
        self.items_processed = 0
        self.urls_seen = 0
        self.duplicate_urls_filtered = 0
        self.robots_txt_blocks = 0

        # Status code tracking
        self.status_codes: Counter = Counter()

        # Error tracking with categorization
        self.errors_by_category: Counter = Counter()
        self.recent_errors: List[Dict[str, Any]] = []
        self.max_recent_errors = 100

        # Timing information
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

        # Streaming statistics (standard/detailed levels)
        self.request_duration_stats: Optional[StreamingStats] = None
        self.request_latency_stats: Optional[StreamingStats] = None
        self.content_length_stats: Optional[StreamingStats] = None
        self.queue_wait_stats: Optional[StreamingStats] = None
        self.queue_size_stats: Optional[StreamingStats] = None

        # Percentile trackers (detailed level only)
        self.request_duration_percentiles: Optional[PercentileTracker] = None
        self.request_latency_percentiles: Optional[PercentileTracker] = None

        # Per-host statistics (detailed level)
        self.host_request_counts: Counter = Counter()
        self.host_duration_stats: Dict[str, StreamingStats] = {}

        # Initialize based on level
        if level in (StatisticsLevel.STANDARD, StatisticsLevel.DETAILED):
            self.request_duration_stats = StreamingStats()
            self.request_latency_stats = StreamingStats()
            self.content_length_stats = StreamingStats()
            self.queue_wait_stats = StreamingStats()
            self.queue_size_stats = StreamingStats()

        if level == StatisticsLevel.DETAILED:
            self.request_duration_percentiles = PercentileTracker(max_samples)
            self.request_latency_percentiles = PercentileTracker(max_samples)

        # Callback task
        self._callback_task: Optional[asyncio.Task] = None
        self._should_stop = False

    def start(self) -> None:
        """Start statistics collection."""
        import time

        self.start_time = time.time()
        if self.callback:
            self._should_stop = False
            try:
                asyncio.get_running_loop()
                self._callback_task = asyncio.create_task(self._periodic_callback())
            except RuntimeError:
                # No event loop running, callback will be started manually if needed
                pass

    async def stop(self) -> None:
        """Stop statistics collection and finalize."""
        import time

        self.end_time = time.time()
        self._should_stop = True
        if self._callback_task and not self._callback_task.done():
            self._callback_task.cancel()
            try:
                await self._callback_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.debug(f"Error stopping callback task: {e}")

    async def _periodic_callback(self) -> None:
        """Periodically invoke callback with current statistics."""
        try:
            while not self._should_stop:
                await asyncio.sleep(self.callback_interval)
                if self._should_stop:
                    break
                if self.callback:
                    try:
                        stats = self.get_stats()
                        if asyncio.iscoroutinefunction(self.callback):
                            await self.callback(stats)
                        else:
                            self.callback(stats)
                    except Exception as e:
                        logger.warning(f"Error in statistics callback: {e}")
        except asyncio.CancelledError:
            # Expected when task is cancelled
            pass

    def record_request_queued(self) -> None:
        """Record a request being queued (sync method for performance)."""
        # Fast path without lock for simple counter
        self.requests_queued += 1

    async def record_request_successful(
        self,
        status_code: int,
        duration_ms: float,
        latency_ms: float,
        content_length: int,
        host: Optional[str] = None,
    ) -> None:
        """Record a successful request."""
        async with self._lock:
            self.requests_successful += 1
            self.status_codes[status_code] += 1

            if self.level in (StatisticsLevel.STANDARD, StatisticsLevel.DETAILED):
                self.request_duration_stats.add(duration_ms)
                self.request_latency_stats.add(latency_ms)
                self.content_length_stats.add(content_length)

            if self.level == StatisticsLevel.DETAILED:
                self.request_duration_percentiles.add(duration_ms)
                self.request_latency_percentiles.add(latency_ms)

                if host:
                    self.host_request_counts[host] += 1
                    if host not in self.host_duration_stats:
                        self.host_duration_stats[host] = StreamingStats()
                    self.host_duration_stats[host].add(duration_ms)

    async def record_request_failed(
        self,
        error_category: ErrorCategory,
        error_message: str,
        status_code: Optional[int] = None,
        url: Optional[str] = None,
    ) -> None:
        """Record a failed request."""
        async with self._lock:
            self.requests_failed += 1
            self.errors_by_category[error_category.value] += 1

            if status_code:
                self.status_codes[status_code] += 1

            # Keep recent errors for debugging
            error_record = {
                "timestamp": datetime.now().isoformat(),
                "category": error_category.value,
                "message": error_message,
                "status_code": status_code,
                "url": url,
            }
            self.recent_errors.append(error_record)

            # Trim to max size
            if len(self.recent_errors) > self.max_recent_errors:
                self.recent_errors = self.recent_errors[-self.max_recent_errors :]

    async def record_request_retried(self) -> None:
        """Record a request retry."""
        self.requests_retried += 1

    async def record_item_processed(self) -> None:
        """Record an item being processed."""
        self.items_processed += 1

    async def record_url_seen(self, is_duplicate: bool = False) -> None:
        """Record a URL being seen."""
        self.urls_seen += 1
        if is_duplicate:
            self.duplicate_urls_filtered += 1

    async def record_robots_block(self) -> None:
        """Record a robots.txt block."""
        self.robots_txt_blocks += 1

    async def record_queue_metrics(self, wait_time_ms: float, queue_size: int) -> None:
        """Record queue-related metrics."""
        if self.level in (StatisticsLevel.STANDARD, StatisticsLevel.DETAILED):
            async with self._lock:
                self.queue_wait_stats.add(wait_time_ms)
                self.queue_size_stats.add(queue_size)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get current statistics in grouped format.

        Returns organized dictionary with summary, requests, performance,
        content, errors, and queue sections.
        """
        import time

        current_time = self.end_time if self.end_time is not None else time.time()
        total_duration = current_time - self.start_time if self.start_time else 0.0

        # Summary section
        total_requests = self.requests_successful + self.requests_failed
        success_rate = (
            self.requests_successful / total_requests if total_requests > 0 else 0.0
        )

        stats = {
            "summary": {
                "total_duration_sec": round(total_duration, 2),
                "total_requests": total_requests,
                "success_rate": round(success_rate, 3),
                "requests_per_second": (
                    round(total_requests / total_duration, 2)
                    if total_duration > 0
                    else 0.0
                ),
            },
            "requests": {
                "queued": self.requests_queued,
                "successful": self.requests_successful,
                "failed": self.requests_failed,
                "retried": self.requests_retried,
            },
            "items": {
                "processed": self.items_processed,
            },
            "urls": {
                "seen": self.urls_seen,
                "duplicates_filtered": self.duplicate_urls_filtered,
                "robots_blocked": self.robots_txt_blocks,
            },
            "status_codes": dict(self.status_codes),
            "errors": {
                "by_category": dict(self.errors_by_category),
                "recent": self.recent_errors[-10:],  # Last 10 errors
            },
        }

        # Add performance metrics if available
        if self.level in (StatisticsLevel.STANDARD, StatisticsLevel.DETAILED):
            stats["performance"] = {}

            if self.request_duration_stats and self.request_duration_stats.count > 0:
                rd = self.request_duration_stats
                stats["performance"]["request_duration_ms"] = {
                    "mean": round(rd.mean, 2),
                    "min": round(rd.min_, 2),
                    "max": round(rd.max_, 2),
                    "stddev": round(rd.stddev, 2),
                }

            if self.request_latency_stats and self.request_latency_stats.count > 0:
                rl = self.request_latency_stats
                stats["performance"]["request_latency_ms"] = {
                    "mean": round(rl.mean, 2),
                    "min": round(rl.min_, 2),
                    "max": round(rl.max_, 2),
                    "stddev": round(rl.stddev, 2),
                }

            if self.content_length_stats and self.content_length_stats.count > 0:
                cl = self.content_length_stats
                stats["content"] = {
                    "total_bytes": int(cl.sum_),
                    "mean_bytes": int(cl.mean),
                    "min_bytes": int(cl.min_),
                    "max_bytes": int(cl.max_),
                }

                # Add throughput
                if total_duration > 0:
                    bytes_per_sec = cl.sum_ / total_duration
                    stats["content"]["bytes_per_second"] = int(bytes_per_sec)
                    stats["content"]["megabytes_per_second"] = round(
                        bytes_per_sec / 1024 / 1024, 2
                    )

            if self.queue_wait_stats and self.queue_wait_stats.count > 0:
                qw = self.queue_wait_stats
                stats["queue"] = {
                    "wait_time_ms": {
                        "mean": round(qw.mean, 2),
                        "min": round(qw.min_, 2),
                        "max": round(qw.max_, 2),
                    }
                }

            if self.queue_size_stats and self.queue_size_stats.count > 0:
                qs = self.queue_size_stats
                if "queue" not in stats:
                    stats["queue"] = {}
                stats["queue"]["size"] = {
                    "mean": round(qs.mean, 2),
                    "min": int(qs.min_),
                    "max": int(qs.max_),
                }

        # Add percentiles if in detailed mode
        if self.level == StatisticsLevel.DETAILED:
            if (
                self.request_duration_percentiles
                and self.request_duration_percentiles.samples
            ):
                perc = self.request_duration_percentiles.get_percentiles()
                if "performance" not in stats:
                    stats["performance"] = {}
                stats["performance"]["request_duration_percentiles_ms"] = {
                    k: round(v, 2) for k, v in perc.items()
                }

            if (
                self.request_latency_percentiles
                and self.request_latency_percentiles.samples
            ):
                perc = self.request_latency_percentiles.get_percentiles()
                if "performance" not in stats:
                    stats["performance"] = {}
                stats["performance"]["request_latency_percentiles_ms"] = {
                    k: round(v, 2) for k, v in perc.items()
                }

            # Add per-host stats (top 10 by count)
            if self.host_request_counts:
                top_hosts = self.host_request_counts.most_common(10)
                host_stats = {}
                for host, count in top_hosts:
                    if host in self.host_duration_stats:
                        hs = self.host_duration_stats[host]
                        host_stats[host] = {
                            "requests": count,
                            "mean_duration_ms": round(hs.mean, 2),
                        }
                stats["hosts"] = host_stats

        return stats

    def save_stats(
        self,
        filepath: Union[str, Path],
        format: str = "json",
    ) -> None:
        """
        Save statistics to file.

        Args:
            filepath: Path to output file
            format: Output format ('json' or 'csv')
        """
        stats = self.get_stats()
        filepath = Path(filepath)

        if format == "json":
            with open(filepath, "w") as f:
                json.dump(stats, f, indent=2)
        elif format == "csv":
            # Flatten statistics for CSV export
            rows = []
            self._flatten_stats(stats, rows)
            with open(filepath, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Metric", "Value"])
                writer.writerows(rows)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _flatten_stats(
        self,
        data: Any,
        rows: List[List[str]],
        prefix: str = "",
    ) -> None:
        """Recursively flatten nested statistics dictionary for CSV export."""
        if isinstance(data, dict):
            for key, value in data.items():
                new_prefix = f"{prefix}.{key}" if prefix else key
                self._flatten_stats(value, rows, new_prefix)
        elif isinstance(data, list):
            rows.append([prefix, f"[{len(data)} items]"])
        else:
            rows.append([prefix, str(data)])
