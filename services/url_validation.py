import html
import ipaddress
import re
import socket
from urllib.parse import urlparse

def _is_private_host(hostname: str) -> bool:
    try:
        for info in socket.getaddrinfo(hostname, None):
            addr = info[4][0]
            ip = ipaddress.ip_address(addr)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return True
    except (socket.gaierror, ValueError):
        pass
    return False


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