"""
考试分数线查询管理器
支持：考研（kaoyan）分数线查询、国考（guokao）分数线查询
"""
import os
import re

from . import clean_text, filter_context_for_llm

DATA_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_data(filename):
    """通用数据加载函数，解析【标题】+字段 格式的数据文件"""
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        return []

    with open(filepath, 'r', encoding='utf-8') as f:
        content = clean_text(f.read())

    entries = []
    # 匹配【标题】和其后的内容（直到下一个【或文件末尾）
    pattern = r'【(.+?)】\n(.*?)(?=\n【|\Z)'
    matches = re.findall(pattern, content, re.DOTALL)

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

    return entries


def _extract_year_aliases(query):
    """从查询中提取可能的年份别名，如"26年"→["2026"],"2026年"→["2026"],"今年"→["2026"]"""
    aliases = set()
    # "今年"/"最新"/"最近" → 当前年份
    import datetime
    current_year = str(datetime.datetime.now().year)  # 2026
    if re.search(r'今年|最新|最近|当前', query):
        aliases.add(current_year)
    # 匹配 "26年" → 2026
    m = re.search(r'(?<!\d)(\d{2})年', query)
    if m:
        short = m.group(1)
        if 20 <= int(short) <= 99:
            aliases.add(f'20{short}')
    # 匹配 "2026年" → 2026
    m = re.search(r'(20\d{2})年', query)
    if m:
        aliases.add(m.group(1))
    # 匹配裸 "2026" → 也作为年份
    m = re.search(r'(20\d{2})', query)
    if m:
        aliases.add(m.group(1))
    return aliases


def _segment_chinese_query(query):
    """把搜索词切成更细的 token，解决中文不带空格的问题"""
    tokens = query.lower().split()
    refined = []
    for token in tokens:
        # 在中文/英文/数字边界处切开
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
                # 对切出的纯中文 token 再做一次：把连续的修饰词和核心词分开
                # 如"车辆工程"、"机械工程"等复合词保持完整
            else:
                refined.append(p)
    # 去重但保持顺序
    seen = set()
    result = []
    for t in refined:
        if t not in seen:
            seen.add(t)
            result.append(t)
    # 过滤掉纯数字年份（如"2026"作为单独 token 可能抢占匹配权重，
    # 年份匹配已有 _extract_year_aliases 专门处理）
    return result


def _match_entries(entries, query, top_n=8):
    """关键词匹配打分，返回top_n条结果"""
    scored = []
    query_lower = query.lower()
    query_words = _segment_chinese_query(query_lower)
    year_aliases = _extract_year_aliases(query_lower)

    for entry in entries:
        title = entry.get('title', '').lower()
        body = entry.get('body', '').lower()
        full_text = title + ' ' + body

        score = 0.0
        for word in query_words:
            if word in title:
                score += 10
            if word in body:
                score += 3
            for char in word:
                if char in full_text:
                    score += 0.1

        # 年份别名匹配（如查"26年"能命中标题带"2026"的条目）
        for year in year_aliases:
            if year in title:
                score += 15
            elif year in body:
                score += 5

        # 近义词加分："复试线" ≈ "复试分数线"
        if '复试线' in query_words and '复试分数线' not in query_words:
            if '复试分数线' in title:
                score += 8
            elif '复试分数线' in body:
                score += 3
        if '复试分数线' in query_words and '复试线' not in query_words:
            if '复试线' in title:
                score += 8

        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [entry for score, entry in scored[:top_n]]


