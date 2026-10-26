"""Positive-list failure diagnostics; never provider bodies or credentials."""
from types import SimpleNamespace

_HTTP_FAILURES = {
    400: "request_rejected", 401: "authentication_rejected", 402: "credits_required",
    403: "access_denied", 404: "route_not_found", 408: "request_timeout",
    422: "request_rejected", 429: "provider_rate_limit", 500: "provider_failure",
    502: "provider_failure", 503: "provider_unavailable", 504: "provider_timeout",
}
_RESPONSE_ISSUES = frozenset({
    "malformed_envelope", "token_limit", "unexpected_finish", "empty_content",
    "invalid_content", "content_limit", "unexpected_cost", "provider_error",
    "content_blocked",
    "invalid_json", "invalid_schema",
})


def http_failure_metadata(error):
    status = getattr(error, "http_status", None)
    if type(status) is not int or not 400 <= status <= 599:
        return {}
    return {"http_status": status, "transport_failure": _HTTP_FAILURES.get(status, "provider_http_error")}


def provider_failure_metadata(error):
    metadata = http_failure_metadata(error)
    issue = getattr(error, "response_issue", None)
    if isinstance(issue, str) and issue in _RESPONSE_ISSUES:
        metadata["response_issue"] = issue
        # A code in an HTTP-200 error envelope is NOT the HTTP status. Keep
        # them separate; unknown codes/messages/metadata are never exported.
        code = getattr(error, "provider_error_code", None)
        if issue == "provider_error" and type(code) is int and code in _HTTP_FAILURES:
            metadata.update(provider_error_code=code, provider_failure=_HTTP_FAILURES[code])
    return metadata


def provider_result_failure_metadata(value):
    """Revalidate returned diagnostics; ignore supplied categories/raw fields."""
    if not isinstance(value, dict):
        return {}
    return provider_failure_metadata(SimpleNamespace(**{
        key: value.get(key) for key in ("http_status", "response_issue", "provider_error_code")}))
