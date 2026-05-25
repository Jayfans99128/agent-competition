from backend.network.session import fetch_url
from backend.skill.search.parsers import parse_sogou

def search_sogou(query: str) -> list:
    url = f"https://www.sogou.com/web?query={query}"
    html_text = fetch_url(url)
    return parse_sogou(html_text)
