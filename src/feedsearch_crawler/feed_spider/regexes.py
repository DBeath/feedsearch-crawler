import re

# Regex to check if possible RSS data.
rss_regex = re.compile("(<rss|<rdf|<feed)", re.IGNORECASE)

# Regex to check that a feed-like string is a whole word to help rule out false positives.
feedlike_regex = re.compile(
    "\\b(rss|feeds?|atom|json|xml|rdf|blogs?|subscribe)\\b", re.IGNORECASE
)

# Regex to check that a podcast string is a whole word.
podcast_regex = re.compile("\\b(podcasts?)\\b", re.IGNORECASE)

# Regex to check if the URL might contain author information.
author_regex = re.compile(
    "(authors?|journalists?|writers?|contributors?)", re.IGNORECASE
)

# Regex to check URL string for invalid file types.
file_regex = re.compile(
    ".(jpe?g|png|gif|bmp|mp4|mp3|mkv|md|css|avi|pdf|js|woff2?|svg|ttf|zip)/?$",
    re.IGNORECASE,
)

# Regex to match year and month in URLs, e.g. /2019/07/
date_regex = re.compile("/(\\d{4}/\\d{2})/")
