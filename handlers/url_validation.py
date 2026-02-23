import re

def is_valid_url(url: str) -> bool:
    pattern = re.compile(
        r'^(https?:\/\/)'          # http:// or https://
        r'([\w\-]+\.)+[\w\-]+'     # domain
        r'([\/\w\-\.\?\=\&\#]*)?$' # path
    )
    return re.match(pattern, url) is not None
