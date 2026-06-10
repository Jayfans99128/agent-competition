"""联网搜索管理器 — 依次尝试多个搜索引擎，返回最先成功的结果"""
import logging
from backend.skill.search.baidu import search_baidu
from backend.skill.search.ddg import search_ddg
from backend.skill.search.bing import search_bing
from backend.skill.search.sogou import search_sogou

logger = logging.getLogger("zhipig")


def web_search(query: str) -> str:
    """联网搜索，依次尝试百度 → DuckDuckGo → Bing → 搜狗"""

    engine_order = [
        ("DuckDuckGo", search_ddg),
        ("百度", search_baidu),
        ("Bing", search_bing),
        ("搜狗", search_sogou),
    ]

    last_error = None
    for engine_name, search_func in engine_order:
        try:
            results = search_func(query)
            if results:
                logger.info("搜索成功 [%s]: %s → %d 条", engine_name, query[:50], len(results))
                return "\n\n".join(results[:5])
        except Exception as e:
            logger.warning("搜索失败 [%s]: %s — %s", engine_name, query[:50], e)
            last_error = e
            continue

    err_msg = f"搜索失败：所有搜索引擎均无法获取结果。"
    if last_error:
        err_msg += f" 最后错误: {last_error}"
    logger.error(err_msg)
    return err_msg
