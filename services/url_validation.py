import re

def is_valid_url(url: str) -> bool:
    pattern = re.compile(
        r'^(https?:\/\/)'          # http:// or https://
        r'([\w\-]+\.)+[\w\-]+'     # domain
        r'([\/\w\-\.\?\=\&\#]*)?$' # path
    )
    return re.match(pattern, url) is not None

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
    Returns clickable link if URL exists, otherwise plain text.
    """
    if url:
        return f'<a href="{url}">{text}</a>'
    return text