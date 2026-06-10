import os
import re

from . import clean_text, filter_context_for_llm

DATA_DIR = os.path.dirname(os.path.abspath(__file__))


def _segment_chinese_query(query):
    """把搜索词切成更细的 token，解决中文不带空格的问题"""
    tokens = query.lower().split()
    refined = []
    for token in tokens:
        parts = re.split(r'([一-鿿]+)', token)
        for p in parts:
            p = p.strip()
            if not p:
                continue
            if re.fullmatch(r'[一-鿿]+', p):
                # 纯中文词：按常见边界词细分，确保专业名、学校名等关键 token 被正确切出
                sub = re.split(
                    r'(分数线|复试线|复试分|复试资格线|国家线|报考|报录|录取'
                    r'|专业|学院|大学|年|的|在|和|与|及|或|是|有)',
                    p
                )
                for s in sub:
                    s = s.strip()
                    if s:
                        refined.append(s)
            else:
                refined.append(p)
    seen = set()
    result = []
    for t in refined:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result


def _extract_year_aliases(query):
    """从查询中提取可能的年份别名"""
    aliases = set()
    m = re.search(r'(?<!\d)(\d{2})年', query)
    if m:
        short = m.group(1)
        if 20 <= int(short) <= 99:
            aliases.add(f'20{short}')
    m = re.search(r'(20\d{2})年', query)
    if m:
        aliases.add(m.group(1))
    m = re.search(r'(20\d{2})', query)
    if m:
        aliases.add(m.group(1))
    return aliases


def query_kaoyan_data(query: str) -> str:
    """
    专门查询考研相关数据
    """
    kaoyan_data_path = os.path.join(DATA_DIR, "kaoyan_data.txt")

    # 检查考研数据文件是否存在
    if not os.path.exists(kaoyan_data_path):
        return "考研数据文件未找到，请检查文件是否存在。"

    with open(kaoyan_data_path, "r", encoding="utf-8") as f:
        content = clean_text(f.read())

    # 处理查询请求：先按 exam_manager 方式加载结构化条目
    pattern = r'【(.+?)】\n(.*?)(?=\n【|\Z)'
    matches = re.findall(pattern, content, re.DOTALL)

    entries = []
    for title, body in matches:
        entry = {'title': title.strip(), 'body': body.strip()}
        for line in body.strip().split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '：' in line:
                key, val = line.split('：', 1)
                entry[key.strip()] = val.strip()
        entries.append(entry)

    if not entries:
        return "考研数据文件为空。"

    # 分词和年份别名
    query_lower = query.lower()
    keywords = _segment_chinese_query(query_lower)
    year_aliases = _extract_year_aliases(query_lower)

    # 打分排序
    scored = []
    for entry in entries:
        title = entry.get('title', '').lower()
        body = entry.get('body', '').lower()
        full_text = title + ' ' + body

        score = 0.0
        for word in keywords:
            if word in title:
                score += 10
            if word in body:
                score += 3
            for char in word:
                if char in full_text:
                    score += 0.1

        for year in year_aliases:
            if year in title:
                score += 15
            elif year in body:
                score += 5

        if '复试线' in keywords and '复试分数线' not in keywords:
            if '复试分数线' in title:
                score += 8

        if score > 0:
            scored.append((score, entry))

    if not scored:
        return (
            "在考研数据中未找到明确相关结果。\n\n"
            "建议您查询具体信息，如：\n"
            "1. '2026年国家线'\n"
            "2. '清华大学复试分数'\n"
            "3. '2026年考研复试流程'\n"
            "4. '北京大学考研分数线'\n"
            "5. '研究生复试要求'"
        )

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:8]

    lines = []
    for score, entry in top:
        title = entry.get('title', '')
        parts = [f'【{title}】']
        for key, val in entry.items():
            if key not in ('title', 'body'):
                clean_v = ' '.join(str(val).split())
                parts.append(f'{key}：{clean_v}')
        lines.append('；'.join(parts))

    return filter_context_for_llm('\n'.join(lines))

def query_kaoyan_scores(query: str) -> str:
    """
    查询考研分数线（特定API方法）
    与原始query_kaoyan_scores保持兼容性
    """
    return query_kaoyan_data(query)