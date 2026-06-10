"""DuckDuckGo 搜索 — 使用 Selenium 获取 Lite 版搜索结果"""
import logging
import time
import re
import urllib.parse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from backend.network.session import get_driver

logger = logging.getLogger("zhipig")


def _unwrap_ddg_url(redirect_url: str) -> str:
    """将 DuckDuckGo 重定向链接解析为真实 URL"""
    parsed = urllib.parse.urlparse(redirect_url)
    query_params = urllib.parse.parse_qs(parsed.query)
    real_url = query_params.get("uddg", [""])[0]
    if real_url:
        return urllib.parse.unquote(real_url)
    return redirect_url


def search_ddg(query: str) -> list:
    """用 Selenium 搜索 DuckDuckGo HTML-only Lite 版并提取结果"""
    driver = get_driver()
    url = f"https://lite.duckduckgo.com/lite/?q={urllib.parse.quote(query)}"
    results = []

    try:
        driver.get(url)

        try:
            WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a.result-link"))
            )
        except TimeoutException:
            logger.warning("DuckDuckGo 搜索结果未找到: %s", query[:50])
            return results

        time.sleep(0.5)

        link_elements = driver.find_elements(By.CSS_SELECTOR, "a.result-link")
        seen_urls = set()

        for link_el in link_elements:
            title = link_el.text.strip()
            href = link_el.get_attribute("href")

            if not title or not href:
                continue

            # 解包 DuckDuckGo 重定向链接
            real_href = _unwrap_ddg_url(href)

            if not real_href.startswith("http"):
                continue
            if real_href in seen_urls:
                continue

            # 尝试获取摘要
            snippet = ""
            try:
                parent_tr = link_el.find_element(By.XPATH, "./ancestor::tr")
                snippet_el = parent_tr.find_element(By.CSS_SELECTOR, "td.result-snippet")
                snippet = snippet_el.text.strip()
            except Exception:
                pass

            seen_urls.add(real_href)
            entry = f"标题: {title}\n链接: {real_href}"
            if snippet and len(snippet) > 10:
                entry += f"\n摘要: {snippet[:200]}"
            results.append(entry)

            if len(results) >= 5:
                break

        logger.info("DuckDuckGo 返回 %d 条结果: %s", len(results), query[:50])
        return results

    except Exception as e:
        logger.error("DuckDuckGo 搜索异常: %s — %s", query[:50], e)
        return results
