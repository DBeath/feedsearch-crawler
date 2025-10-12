"""Tests for API serialization and schema validation.

These tests ensure that the public API outputs remain consistent
and conform to documented schemas.
"""

from datetime import datetime, timezone

import jsonschema
import pytest
from yarl import URL

from feedsearch_crawler.feed_spider.feed_info import FeedInfo
from feedsearch_crawler.feed_spider.site_meta import SiteMeta
from feedsearch_crawler.schemas import FEEDINFO_SCHEMA, SITEMETA_SCHEMA


class TestFeedInfoSerialization:
    """Test FeedInfo.serialize() output format and consistency."""

    def test_serialize_minimal_feedinfo(self):
        """Test serialization with only required fields."""
        feed = FeedInfo(url=URL("https://example.com/feed.xml"))

        result = feed.serialize()

        # Verify it's a dictionary
        assert isinstance(result, dict)

        # Verify URL is converted to string
        assert result["url"] == "https://example.com/feed.xml"
        assert isinstance(result["url"], str)

    def test_serialize_complete_feedinfo(self):
        """Test serialization with all fields populated."""
        feed = FeedInfo(
            url=URL("https://example.com/feed.xml"),
            title="Test Feed",
            description="A test feed for validation",
            version="rss20",
            score=42,
            bozo=0,
            item_count=10,
            last_updated=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            velocity=2.5,
            site_name="Example Site",
            site_url=URL("https://example.com"),
            favicon=URL("https://example.com/favicon.ico"),
            favicon_data_uri="data:image/png;base64,ABC123",
            is_push=True,
            hubs=["https://hub.example.com"],
            self_url=URL("https://example.com/feed.xml"),
            is_podcast=False,
            content_type="application/rss+xml",
            content_length=5000,
        )

        result = feed.serialize()

        # Verify all documented fields are present (from README)
        assert result["url"] == "https://example.com/feed.xml"
        assert result["title"] == "Test Feed"
        assert result["description"] == "A test feed for validation"
        assert result["version"] == "rss20"
        assert result["score"] == 42
        assert result["bozo"] == 0
        assert result["item_count"] == 10
        assert result["last_updated"] == "2025-01-01T12:00:00+00:00"
        assert result["velocity"] == 2.5
        assert result["site_name"] == "Example Site"
        assert result["site_url"] == "https://example.com"
        assert result["favicon"] == "https://example.com/favicon.ico"
        assert result["is_push"] is True
        assert result["hubs"] == ["https://hub.example.com"]
        assert result["self_url"] == "https://example.com/feed.xml"

    def test_serialize_handles_none_urls(self):
        """Test serialization when optional URL fields are None."""
        feed = FeedInfo(
            url=URL("https://example.com/feed.xml"),
            site_url=None,
            favicon=None,
            self_url=None,
        )

        result = feed.serialize()

        assert result["site_url"] is None
        assert result["favicon"] is None
        assert result["self_url"] is None

    def test_serialize_handles_none_datetime(self):
        """Test serialization when last_updated is None."""
        feed = FeedInfo(url=URL("https://example.com/feed.xml"), last_updated=None)

        result = feed.serialize()

        assert result["last_updated"] is None

    def test_serialize_datetime_format(self):
        """Test that datetime is serialized as ISO 8601."""
        dt = datetime(2025, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        feed = FeedInfo(url=URL("https://example.com/feed.xml"), last_updated=dt)

        result = feed.serialize()

        assert result["last_updated"] == "2025-01-15T10:30:45+00:00"
        assert isinstance(result["last_updated"], str)

    def test_serialize_all_required_fields_present(self):
        """Test that all fields mentioned in README are in serialize() output."""
        feed = FeedInfo(url=URL("https://example.com/feed.xml"))

        result = feed.serialize()

        # All fields from README FeedInfo Values section
        expected_fields = [
            "url",
            "title",
            "description",
            "version",
            "score",
            "bozo",
            "item_count",
            "last_updated",
            "velocity",
            "site_name",
            "site_url",
            "favicon",
            "is_push",
            "hubs",
            "self_url",
        ]

        for field in expected_fields:
            assert field in result, f"Missing field: {field}"

    def test_serialize_output_types(self):
        """Test that serialize() output has correct types."""
        feed = FeedInfo(
            url=URL("https://example.com/feed.xml"),
            title="Test",
            score=10,
            velocity=2.5,
            hubs=["https://hub1.com", "https://hub2.com"],
            is_push=True,
            bozo=0,
        )

        result = feed.serialize()

        assert isinstance(result["url"], str)
        assert isinstance(result["title"], str)
        assert isinstance(result["score"], int)
        assert isinstance(result["velocity"], float)
        assert isinstance(result["hubs"], list)
        assert isinstance(result["is_push"], bool)
        assert isinstance(result["bozo"], int)


class TestFeedInfoSchemaValidation:
    """Test FeedInfo serialization against JSON schema."""

    def test_minimal_feedinfo_validates(self):
        """Test that minimal FeedInfo passes schema validation."""
        feed = FeedInfo(url=URL("https://example.com/feed.xml"))

        result = feed.serialize()

        # Should not raise ValidationError
        jsonschema.validate(instance=result, schema=FEEDINFO_SCHEMA)

    def test_complete_feedinfo_validates(self):
        """Test that complete FeedInfo passes schema validation."""
        feed = FeedInfo(
            url=URL("https://example.com/feed.xml"),
            title="Test Feed",
            description="Description",
            version="atom10",
            score=50,
            bozo=0,
            item_count=5,
            last_updated=datetime(2025, 1, 1, tzinfo=timezone.utc),
            velocity=1.5,
            site_name="Site",
            site_url=URL("https://example.com"),
            favicon=URL("https://example.com/favicon.ico"),
            favicon_data_uri="data:image/png;base64,ABC",
            is_push=False,
            hubs=[],
            self_url=URL("https://example.com/feed.xml"),
            is_podcast=True,
            content_type="application/atom+xml",
            content_length=1000,
        )

        result = feed.serialize()

        jsonschema.validate(instance=result, schema=FEEDINFO_SCHEMA)

    def test_podcast_feed_validates(self):
        """Test podcast feed serialization validates."""
        feed = FeedInfo(
            url=URL("https://example.com/podcast.xml"),
            title="Test Podcast",
            is_podcast=True,
            version="rss20",
            score=30,
        )

        result = feed.serialize()

        jsonschema.validate(instance=result, schema=FEEDINFO_SCHEMA)

    def test_json_feed_validates(self):
        """Test JSON feed serialization validates."""
        feed = FeedInfo(
            url=URL("https://example.com/feed.json"),
            version="json",
            is_push=True,
            hubs=["https://hub.example.com"],
        )

        result = feed.serialize()

        jsonschema.validate(instance=result, schema=FEEDINFO_SCHEMA)

    def test_schema_rejects_invalid_bozo(self):
        """Test schema rejects invalid bozo values."""
        result = {
            "url": "https://example.com/feed.xml",
            "title": "",
            "score": 10,
            "bozo": 2,  # Invalid - must be 0 or 1
            "description": "",
            "site_name": "",
            "site_url": None,
            "favicon": None,
            "version": "",
            "velocity": 0,
            "last_updated": None,
            "item_count": 0,
            "is_push": False,
            "hubs": [],
            "self_url": None,
        }

        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=result, schema=FEEDINFO_SCHEMA)

    def test_schema_rejects_negative_score(self):
        """Test schema rejects negative score."""
        result = {
            "url": "https://example.com/feed.xml",
            "title": "",
            "score": -1,  # Invalid
            "description": "",
            "site_name": "",
            "site_url": None,
            "favicon": None,
            "version": "",
            "bozo": 0,
            "velocity": 0,
            "last_updated": None,
            "item_count": 0,
            "is_push": False,
            "hubs": [],
            "self_url": None,
        }

        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=result, schema=FEEDINFO_SCHEMA)


