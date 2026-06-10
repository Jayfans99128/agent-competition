"""Selenium WebDriver 管理 — 单例模式，集成反检测，提供页面抓取能力"""
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

logger = logging.getLogger("zhipig")

_driver = None


def _create_chrome_driver():
    """创建带反检测的 headless Chrome WebDriver"""
    options = ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=zh-CN")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-setuid-sandbox")
    options.add_argument("--remote-debugging-port=0")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.default_content_setting_values.notifications": 2,
    }
    options.add_experimental_option("prefs", prefs)

    # 优先用 webdriver-manager 自动下载匹配的 ChromeDriver
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except Exception:
        logger.info("webdriver-manager 不可用，尝试系统 ChromeDriver")
        driver = webdriver.Chrome(options=options)

    # 注入 selenium-stealth 反检测脚本
    try:
        from selenium_stealth import stealth
        stealth(
            driver,
            languages=["zh-CN", "zh", "en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        logger.info("selenium-stealth 已注入")
    except ImportError:
        logger.info("selenium-stealth 未安装，使用手动反检测")

    # 手动隐藏 webdriver 特征（后备）
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    driver.execute_script(
        "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})"
    )
    driver.execute_script(
        "Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh']})"
    )

    driver.set_page_load_timeout(20)
    driver.implicitly_wait(3)
    return driver


def get_driver():
    """获取全局 WebDriver 单例，自动修复已断开的连接"""
    global _driver
    if _driver is not None:
        try:
            _driver.current_url
            return _driver
        except WebDriverException:
            logger.info("WebDriver 连接已断开，重新创建...")
            _driver = None

    _driver = _create_chrome_driver()
    logger.info("✓ Selenium WebDriver 就绪 (headless Chrome)")
    return _driver


def fetch_page(url: str, wait_selector: str = "body", timeout: int = 15) -> str:
    """用 Selenium 加载页面并返回渲染后的 HTML 源码"""
    driver = get_driver()
    try:
        driver.get(url)
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(("css selector", wait_selector))
        )
        return driver.page_source
    except TimeoutException:
        logger.warning("页面加载超时: %s (selector=%s)", url[:80], wait_selector)
        return driver.page_source
    except WebDriverException as e:
        logger.error("页面加载失败: %s — %s", url[:80], e)
        raise


def fetch_url(url: str, timeout: int = 15) -> str:
    """向后兼容接口 — 使用 Selenium 获取页面 HTML（取代 urllib.request）"""
    return fetch_page(url, timeout=timeout)


def quit_driver():
    """关闭 WebDriver（应用退出时调用）"""
    global _driver
    if _driver is not None:
        try:
            _driver.quit()
        except Exception:
            pass
        _driver = None
        logger.info("WebDriver 已关闭")
