"""Tests for FeedInfo field validation.

Tests that FeedInfo validates field values in __post_init__
and that serialize() properly handles None URL values.
"""

import pytest
from yarl import URL

from feedsearch_crawler.feed_spider.feed_info import FeedInfo


class TestFeedInfoValidation:
    """Test FeedInfo field validation."""

    def test_valid_bozo_zero(self):
        """Test that bozo=0 is valid."""
        feed = FeedInfo(url=URL("https://example.com/feed.xml"), bozo=0)
        assert feed.bozo == 0

    def test_valid_bozo_one(self):
        """Test that bozo=1 is valid."""
        feed = FeedInfo(url=URL("https://example.com/feed.xml"), bozo=1)
        assert feed.bozo == 1

    def test_invalid_bozo_negative(self):
        """Test that bozo=-1 raises ValueError."""
        with pytest.raises(ValueError, match="bozo must be 0 or 1"):
            FeedInfo(url=URL("https://example.com/feed.xml"), bozo=-1)

    def test_invalid_bozo_two(self):
        """Test that bozo=2 raises ValueError."""
        with pytest.raises(ValueError, match="bozo must be 0 or 1"):
            FeedInfo(url=URL("https://example.com/feed.xml"), bozo=2)

    def test_valid_score_zero(self):
        """Test that score=0 is valid."""
        feed = FeedInfo(url=URL("https://example.com/feed.xml"), score=0)
        assert feed.score == 0

    def test_valid_score_positive(self):
        """Test that positive scores are valid."""
        feed = FeedInfo(url=URL("https://example.com/feed.xml"), score=100)
        assert feed.score == 100

    def test_invalid_score_negative(self):
        """Test that negative score raises ValueError."""
        with pytest.raises(ValueError, match="score must be >= 0"):
            FeedInfo(url=URL("https://example.com/feed.xml"), score=-1)

    def test_valid_item_count_zero(self):
        """Test that item_count=0 is valid."""
        feed = FeedInfo(url=URL("https://example.com/feed.xml"), item_count=0)
        assert feed.item_count == 0

    def test_valid_item_count_positive(self):
        """Test that positive item_count is valid."""
        feed = FeedInfo(url=URL("https://example.com/feed.xml"), item_count=50)
        assert feed.item_count == 50

    def test_invalid_item_count_negative(self):
        """Test that negative item_count raises ValueError."""
        with pytest.raises(ValueError, match="item_count must be >= 0"):
            FeedInfo(url=URL("https://example.com/feed.xml"), item_count=-1)

    def test_valid_content_length_zero(self):
        """Test that content_length=0 is valid."""
        feed = FeedInfo(url=URL("https://example.com/feed.xml"), content_length=0)
        assert feed.content_length == 0

    def test_valid_content_length_positive(self):
        """Test that positive content_length is valid."""
        feed = FeedInfo(url=URL("https://example.com/feed.xml"), content_length=1024)
        assert feed.content_length == 1024

    def test_invalid_content_length_negative(self):
        """Test that negative content_length raises ValueError."""
        with pytest.raises(ValueError, match="content_length must be >= 0"):
            FeedInfo(url=URL("https://example.com/feed.xml"), content_length=-1)

    def test_valid_velocity_zero(self):
        """Test that velocity=0 is valid."""
        feed = FeedInfo(url=URL("https://example.com/feed.xml"), velocity=0.0)
        assert feed.velocity == 0.0

    def test_valid_velocity_positive(self):
        """Test that positive velocity is valid."""
        feed = FeedInfo(url=URL("https://example.com/feed.xml"), velocity=2.5)
        assert feed.velocity == 2.5

    def test_invalid_velocity_negative(self):
        """Test that negative velocity raises ValueError."""
        with pytest.raises(ValueError, match="velocity must be >= 0"):
            FeedInfo(url=URL("https://example.com/feed.xml"), velocity=-1.0)


class TestFeedInfoSerializeNoneHandling:
    """Test serialize() properly handles None URL values."""

    def test_serialize_none_url(self):
        """Test that None url serializes as None, not 'None'."""
        feed = FeedInfo(url=None)
        result = feed.serialize()
        assert result["url"] is None
        assert result["url"] != "None"

    def test_serialize_valid_url(self):
        """Test that valid URL serializes as string."""
        feed = FeedInfo(url=URL("https://example.com/feed.xml"))
        result = feed.serialize()
        assert result["url"] == "https://example.com/feed.xml"
        assert isinstance(result["url"], str)

    def test_serialize_none_site_url(self):
        """Test that None site_url serializes as None."""
        feed = FeedInfo(url=URL("https://example.com/feed.xml"), site_url=None)
        result = feed.serialize()
        assert result["site_url"] is None

    def test_serialize_valid_site_url(self):
        """Test that valid site_url serializes as string."""
        feed = FeedInfo(
            url=URL("https://example.com/feed.xml"),
            site_url=URL("https://example.com"),
        )
        result = feed.serialize()
        assert result["site_url"] == "https://example.com"

    def test_serialize_none_favicon(self):
        """Test that None favicon serializes as None."""
        feed = FeedInfo(url=URL("https://example.com/feed.xml"), favicon=None)
        result = feed.serialize()
        assert result["favicon"] is None

    def test_serialize_valid_favicon(self):
        """Test that valid favicon serializes as string."""
        feed = FeedInfo(
            url=URL("https://example.com/feed.xml"),
            favicon=URL("https://example.com/favicon.ico"),
        )
        result = feed.serialize()
        assert result["favicon"] == "https://example.com/favicon.ico"

    def test_serialize_none_self_url(self):
        """Test that None self_url serializes as None."""
        feed = FeedInfo(url=URL("https://example.com/feed.xml"), self_url=None)
        result = feed.serialize()
        assert result["self_url"] is None

    def test_serialize_valid_self_url(self):
        """Test that valid self_url serializes as string."""
        feed = FeedInfo(
            url=URL("https://example.com/feed.xml"),
            self_url=URL("https://example.com/rss"),
        )
        result = feed.serialize()
        assert result["self_url"] == "https://example.com/rss"


class TestFeedInfoSerializeFieldOrder:
    """Test that serialize() returns fields in consistent order."""

    def test_serialize_field_order(self):
        """Test that serialized fields appear in documented order."""
        feed = FeedInfo(
            url=URL("https://example.com/feed.xml"),
            title="Test Feed",
            description="Test Description",
            version="rss20",
            item_count=10,
            velocity=1.5,
            site_name="Test Site",
            site_url=URL("https://example.com"),
            favicon=URL("https://example.com/favicon.ico"),
            is_push=True,
            is_podcast=False,
            content_type="text/xml",
            content_length=1024,
            bozo=0,
            score=50,
        )
        result = feed.serialize()

        # Get list of keys in order
        keys = list(result.keys())

        # Core identification should come first
        assert keys[0] == "url"
        assert keys[1] == "title"
        assert keys[2] == "description"
        assert keys[3] == "version"

        # Content metadata
        assert "item_count" in keys[4:7]
        assert "velocity" in keys[4:7]

        # Site metadata
        assert "site_name" in keys[7:11]
        assert "site_url" in keys[7:11]
        assert "favicon" in keys[7:11]

        # Score should be last
        assert keys[-1] == "score"