class TestSiteMetaSerialization:
    """Test SiteMeta.serialize() output format."""

    def test_serialize_minimal_sitemeta(self):
        """Test serialization with minimal fields."""
        meta = SiteMeta(url=URL("https://example.com"))

        result = meta.serialize()

        assert isinstance(result, dict)
        assert result["url"] == "https://example.com"
        assert isinstance(result["url"], str)

    def test_serialize_complete_sitemeta(self):
        """Test serialization with all fields populated."""
        meta = SiteMeta(url=URL("https://example.com"))
        meta.site_name = "Example Site"
        meta.icon_url = URL("https://example.com/icon.png")

        result = meta.serialize()

        assert result["url"] == "https://example.com"
        assert result["site_name"] == "Example Site"
        assert result["icon_url"] == "https://example.com/icon.png"

    def test_serialize_handles_none_icon_url(self):
        """Test serialization when icon_url is None."""
        meta = SiteMeta(url=URL("https://example.com"))
        meta.icon_url = None

        result = meta.serialize()

        assert result["icon_url"] is None

    def test_serialize_required_fields(self):
        """Test that required fields are present."""
        meta = SiteMeta(url=URL("https://example.com"))

        result = meta.serialize()

        assert "url" in result
        assert "site_name" in result
        assert "icon_url" in result


