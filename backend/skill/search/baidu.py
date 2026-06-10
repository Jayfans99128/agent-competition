"""百度搜索 — 使用 Selenium 获取并解析搜索结果"""
import logging
import time
import urllib.parse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from backend.network.session import get_driver

logger = logging.getLogger("zhipig")


def search_baidu(query: str) -> list:
    """用 Selenium 搜索百度并提取结果"""
    driver = get_driver()
    url = f"https://www.baidu.com/s?wd={urllib.parse.quote(query)}&ie=utf-8"
    results = []

    try:
        driver.get(url)

        # 等待搜索结果
        try:
            WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#content_left, #results"))
            )
        except TimeoutException:
            logger.warning("百度搜索结果未找到: %s", query[:50])
            return results

        time.sleep(1)

        # 百度结果容器
        containers = driver.find_elements(
            By.CSS_SELECTOR,
            "#content_left .result, #content_left .c-container, #results .result"
        )

        seen_urls = set()
        for container in containers:
            try:
                # 百度的标题链接通常在 h3 > a
                link_el = container.find_element(By.CSS_SELECTOR, "h3 a, .t a")
                title = link_el.text.strip()
                href = link_el.get_attribute("href")
            except Exception:
                continue

            if not title or not href:
                continue
            if not href.startswith("http"):
                continue
            if "baidu.com" in href and "/s?" in href:
                continue  # 跳过百度自身的搜索链接
            if href in seen_urls:
                continue

            # 提取摘要
            snippet = ""
            try:
                snippet_el = container.find_element(
                    By.CSS_SELECTOR, ".c-abstract, .c-span-last, .c-row"
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

        logger.info("百度返回 %d 条结果: %s", len(results), query[:50])
        return results

    except Exception as e:
        logger.error("百度搜索异常: %s — %s", query[:50], e)
        return results
