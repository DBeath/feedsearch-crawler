"""JSON schemas for API output validation.

These schemas define the structure of serialized outputs from the public API.
They ensure backward compatibility and API stability.

Field Validation:
- bozo: Must be 0 or 1
- score: Must be >= 0
- item_count: Must be >= 0
- content_length: Must be >= 0
- velocity: Must be >= 0
- URL fields: Can be null; if present, must be valid URIs
"""

# FeedInfo schema - matches output from FeedInfo.serialize()
# Based on README documentation and FeedInfo class definition
# Field order matches serialize() output for consistency
FEEDINFO_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$id": "https://feedsearch.dev/schemas/feedinfo.json",
    "title": "FeedInfo",
    "description": "Feed discovery result with metadata. All fields are validated on construction.",
    "type": "object",
    "required": ["url", "title", "score"],
    "properties": {
        # Core identification
        "url": {
            "type": ["string", "null"],
            "format": "uri",
            "description": "URL location of the feed (nullable)",
        },
        "title": {
            "type": "string",
            "description": "Feed title",
        },
        "description": {
            "type": "string",
            "description": "Feed description",
        },
        "version": {
            "type": "string",
            "description": "Feed format version (rss20, atom10, json, etc.)",
        },
        # Feed-declared metadata (RSS 2.0 channel / Atom feed / JSON Feed top-level)
        "link": {
            "type": ["string", "null"],
            "format": "uri",
            "description": "Website link declared by the feed itself: RSS <link>, "
            'Atom rel="alternate" link, or JSON Feed home_page_url (nullable)',
        },
        "language": {
            "type": "string",
            "description": "Feed language: RSS <language>, Atom xml:lang, "
            "or JSON Feed language",
        },
        "author": {
            "type": "string",
            "description": "Feed author name: RSS managingEditor, itunes:author, "
            "Atom <author><name>, or JSON Feed authors[0].name",
        },
        "copyright": {
            "type": "string",
            "description": "Copyright notice: RSS <copyright> or Atom <rights>",
        },
        "generator": {
            "type": "string",
            "description": "Software that generated the feed: <generator>",
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Category/tag terms: RSS <category>, Atom <category>, "
            "and itunes:category (unique, order preserved)",
        },
        "image": {
            "type": ["string", "null"],
            "format": "uri",
            "description": "Feed artwork: itunes:image, RSS <image><url>, "
            "Atom <logo>, or JSON Feed icon (nullable)",
        },
        "is_explicit": {
            "type": ["boolean", "null"],
            "description": "itunes:explicit value; null when not declared",
        },
        "new_feed_url": {
            "type": ["string", "null"],
            "format": "uri",
            "description": "itunes:new-feed-url - the feed has permanently "
            "moved to this URL (nullable)",
        },
        # Content metadata
        "item_count": {
            "type": "integer",
            "minimum": 0,
            "description": "Number of items currently in feed (validated >= 0)",
        },
        "last_updated": {
            "type": ["string", "null"],
            "format": "date-time",
            "description": "ISO 8601 datetime of latest entry",
        },
        "velocity": {
            "type": "number",
            "minimum": 0,
            "description": "Mean items per day (validated >= 0)",
        },
        # Site metadata
        "site_name": {
            "type": "string",
            "description": "Name of feed's website",
        },
        "site_url": {
            "type": ["string", "null"],
            "format": "uri",
            "description": "URL of feed's website (nullable)",
        },
        "favicon": {
            "type": ["string", "null"],
            "format": "uri",
            "description": "URL of the feed icon: Atom <icon>, JSON Feed favicon, "
            "or the site favicon as fallback (nullable)",
        },
        "favicon_data_uri": {
            "type": "string",
            "description": "Favicon as Data URI (base64 encoded)",
        },
        # Feed properties
        "is_push": {
            "type": "boolean",
            "description": "True if feed has WebSub support",
        },
        "is_podcast": {
            "type": "boolean",
            "description": "True if feed contains podcast elements",
        },
        "hubs": {
            "type": "array",
            "items": {"type": "string", "format": "uri"},
            "description": "List of WebSub hub URLs",
        },
        # Technical details
        "content_type": {
            "type": "string",
            "description": "HTTP Content-Type of feed",
        },
        "content_length": {
            "type": "integer",
            "minimum": 0,
            "description": "Feed size in bytes (validated >= 0)",
        },
        "bozo": {
            "type": "integer",
            "enum": [0, 1],
            "description": "1 if feed is malformed, 0 if well-formed (validated)",
        },
        "self_url": {
            "type": ["string", "null"],
            "format": "uri",
            "description": 'rel="self" URL from feed (nullable)',
        },
        # Scoring
        "score": {
            "type": "integer",
            "minimum": 0,
            "description": "Relevance score (higher = more relevant, validated >= 0)",
        },
    },
    "additionalProperties": False,
}

# SiteMeta schema - matches output from SiteMeta.serialize()
SITEMETA_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$id": "https://feedsearch.dev/schemas/sitemeta.json",
    "title": "SiteMeta",
    "description": "Website metadata collected during feed discovery",
    "type": "object",
    "required": ["url", "site_name"],
    "properties": {
        "url": {
            "type": "string",
            "format": "uri",
            "description": "Page URL where metadata was found",
        },
        "site_name": {
            "type": "string",
            "description": "Name of the website",
        },
        "icon_url": {
            "type": ["string", "null"],
            "format": "uri",
            "description": "URL of site icon/favicon",
        },
    },
    "additionalProperties": False,
}

# OpenAPI schema for the public API
OPENAPI_SCHEMA = {
    "openapi": "3.0.3",
    "info": {
        "title": "Feedsearch Crawler API",
        "description": "Python library for discovering RSS, Atom, and JSON feeds on websites",
        "version": "1.0.3",
        "license": {
            "name": "MIT",
            "url": "https://github.com/DBeath/feedsearch-crawler/blob/master/LICENSE",
        },
    },
    "components": {
        "schemas": {
            "FeedInfo": FEEDINFO_SCHEMA,
            "SiteMeta": SITEMETA_SCHEMA,
        }
    },
}