class TestSiteMetaSchemaValidation:
    """Test SiteMeta serialization against JSON schema."""

    def test_minimal_sitemeta_validates(self):
        """Test minimal SiteMeta validates."""
        meta = SiteMeta(url=URL("https://example.com"))

        result = meta.serialize()

        jsonschema.validate(instance=result, schema=SITEMETA_SCHEMA)

    def test_complete_sitemeta_validates(self):
        """Test complete SiteMeta validates."""
        meta = SiteMeta(url=URL("https://example.com"))
        meta.site_name = "Example"
        meta.icon_url = URL("https://example.com/icon.png")

        result = meta.serialize()

        jsonschema.validate(instance=result, schema=SITEMETA_SCHEMA)


class TestBackwardCompatibility:
    """Test that serialization maintains backward compatibility."""

    def test_feedinfo_has_readme_example_fields(self):
        """Test that FeedInfo.serialize() includes fields from README example."""
        # From README line 42 example output
        feed = FeedInfo(
            url=URL("https://xkcd.com/rss.xml"),
            title="xkcd.com",
            description="xkcd.com: A webcomic of romance and math humor.",
            version="rss20",
            score=24,
            site_url=URL("https://xkcd.com/"),
            site_name="xkcd: Chernobyl",
            favicon=URL("https://xkcd.com/s/919f27.ico"),
            content_type="text/xml; charset=UTF-8",
            bozo=0,
            content_length=2847,
            is_push=False,
            self_url=URL(""),
            favicon_data_uri="",
            hubs=[],
        )

        result = feed.serialize()

        # All fields from README example must be present
        assert "url" in result
        assert "title" in result
        assert "version" in result
        assert "score" in result
        assert "hubs" in result
        assert "description" in result
        assert "is_push" in result
        assert "self_url" in result
        assert "favicon" in result
        assert "content_type" in result
        assert "bozo" in result
        assert "site_url" in result
        assert "site_name" in result
        assert "favicon_data_uri" in result
        assert "content_length" in result

    def test_all_readme_documented_fields_exist(self):
        """Test that all fields documented in README exist in serialization.

        README documents these FeedInfo fields:
        - bozo, content_length, content_type, description, favicon
        - favicon_data_uri, hubs, is_podcast, is_push, item_count
        - last_updated, score, self_url, site_name, site_url
        - title, url, velocity, version
        """
        feed = FeedInfo(url=URL("https://example.com/feed.xml"))
        result = feed.serialize()

        readme_fields = [
            "bozo",
            "content_length",
            "content_type",
            "description",
            "favicon",
            "favicon_data_uri",
            "hubs",
            "is_podcast",
            "is_push",
            "item_count",
            "last_updated",
            "score",
            "self_url",
            "site_name",
            "site_url",
            "title",
            "url",
            "velocity",
            "version",
        ]

        for field in readme_fields:
            assert field in result, (
                f"Field '{field}' documented in README but missing from serialize()"
            )
