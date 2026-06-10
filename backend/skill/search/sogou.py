"""搜狗搜索 — 使用 Selenium 获取并解析搜索结果"""
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


def search_sogou(query: str) -> list:
    """用 Selenium 搜索搜狗并提取结果"""
    driver = get_driver()
    url = f"https://www.sogou.com/web?query={urllib.parse.quote(query)}"
    results = []

    try:
        driver.get(url)

        try:
            WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.results, div.vrwrap, div.rb"))
            )
        except TimeoutException:
            logger.warning("搜狗搜索结果未找到: %s", query[:50])
            return results

        time.sleep(1)

        # 搜狗结果容器
        containers = driver.find_elements(By.CSS_SELECTOR, "div.vrwrap, div.rb")
        if not containers:
            containers = driver.find_elements(By.CSS_SELECTOR, "div.results > div")

        seen_urls = set()
        for container in containers:
            try:
                link_el = container.find_element(By.CSS_SELECTOR, "h3 a, .vr-title a")
                title = link_el.text.strip()
                href = link_el.get_attribute("href")
            except Exception:
                try:
                    link_el = container.find_element(By.CSS_SELECTOR, "a[href]")
                    title = link_el.text.strip()
                    href = link_el.get_attribute("href")
                except Exception:
                    continue

            if not title or not href:
                continue
            if not href.startswith("http"):
                continue
            if "sogou.com" in href and "/link?" not in href:
                continue
            if href in seen_urls:
                continue

            snippet = ""
            try:
                snippet_el = container.find_element(
                    By.CSS_SELECTOR, ".star-wiki, .space-txt, .str-text, .abstract"
                )
                snippet = snippet_el.text.strip()
            except Exception:
                pass

            seen_urls.add(href)
            entry = f"标题: {title}\n链接: {href}"
            if snippet and len(snippet) > 5:
                entry += f"\n摘要: {snippet[:200]}"
            results.append(entry)

            if len(results) >= 5:
                break

        logger.info("搜狗返回 %d 条结果: %s", len(results), query[:50])
        return results

    except Exception as e:
        logger.error("搜狗搜索异常: %s — %s", query[:50], e)
        return results
