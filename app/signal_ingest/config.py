"""Configuration for the IRIS-SIG-40 source ingestion."""

SOURCE_NAME = "The Register"

# The endpoint named in the assignment currently returns HTTP 404. It is kept
# here so the fallback is visible and can be documented in run output.
LEGACY_FEED_URL = "https://www.theregister.com/data_centre/headlines.atom"

# Current official feed used for the initial implementation and fixture review.
DEFAULT_FEED_URL = (
    "https://api.theregister.com/api/v1/article"
    "?limit=25&orderBy=published&query=tag%3Ahpc"
    "&remapper=rss&site_id=2"
)

DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_PAGE_SIZE = 25
DEFAULT_MAX_PAGES = 100
DEFAULT_RETRY_ATTEMPTS = 3
PAGINATION_PARAMETER = "start"

USER_AGENT = (
    "IRIS-SIG-40-signal-ingest/1.0 "
    "(lawful public-feed ingestion for an engineering assignment)"
)
