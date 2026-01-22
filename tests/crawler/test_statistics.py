"""Tests for the statistics module."""

import asyncio
import json
import tempfile
from pathlib import Path

import pytest

from feedsearch_crawler.crawler.statistics import (
    ErrorCategory,
    PercentileTracker,
    StatisticsLevel,
    StatsCollector,
    StreamingStats,
)


class TestStreamingStats:
    """Test streaming statistics calculator."""

    def test_empty_stats(self):
        """Test stats with no values."""
        stats = StreamingStats()
        assert stats.count == 0
        assert stats.mean == 0.0
        assert stats.variance == 0.0
        assert stats.stddev == 0.0

    def test_single_value(self):
        """Test stats with one value."""
        stats = StreamingStats()
        stats.add(10.0)
        assert stats.count == 1
        assert stats.mean == 10.0
        assert stats.min_ == 10.0
        assert stats.max_ == 10.0
        assert stats.variance == 0.0

    def test_multiple_values(self):
        """Test stats with multiple values."""
        stats = StreamingStats()
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        for v in values:
            stats.add(v)

        assert stats.count == 5
        assert stats.mean == 30.0
        assert stats.min_ == 10.0
        assert stats.max_ == 50.0
        assert stats.stddev > 0  # Should have variance

    def test_incremental_calculation(self):
        """Test that stats are calculated incrementally."""
        stats = StreamingStats()
        stats.add(5.0)
        mean1 = stats.mean

        stats.add(15.0)
        mean2 = stats.mean

        assert mean1 == 5.0
        assert mean2 == 10.0


class TestPercentileTracker:
    """Test percentile tracker."""

    def test_empty_tracker(self):
        """Test tracker with no samples."""
        tracker = PercentileTracker()
        percentiles = tracker.get_percentiles()
        assert percentiles["p50"] == 0.0
        assert percentiles["p90"] == 0.0

    def test_basic_percentiles(self):
        """Test percentile calculation."""
        tracker = PercentileTracker()
        for i in range(1, 101):  # 1 to 100
            tracker.add(float(i))

        percentiles = tracker.get_percentiles()
        assert 49 <= percentiles["p50"] <= 51  # ~50
        assert 89 <= percentiles["p90"] <= 91  # ~90
        assert 94 <= percentiles["p95"] <= 96  # ~95
        assert 98 <= percentiles["p99"] <= 100  # ~99

    def test_max_samples_limit(self):
        """Test that tracker respects max_samples."""
        tracker = PercentileTracker(max_samples=100)

        # Add more than max_samples
        for i in range(1000):
            tracker.add(float(i))

        assert tracker.total_count == 1000
        assert len(tracker.samples) <= 100

    def test_reservoir_sampling(self):
        """Test that reservoir sampling maintains representative distribution."""
        tracker = PercentileTracker(max_samples=100)

        # Add values 0-999
        for i in range(1000):
            tracker.add(float(i))

        # Percentiles should still be reasonable approximations (be lenient due to sampling)
        percentiles = tracker.get_percentiles()
        assert 300 <= percentiles["p50"] <= 700  # ~500 with sampling variance
        assert 700 <= percentiles["p90"] <= 990  # ~900 with sampling variance


class TestStatsCollectorMinimal:
    """Test stats collector in minimal mode."""

    def test_minimal_initialization(self):
        """Test initialization with minimal level."""
        collector = StatsCollector(level=StatisticsLevel.MINIMAL)
        assert collector.level == StatisticsLevel.MINIMAL
        assert collector.request_duration_stats is None
        assert collector.request_duration_percentiles is None

    @pytest.mark.asyncio
    async def test_minimal_counters_only(self):
        """Test that minimal mode only tracks counters."""
        collector = StatsCollector(level=StatisticsLevel.MINIMAL)
        collector.start()

        collector.record_request_queued()
        await collector.record_request_successful(200, 100.0, 50.0, 1000)
        await collector.record_item_processed()

        stats = collector.get_stats()
        assert stats["requests"]["queued"] == 1
        assert stats["requests"]["successful"] == 1
        assert stats["items"]["processed"] == 1

        # Performance stats should not be present
        assert "performance" not in stats or not stats.get("performance")

        await collector.stop()


