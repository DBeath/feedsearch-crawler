"""JSON schemas for API output validation.

These schemas define the structure of serialized outputs from the public API.
They ensure backward compatibility and API stability.
"""

# FeedInfo schema - matches output from FeedInfo.serialize()
# Based on README documentation and FeedInfo class definition
FEEDINFO_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$id": "https://feedsearch.dev/schemas/feedinfo.json",
    "title": "FeedInfo",
    "description": "Feed discovery result with metadata",
    "type": "object",
    "required": ["url", "title", "score"],
    "properties": {
        # Core feed identification
        "url": {
            "type": "string",
            "format": "uri",
            "description": "URL location of the feed",
        },
        "title": {
            "type": "string",
            "description": "Feed title",
        },
        "description": {
            "type": "string",
            "description": "Feed description",
        },
        # Feed metadata
        "version": {
            "type": "string",
            "description": "Feed format version (rss20, atom10, json, etc.)",
        },
        "score": {
            "type": "integer",
            "minimum": 0,
            "description": "Relevance score (higher = more relevant)",
        },
        "bozo": {
            "type": "integer",
            "enum": [0, 1],
            "description": "1 if feed is malformed, 0 if well-formed",
        },
        # Content metadata
        "item_count": {
            "type": "integer",
            "minimum": 0,
            "description": "Number of items currently in feed",
        },
        "last_updated": {
            "type": ["string", "null"],
            "format": "date-time",
            "description": "ISO 8601 datetime of latest entry",
        },
        "velocity": {
            "type": "number",
            "minimum": 0,
            "description": "Mean items per day",
        },
        # Site metadata
        "site_name": {
            "type": "string",
            "description": "Name of feed's website",
        },
        "site_url": {
            "type": ["string", "null"],
            "format": "uri",
            "description": "URL of feed's website",
        },
        "favicon": {
            "type": ["string", "null"],
            "format": "uri",
            "description": "URL of site favicon",
        },
        # WebSub/PubSubHubbub
        "is_push": {
            "type": "boolean",
            "description": "True if feed has WebSub support",
        },
        "hubs": {
            "type": "array",
            "items": {"type": "string", "format": "uri"},
            "description": "List of WebSub hub URLs",
        },
        "self_url": {
            "type": ["string", "null"],
            "format": "uri",
            "description": 'rel="self" URL from feed',
        },
        # Additional metadata (not in README but in serialize())
        "content_type": {
            "type": "string",
            "description": "HTTP Content-Type of feed",
        },
        "content_length": {
            "type": "integer",
            "minimum": 0,
            "description": "Feed size in bytes",
        },
        "favicon_data_uri": {
            "type": "string",
            "description": "Favicon as Data URI",
        },
        "is_podcast": {
            "type": "boolean",
            "description": "True if feed contains podcast elements",
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