def _format_entries(entries, query_type='kaoyan'):
    """格式化查询结果为可读文本"""
    if not entries:
        if query_type == 'kaoyan':
            return (
                '未在本地知识库中找到相关考研分数数据。\n'
                '建议尝试以下方式：\n'
                '1. 输入大学名称（如"清华大学"、"北京大学"）\n'
                '2. 输入学科门类（如"工学"、"经济学"、"法学"）\n'
                '3. 输入"国家线"查看全国分数线\n'
                '4. 输入"报考人数"或"报录比"查看竞争情况\n'
                '5. 组合查询（如"清华大学 2025 工学"）\n'
                '你也可以使用网页搜索获取更详细的信息。'
            )
        else:
            return (
                '未在本地知识库中找到相关国考分数数据。\n'
                '建议尝试以下方式：\n'
                '1. 输入省份名称（如"北京"、"广东"、"浙江"）\n'
                '2. 输入"中央机关"或"省级"查看对应级别合格线\n'
                '3. 输入具体部门名称（如"税务局"、"海关"）\n'
                '4. 输入"合格线"查看全国笔试最低合格分数线\n'
                '5. 输入"竞争比"或"报考人数"查看竞争情况\n'
                '你也可以使用网页搜索获取更详细的信息。'
            )

    lines = []
    for entry in entries:
        title = entry.get('title', '')
        parts = [f'【{title}】']
        for key, val in entry.items():
            if key not in ('title', 'body'):
                # 压缩值中的多余空白和换行
                clean_val = ' '.join(str(val).split())
                parts.append(f'{key}：{clean_val}')
        # 用分号连接，紧凑但可读
        lines.append('；'.join(parts))

    return filter_context_for_llm('\n'.join(lines).strip())


def query_kaoyan_scores(query: str) -> str:
    """
    查询考研（全国硕士研究生招生考试）近三年分数线。

    覆盖内容：
    - 全国13个学科门类的国家线（A/B类）
    - 清华、北大、浙大、复旦、上交等20+所自主划线高校的复试基本线
    - 热门院校专业的报考人数和报录比
    - 全国考研报名总人数趋势

    用法示例：query_kaoyan_scores("清华大学 工学 2025")
    """
    entries = _load_data('kaoyan_data.txt')
    if not entries:
        return (
            '考研分数数据库暂未初始化。\n'
            '建议使用网页搜索获取最新数据：对我说"帮我搜索[院校名]考研复试线"即可联网查询。'
        )

    matched = _match_entries(entries, query)

    # 本地数据库无匹配时，引导用户使用联网搜索
    if not matched:
        return (
            f'数据库中暂未找到与"{query}"完全匹配的数据。\n\n'
            '建议：\n'
            '1. 尝试更精准的关键词（如"清华大学 工学 2025"、"广东工业大学 机械"）\n'
            '2. 使用联网搜索获取最新数据：对我说"帮我搜索 [院校名] 考研复试线"\n'
            '3. 输入"国家线"查看2023-2026年各学科国家线'
        )

    return _format_entries(matched, 'kaoyan')


def query_guokao_scores(query: str) -> str:
    """
    查询国考（国家公务员考试）近三年分数线。

    覆盖内容：
    - 各级别（中央/省级/市地级/行政执法类）笔试最低合格分数线
    - 北京、广东、上海、浙江、江苏、山东等20+省份热门岗位进面分数线
    - 热门岗位报考人数和竞争比
    - 国考全国报名总人数趋势

    用法示例：query_guokao_scores("北京 税务局 2025")
    """
    entries = _load_data('guokao_data.txt')
    if not entries:
        return (
            '国考分数数据库暂未初始化。\n'
            '建议使用网页搜索获取最新数据：对我说"帮我搜索[岗位名]国考分数线"即可联网查询。'
        )

    matched = _match_entries(entries, query)

    # 本地数据库无匹配时，返回提示引导联网搜索
    if not matched:
        return (
            f'本地数据库中暂未找到与"{query}"相关的国考分数线数据。\n\n'
            '建议：\n'
            '1. 尝试更精准的关键词（如"北京 税务局 2025"、"合格线 中央机关"、"广东 海关 竞争比"）\n'
            '2. 使用联网搜索获取最新数据：对我说"帮我搜索[岗位名]国考分数线"\n'
            '3. 输入"合格线"查看各级别笔试最低合格分数线\n'
            '4. 直接告诉我想查哪个省份和部门，我会帮你找到最匹配的结果。'
        )

    return _format_entries(matched, 'guokao')