class TestStatsCollectorStandard:
    """Test stats collector in standard mode."""

    def test_standard_initialization(self):
        """Test initialization with standard level."""
        collector = StatsCollector(level=StatisticsLevel.STANDARD)
        assert collector.level == StatisticsLevel.STANDARD
        assert collector.request_duration_stats is not None
        assert collector.request_duration_percentiles is None  # Not in standard

    @pytest.mark.asyncio
    async def test_standard_streaming_stats(self):
        """Test that standard mode tracks streaming stats."""
        collector = StatsCollector(level=StatisticsLevel.STANDARD)
        collector.start()

        # Record multiple requests
        for i in range(10):
            await collector.record_request_successful(
                status_code=200,
                duration_ms=100.0 + i * 10,
                latency_ms=50.0 + i * 5,
                content_length=1000 + i * 100,
                host="example.com",
            )

        stats = collector.get_stats()

        # Should have performance stats
        assert "performance" in stats
        assert "request_duration_ms" in stats["performance"]
        assert stats["performance"]["request_duration_ms"]["mean"] > 0
        assert stats["performance"]["request_duration_ms"]["min"] > 0
        assert stats["performance"]["request_duration_ms"]["max"] > 0

        # Should have content stats
        assert "content" in stats
        assert stats["content"]["total_bytes"] == 10 * 1000 + sum(
            i * 100 for i in range(10)
        )

        await collector.stop()


class TestStatsCollectorDetailed:
    """Test stats collector in detailed mode."""

    def test_detailed_initialization(self):
        """Test initialization with detailed level."""
        collector = StatsCollector(level=StatisticsLevel.DETAILED)
        assert collector.level == StatisticsLevel.DETAILED
        assert collector.request_duration_stats is not None
        assert collector.request_duration_percentiles is not None

    @pytest.mark.asyncio
    async def test_detailed_percentiles(self):
        """Test that detailed mode tracks percentiles."""
        collector = StatsCollector(level=StatisticsLevel.DETAILED)
        collector.start()

        # Record enough requests for percentiles
        for i in range(100):
            await collector.record_request_successful(
                status_code=200,
                duration_ms=float(i),
                latency_ms=float(i * 0.5),
                content_length=1000,
                host="example.com",
            )

        stats = collector.get_stats()

        # Should have percentile stats
        assert "performance" in stats
        assert "request_duration_percentiles_ms" in stats["performance"]
        perc = stats["performance"]["request_duration_percentiles_ms"]
        assert "p50" in perc
        assert "p90" in perc
        assert "p95" in perc
        assert "p99" in perc

        # Percentiles should be reasonable
        assert 40 <= perc["p50"] <= 60
        assert 85 <= perc["p90"] <= 95

        await collector.stop()

    @pytest.mark.asyncio
    async def test_detailed_per_host_stats(self):
        """Test per-host statistics in detailed mode."""
        collector = StatsCollector(level=StatisticsLevel.DETAILED)
        collector.start()

        # Record requests to different hosts
        for i in range(5):
            await collector.record_request_successful(
                status_code=200,
                duration_ms=100.0,
                latency_ms=50.0,
                content_length=1000,
                host="host1.com",
            )

        for i in range(3):
            await collector.record_request_successful(
                status_code=200,
                duration_ms=200.0,
                latency_ms=100.0,
                content_length=2000,
                host="host2.com",
            )

        stats = collector.get_stats()

        # Should have per-host stats
        assert stats.__contains__("hosts")
        assert stats["hosts"].__contains__("host1.com")
        assert stats["hosts"].__contains__("host2.com")
        assert stats["hosts"]["host1.com"]["requests"] == 5
        assert stats["hosts"]["host2.com"]["requests"] == 3
        assert (
            stats["hosts"]["host1.com"]["mean_duration_ms"]
            < stats["hosts"]["host2.com"]["mean_duration_ms"]
        )

        await collector.stop()


