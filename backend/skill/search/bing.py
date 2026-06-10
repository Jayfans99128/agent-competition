"""Bing 搜索 — 使用 Selenium 获取并解析搜索结果（含反检测）"""
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


def search_bing(query: str) -> list:
    """用 Selenium 搜索 Bing 并提取结果"""
    driver = get_driver()
    # 添加随机参数避免缓存/CAPTCHA
    import random
    url = f"https://cn.bing.com/search?q={urllib.parse.quote(query)}&setlang=zh-cn&ensearch=0&_={random.randint(1000,9999)}"
    results = []

    try:
        driver.get(url)

        # 等待搜索结果出现 — 使用多种选择器
        try:
            WebDriverWait(driver, 8).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "li.b_algo, #b_results, .b_caption, main")
                )
            )
        except TimeoutException:
            pass

        time.sleep(1.5)

        # 用 page_source + 正则作为后备（鲁棒性最强）
        html = driver.page_source
        seen_urls = set()

        # 提取搜索结果块
        # Bing 结果通常在 <li class="b_algo"> 中
        blocks = re.findall(
            r'<li[^>]*class="[^"]*b_algo[^"]*"[^>]*>(.*?)</li>',
            html, re.DOTALL | re.IGNORECASE
        )

        for block in blocks:
            # 提取标题链接
            link_match = re.search(
                r'<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>',
                block, re.DOTALL | re.IGNORECASE
            )
            if not link_match:
                continue

            href = link_match.group(1)
            title = re.sub(r'<[^>]+>', '', link_match.group(2)).strip()
            title = __import__('html').unescape(title)

            if not title or not href:
                continue
            if 'bing.com' in href or 'microsoft.com' in href or 'live.com' in href:
                continue
            if href in seen_urls:
                continue

            # 提取摘要
            snippet_match = re.search(
                r'<p[^>]*>(.*?)</p>|<div[^>]*class="[^"]*b_caption[^"]*"[^>]*>(.*?)</div>',
                block, re.DOTALL | re.IGNORECASE
            )
            snippet = ""
            if snippet_match:
                snippet = re.sub(r'<[^>]+>', '', snippet_match.group(1) or snippet_match.group(2) or "").strip()
                snippet = __import__('html').unescape(snippet)

            seen_urls.add(href)
            entry = f"标题: {title}\n链接: {href}"
            if snippet and len(snippet) > 10:
                entry += f"\n摘要: {snippet[:200]}"
            results.append(entry)

            if len(results) >= 5:
                break

        # 如果正则没抓到，用 Selenium DOM 方式再试
        if not results:
            try:
                items = driver.find_elements(By.CSS_SELECTOR, "li.b_algo, .b_algo")
                for item in items:
                    try:
                        link_el = item.find_element(By.CSS_SELECTOR, "h2 a, a[href]")
                        title = link_el.text.strip()
                        href = link_el.get_attribute("href")
                    except Exception:
                        continue

                    if not title or not href or not href.startswith("http"):
                        continue
                    if 'bing.com' in href or href in seen_urls:
                        continue

                    seen_urls.add(href)
                    results.append(f"标题: {title}\n链接: {href}")
                    if len(results) >= 5:
                        break
            except Exception:
                pass

        logger.info("Bing 返回 %d 条结果: %s", len(results), query[:50])
        return results

    except Exception as e:
        logger.error("Bing 搜索异常: %s — %s", query[:50], e)
        return results
