import os

from backend.skill.search.ddg import search_ddg
from backend.skill.search.bing import search_bing
from backend.skill.search.sogou import search_sogou

def web_search(query: str) -> str:
    try:
        results = []

        for engine_name, search_func in [
            ("DuckDuckGo", search_ddg),
            ("Bing", search_bing),
            ("搜狗", search_sogou),
        ]:
            try:
                results = search_func(query)
                if results:
                    break
            except Exception:
                continue

        if not results:
            save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "search_error.html")
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(f"所有搜索引擎均未返回结果。最后尝试的引擎: {engine_name}\nquery: {query}")
            return f"搜索失败：所有搜索引擎均无法获取结果。已将诊断信息保存至 {save_path}"

        return "\n\n".join(results[:5])
    except Exception as e:
        return f"搜索请求报错: {e}"