class TestErrorCategorization:
    """Test error categorization."""

    @pytest.mark.asyncio
    async def test_error_categories(self):
        """Test different error categories are tracked."""
        collector = StatsCollector()
        collector.start()

        await collector.record_request_failed(
            ErrorCategory.NETWORK, "Connection refused", url="http://example.com"
        )
        await collector.record_request_failed(
            ErrorCategory.TIMEOUT, "Request timeout", url="http://slow.com"
        )
        await collector.record_request_failed(
            ErrorCategory.HTTP_CLIENT,
            "404 Not Found",
            status_code=404,
            url="http://missing.com",
        )
        await collector.record_request_failed(
            ErrorCategory.HTTP_SERVER,
            "500 Internal Error",
            status_code=500,
            url="http://broken.com",
        )

        stats = collector.get_stats()

        assert stats["requests"]["failed"] == 4
        assert stats["errors"]["by_category"]["network"] == 1
        assert stats["errors"]["by_category"]["timeout"] == 1
        assert stats["errors"]["by_category"]["http_client"] == 1
        assert stats["errors"]["by_category"]["http_server"] == 1

        # Should track recent errors
        assert len(stats["errors"]["recent"]) == 4

        await collector.stop()

    @pytest.mark.asyncio
    async def test_recent_errors_limit(self):
        """Test that recent errors are limited."""
        collector = StatsCollector()
        collector.max_recent_errors = 10
        collector.start()

        # Record more than max
        for i in range(20):
            await collector.record_request_failed(
                ErrorCategory.OTHER, f"Error {i}", url=f"http://test{i}.com"
            )

        # Should only keep last 10
        assert len(collector.recent_errors) == 10
        assert "Error 19" in collector.recent_errors[-1]["message"]

        await collector.stop()


class TestStatusCodeTracking:
    """Test status code tracking."""

    @pytest.mark.asyncio
    async def test_status_codes(self):
        """Test that status codes are tracked."""
        collector = StatsCollector()
        collector.start()

        await collector.record_request_successful(200, 100.0, 50.0, 1000)
        await collector.record_request_successful(200, 100.0, 50.0, 1000)
        await collector.record_request_successful(201, 100.0, 50.0, 1000)
        await collector.record_request_failed(
            ErrorCategory.HTTP_CLIENT, "Not found", status_code=404
        )
        await collector.record_request_failed(
            ErrorCategory.HTTP_SERVER, "Server error", status_code=500
        )

        stats = collector.get_stats()

        assert stats["status_codes"][200] == 2
        assert stats["status_codes"][201] == 1
        assert stats["status_codes"][404] == 1
        assert stats["status_codes"][500] == 1

        await collector.stop()


class TestSummaryMetrics:
    """Test summary metrics."""

    @pytest.mark.asyncio
    async def test_success_rate(self):
        """Test success rate calculation."""
        collector = StatsCollector()
        collector.start()

        # 8 successful, 2 failed = 80% success rate
        for i in range(8):
            await collector.record_request_successful(200, 100.0, 50.0, 1000)
        for i in range(2):
            await collector.record_request_failed(ErrorCategory.OTHER, "Error")

        stats = collector.get_stats()

        assert stats["summary"]["total_requests"] == 10
        assert stats["summary"]["success_rate"] == 0.8

        await collector.stop()

    @pytest.mark.asyncio
    async def test_requests_per_second(self):
        """Test requests per second calculation."""
        collector = StatsCollector()
        collector.start()

        # Simulate some delay
        await asyncio.sleep(0.1)

        # Record 10 requests
        for i in range(10):
            await collector.record_request_successful(200, 100.0, 50.0, 1000)

        await collector.stop()

        stats = collector.get_stats()

        # Should have reasonable RPS (depends on timing, be lenient)
        assert stats["summary"]["requests_per_second"] > 0
        assert stats["summary"]["requests_per_second"] < 1000  # Sanity check

    @pytest.mark.asyncio
    async def test_throughput_metrics(self):
        """Test bytes per second throughput."""
        collector = StatsCollector(level=StatisticsLevel.STANDARD)
        collector.start()

        await asyncio.sleep(0.1)

        # Record requests with content
        for i in range(10):
            await collector.record_request_successful(
                200, 100.0, 50.0, 10000
            )  # 10KB each

        await collector.stop()

        stats = collector.get_stats()

        assert "content" in stats
        assert stats["content"]["total_bytes"] == 100000
        assert stats["content"]["bytes_per_second"] > 0
        assert stats["content"]["megabytes_per_second"] > 0


