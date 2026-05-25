import re
import html as html_mod

def parse_ddg(html_text: str) -> list:
    """解析 DuckDuckGo Lite 搜索结果"""
    results = []
    pattern = re.compile(
        r'<a[^>]*href=["\'](https?://(?!lite\.duckduckgo|duckduckgo\.com)[^"\']+)["\'][^>]*>(.*?)</a>',
        re.IGNORECASE | re.DOTALL
    )
    matches = pattern.findall(html_text)
    seen = set()
    for href, title in matches:
        title = re.sub(r'<[^>]+>', '', title).strip()
        title = html_mod.unescape(title)
        href = html_mod.unescape(href)
        if title and href not in seen:
            seen.add(href)
            results.append(f"标题: {title}\n链接: {href}")
    return results


def parse_bing(html_text: str) -> list:
    """解析 Bing 搜索结果"""
    results = []
    blocks = re.findall(r'<li[^>]*class=["\']?[^"\']*b_algo[^"\']*["\']?[^>]*>(.*?)</li>', html_text, re.IGNORECASE | re.DOTALL)
    for block in blocks:
        link_match = re.search(r'<a[^>]+href=["\'](https?://[^"\']+)["\'][^>]*>(.*?)</a>', block, re.IGNORECASE | re.DOTALL)
        if not link_match:
            continue
        href = html_mod.unescape(link_match.group(1))
        title = html_mod.unescape(re.sub(r'<[^>]+>', '', link_match.group(2)).strip())
        if title:
            results.append(f"标题: {title}\n链接: {href}")
    return results


def parse_sogou(html_text: str) -> list:
    """解析 搜狗 搜索结果"""
    results = []
    blocks = re.findall(r'<div[^>]*class=["\']?[^"\']*(?:vrwrap|rb)[^"\']*["\']?[^>]*>(.*?)</div>', html_text, re.IGNORECASE | re.DOTALL)
    for block in blocks:
        link_match = re.search(r'<a[^>]+href=["\'](https?://[^"\']+)["\'][^>]*>(.*?)</a>', block, re.IGNORECASE | re.DOTALL)
        if not link_match:
            continue
        href = html_mod.unescape(link_match.group(1))
        title = html_mod.unescape(re.sub(r'<[^>]+>', '', link_match.group(2)).strip())
        if title:
            results.append(f"标题: {title}\n链接: {href}")
    return results
