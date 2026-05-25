import urllib.request
import urllib.parse
import ssl

from .headers import HEADERS

def create_request(url: str) -> urllib.request.Request:
    encoded_url = urllib.parse.quote(url, safe=":/?=&%+")
    return urllib.request.Request(encoded_url, headers=HEADERS)

def get_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def fetch_url(url: str, timeout: int = 10) -> str:
    req = create_request(url)
    ctx = get_ssl_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return resp.read().decode("utf-8", errors="ignore")