class TestStatisticsPersistence:
    """Test statistics persistence."""

    def test_save_stats_json(self):
        """Test saving statistics to JSON."""
        collector = StatsCollector()
        collector.start()

        # Add some data
        asyncio.run(collector.record_request_successful(200, 100.0, 50.0, 1000))
        asyncio.run(collector.record_item_processed())

        # Save to temp file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            temp_path = Path(f.name)

        try:
            collector.save_stats(temp_path, format="json")

            # Verify file was created and contains valid JSON
            assert temp_path.exists()
            with open(temp_path) as f:
                data = json.load(f)
                assert "summary" in data
                assert "requests" in data
                assert data["requests"]["successful"] == 1
        finally:
            temp_path.unlink()

    def test_save_stats_csv(self):
        """Test saving statistics to CSV."""
        collector = StatsCollector()
        collector.start()

        asyncio.run(collector.record_request_successful(200, 100.0, 50.0, 1000))

        # Save to temp file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
            temp_path = Path(f.name)

        try:
            collector.save_stats(temp_path, format="csv")

            # Verify file was created
            assert temp_path.exists()
            content = temp_path.read_text()
            assert "Metric,Value" in content
            assert "summary" in content
        finally:
            temp_path.unlink()

    def test_save_stats_invalid_format(self):
        """Test error on invalid format."""
        collector = StatsCollector()

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="Unsupported format"):
                collector.save_stats(temp_path, format="xml")
        finally:
            if temp_path.exists():
                temp_path.unlink()


class TestRealTimeCallback:
    """Test real-time statistics callbacks."""

    @pytest.mark.asyncio
    async def test_callback_invoked(self):
        """Test that callback is invoked periodically."""
        callback_count = 0
        received_stats = []

        def callback(stats):
            nonlocal callback_count
            callback_count += 1
            received_stats.append(stats)

        collector = StatsCollector(
            callback=callback,
            callback_interval=0.1,  # Fast for testing
        )
        collector.start()

        # Record some data
        await collector.record_request_successful(200, 100.0, 50.0, 1000)

        # Wait for at least one callback
        await asyncio.sleep(0.3)

        await collector.stop()

        # Should have been called at least once
        assert callback_count >= 1
        assert len(received_stats) >= 1
        assert "summary" in received_stats[0]

    @pytest.mark.asyncio
    async def test_async_callback(self):
        """Test async callback function."""
        callback_count = 0

        async def async_callback(stats):
            nonlocal callback_count
            callback_count += 1
            await asyncio.sleep(0.01)  # Simulate async work

        collector = StatsCollector(
            callback=async_callback,
            callback_interval=0.1,
        )
        collector.start()

        await collector.record_request_successful(200, 100.0, 50.0, 1000)
        await asyncio.sleep(0.3)
        await collector.stop()

        assert callback_count >= 1


class TestThreadSafety:
    """Test thread safety of stats collector."""

    @pytest.mark.asyncio
    async def test_concurrent_updates(self):
        """Test concurrent statistics updates."""
        collector = StatsCollector(level=StatisticsLevel.STANDARD)
        collector.start()

        # Simulate concurrent requests
        tasks = []
        for i in range(100):
            task = collector.record_request_successful(
                status_code=200,
                duration_ms=100.0,
                latency_ms=50.0,
                content_length=1000,
                host="example.com",
            )
            tasks.append(task)

        # Execute all concurrently
        await asyncio.gather(*tasks)

        stats = collector.get_stats()
        assert stats["requests"]["successful"] == 100

        await collector.stop()

    @pytest.mark.asyncio
    async def test_concurrent_mixed_operations(self):
        """Test concurrent mixed operations."""
        collector = StatsCollector(level=StatisticsLevel.DETAILED)
        collector.start()

        # Mix of different operations
        tasks = []
        for i in range(50):
            collector.record_request_queued()  # Sync call
            tasks.append(
                collector.record_request_successful(200, 100.0, 50.0, 1000, "host.com")
            )
            tasks.append(collector.record_item_processed())
            tasks.append(collector.record_url_seen(is_duplicate=(i % 2 == 0)))

        await asyncio.gather(*tasks)

        stats = collector.get_stats()
        assert stats["requests"]["queued"] == 50
        assert stats["requests"]["successful"] == 50
        assert stats["items"]["processed"] == 50
        assert stats["urls"]["seen"] == 50
        assert stats["urls"]["duplicates_filtered"] == 25

        await collector.stop()
