from backend.network.session import fetch_url
from backend.skill.search.parsers import parse_bing

def search_bing(query: str) -> list:
    url = f"https://cn.bing.com/search?q={query}&setlang=zh-cn"
    html_text = fetch_url(url)
    return parse_bing(html_text)
