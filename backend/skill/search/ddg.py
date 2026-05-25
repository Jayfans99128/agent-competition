from backend.network.session import fetch_url
from backend.skill.search.parsers import parse_ddg

def search_ddg(query: str) -> list:
    url = f"https://lite.duckduckgo.com/lite/?q={query}"
    html_text = fetch_url(url)
    return parse_ddg(html_text)
