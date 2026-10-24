"""Positive-list HTTP diagnostics; never provider bodies, URLs or credentials."""

_HTTP_FAILURES = {
    400: "request_rejected", 401: "authentication_rejected", 402: "credits_required",
    403: "access_denied", 404: "route_not_found", 408: "request_timeout",
    422: "request_rejected", 429: "provider_rate_limit", 500: "provider_failure",
    502: "provider_failure", 503: "provider_unavailable", 504: "provider_timeout",
}


def http_failure_metadata(error):
    status = getattr(error, "http_status", None)
    if type(status) is not int or not 400 <= status <= 599:
        return {}
    return {"http_status": status, "transport_failure": _HTTP_FAILURES.get(status, "provider_http_error")}
