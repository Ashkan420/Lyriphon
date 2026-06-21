import html
import ipaddress
import re
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_PRIVATE_HOST_SUFFIXES = (".localhost", ".local", ".internal")


def _is_private_host(hostname: str) -> bool:
    """Reject obviously-internal hosts without any network I/O.

    Avoids blocking DNS resolution on the event loop. For IP literals the
    address ranges are checked directly; bare hostnames are matched against
    well-known private/loopback names.
    """
    if not hostname:
        return True

    host = hostname.strip().lower().rstrip(".")
    if host == "localhost" or host.endswith(_PRIVATE_HOST_SUFFIXES):
        return True

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False

    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_unspecified
    )


def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        if result.scheme not in ("http", "https") or not result.netloc:
            return False
        hostname = result.hostname or ""
        if _is_private_host(hostname):
            return False
        return True
    except Exception:
        logger.debug("URL validation failed for: %s", url)
        return False

def _is_valid_image_url(url: str) -> bool:
    """
    Validates that the URL ends with a proper image extension.
    """
    if not url:
        return False

    pattern = re.compile(
        r'^(https?:\/\/).*\.(jpg|jpeg|png|webp)$',
        re.IGNORECASE
    )
    return re.match(pattern, url) is not None

def _safe_link(text: str, url: str) -> str:
    """
    Returns clickable link if URL exists, otherwise plain escaped text.
    """
    safe_text = html.escape(str(text))
    if url:
        safe_url = html.escape(str(url), quote=True)
        return f'<a href="{safe_url}">{safe_text}</a>'
    return safe_text