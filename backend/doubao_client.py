"""
豆包（Doubao）客户端

支持两种模式：
1. web 模式（默认）：调用豆包网页版内部 API，免费，需要提供 DOUBAO_SESSION_ID
2. api 模式：调用火山引擎 ARK 官方 API，需付费

获取 DOUBAO_SESSION_ID 的方法：
  1. 在浏览器中打开 https://www.doubao.com/chat/ 并登录
  2. 按 F12 打开开发者工具 → Application → Cookies → www.doubao.com
  3. 复制 sessionid 的值
  4. 放入 .env 文件：DOUBAO_SESSION_ID=你的sessionid
"""

import json
import ssl
import urllib.request
import urllib.parse

from backend.config import (
    DOUBAO_MODE,
    DOUBAO_SESSION_ID,
    DOUBAO_WEB_BASE,
    DOUBAO_API_KEY,
    DOUBAO_BASE_URL,
    DOUBAO_MODEL,
)


def _get_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


WEB_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Content-Type": "application/json",
    "Origin": "https://www.doubao.com",
    "Referer": "https://www.doubao.com/chat/",
}


def _query_via_web(query: str) -> str:
    """通过豆包网页版内部 API 查询（免费，需要 session cookie）"""
    if not DOUBAO_SESSION_ID:
        return "未配置 DOUBAO_SESSION_ID，请在 .env 中设置。获取方法：浏览器登录 doubao.com → F12 → Application → Cookies → 复制 sessionid 的值"

    url = f"{DOUBAO_WEB_BASE}/samantha/chat/completion"
    headers = {**WEB_HEADERS, "Cookie": f"sessionid={DOUBAO_SESSION_ID}"}

    body = json.dumps({
        "model": "doubao-pro-chat",
        "messages": [
            {"role": "system", "content": "你是一个知识渊博的助手，专门帮助用户查询考研和考公相关的备考资料、学习方法、书籍推荐、时间规划等信息。请提供详细、实用、具体的回答，用中文回答。"},
            {"role": "user", "content": query},
        ],
        "stream": False,
    }, ensure_ascii=False).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=body, headers=headers)
        ctx = _get_ssl_context()
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]
            return f"豆包返回格式异常: {json.dumps(data, ensure_ascii=False)[:300]}"
    except urllib.error.HTTPError as e:
        body_text = ""
        try:
            body_text = e.read().decode("utf-8", errors="ignore")[:300]
        except Exception:
            pass
        return f"豆包网页版请求失败 (HTTP {e.code}): {body_text}"
    except Exception as e:
        return f"豆包网页版请求失败: {e}"


def _query_via_api(query: str) -> str:
    """通过火山引擎 ARK 官方 API 查询"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=DOUBAO_API_KEY, base_url=DOUBAO_BASE_URL)
        response = client.chat.completions.create(
            model=DOUBAO_MODEL,
            messages=[
                {"role": "system", "content": "你是一个知识渊博的助手，专门帮助用户查询考研和考公相关的备考资料、学习方法、书籍推荐、时间规划等信息。请提供详细、实用、具体的回答，用中文回答。"},
                {"role": "user", "content": query},
            ],
            max_tokens=2000,
            temperature=0.7,
        )
        return response.choices[0].message.content or "豆包未返回有效回答"
    except Exception as e:
        return f"豆包 API 调用失败: {e}"


def query_doubao(query: str) -> str:
    """调用豆包，根据 DOUBAO_MODE 自动选择 web 或 api 模式"""
    if DOUBAO_MODE == "api":
        return _query_via_api(query)
    else:
        return _query_via_web(query)
