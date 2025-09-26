"""Custom exceptions used by the Weibo crawler package."""


class WeiboCrawlerError(Exception):
    """Base exception for crawler related failures."""


class UnexpectedResponseFormat(WeiboCrawlerError):
    """Raised when the API response payload does not match expectations."""


class AuthenticationRequired(WeiboCrawlerError):
    """Raised when the crawler receives a response that indicates authentication is required."""
