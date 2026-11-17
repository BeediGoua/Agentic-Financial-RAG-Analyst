from __future__ import annotations

import ipaddress
import os
import re
from typing import Any, Protocol
from urllib.parse import urljoin, urlsplit

from requests import Response


class HttpClient(Protocol):
    def get(self, url: str, **kwargs: Any) -> Response: ...


BRVM_HTML_HOSTS = frozenset({"brvm.org", "www.brvm.org"})
RICHBOURSE_HOSTS = frozenset({"richbourse.com", "www.richbourse.com"})
REDIRECT_STATUS_CODES = frozenset({301, 302, 303, 307, 308})
MAX_REDIRECTS = 5


def configured_pdf_hosts() -> frozenset[str]:
    """Return BRVM hosts plus explicitly reviewed PDF hosts from the environment."""
    hosts = set(BRVM_HTML_HOSTS)
    raw = os.getenv("BRVM_ALLOWED_PDF_HOSTS", "")

    for item in raw.split(","):
        host = item.strip().lower().rstrip(".")
        if not host:
            continue
        if (
            len(host) > 253
            or not re.fullmatch(
                r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}",
                host,
            )
        ):
            raise ValueError(f"Invalid explicitly approved PDF host: {host!r}")
        hosts.add(host)

    return frozenset(hosts)


def validate_https_url(
    url: str,
    *,
    allowed_hosts: frozenset[str],
) -> str:
    """Validate HTTPS and exact hostname membership without making a request."""
    if not isinstance(url, str) or not url:
        raise ValueError("URL must be a non-empty string")
    if any(ord(character) <= 32 for character in url):
        raise ValueError("URL contains whitespace/control characters")

    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        port = parsed.port
    except ValueError as exc:
        raise ValueError(f"Malformed URL: {url!r}") from exc

    if parsed.scheme.lower() != "https":
        raise ValueError("Only HTTPS URLs are allowed")
    if not host:
        raise ValueError("URL has no hostname")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Credentials in URLs are forbidden")
    if port not in (None, 443):
        raise ValueError("Unexpected HTTPS port")

    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("IP literal destinations are forbidden")

    if host not in allowed_hosts:
        raise ValueError(f"Unapproved destination host: {host}")

    return url


def get_trusted_response(
    session: HttpClient,
    url: str,
    *,
    allowed_hosts: frozenset[str],
    max_redirects: int = MAX_REDIRECTS,
    **request_kwargs,
) -> Response:
    """Request a trusted URL, validating each redirect before following it."""
    if max_redirects < 0:
        raise ValueError("max_redirects must be non-negative")
    requested_redirects = request_kwargs.pop("allow_redirects", False)
    if requested_redirects is not False:
        raise ValueError("Automatic redirects are forbidden")
    verify = request_kwargs.get("verify")
    if verify is None:
        verify = getattr(session, "verify", True)
    if verify is False:
        raise ValueError("TLS certificate verification must remain enabled")

    current_url = url
    for _ in range(max_redirects + 1):
        validate_https_url(current_url, allowed_hosts=allowed_hosts)
        response = session.get(
            current_url,
            allow_redirects=False,
            **request_kwargs,
        )
        status_code = getattr(response, "status_code", 200)

        if status_code in REDIRECT_STATUS_CODES:
            location = getattr(response, "headers", {}).get("Location")
            response.close()
            if not location:
                raise ValueError(f"Redirect without Location: {current_url}")
            current_url = urljoin(current_url, location)
            continue

        try:
            response.raise_for_status()
        except Exception:
            response.close()
            raise
        return response

    raise ValueError(f"Too many redirects, maximum={max_redirects}")
