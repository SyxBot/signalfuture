class GMGNError(Exception):
    """Base GMGN API error."""


class AuthError(GMGNError):
    """Invalid or missing API token."""


class RateLimitError(GMGNError):
    """429 rate limit hit."""


class ParseError(GMGNError):
    """Unexpected response shape."""
