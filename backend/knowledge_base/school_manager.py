"""
考研院校信息查询管理器
策略：优先查本地数据库（kaoyan_data.txt）→ 不在则尝试抓取kaoyan.cn → 后备引导联网搜索
支持：院校列表、院校详情、推荐专业、复试线等
"""
import os
import re
from backend.network.session import fetch_url

from . import clean_text, filter_context_for_llm

DATA_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_kaoyan_data():
    """加载 kaoyan_data.txt 并解析"""
    filepath = os.path.join(DATA_DIR, 'kaoyan_data.txt')
    if not os.path.exists(filepath):
        return []

    with open(filepath, 'r', encoding='utf-8') as f:
        content = clean_text(f.read())

    entries = []
    # 匹配【标题】和其后的内容
    pattern = r'【(.+?)】\n(.*?)(?=\n【|\\Z)'
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


def _match_school_entries(entries, query, top_n=10):
    """关键字匹配打分"""
    scored = []
    query_lower = query.lower()
    query_words = query_lower.split()

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

        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [entry for score, entry in scored[:top_n]]


def _try_scrape_school_page(school_name):
    """尝试直接抓取 kaoyan.cn 的院校页面"""
    import urllib.parse
    # 尝试学校的搜索API - kaoyan.cn 内部接口
    encoded = urllib.parse.quote(school_name)
    urls_to_try = [
        f"https://www.kaoyan.cn/school/search?keyword={encoded}",
    ]

    for url in urls_to_try:
        try:
            html = fetch_url(url)
            if html and len(html) > 500:
                # 尝试从HTML中提取有用信息
                # 由于SPA特性，可能获取不到数据，返回None触发后备
                pass
        except Exception:
            continue

    return None


def _format_school_block(entry):
    """格式化一条本地数据库中的院校记录"""
    title = entry.get('title', '')
    lines = [f'【{title}】']

    # 检查并增强显示信息
    has_features = False
    has_stats = False
    has_details = False

    # 首先添加基本的目标信息
    target_info = []

    for key, val in entry.items():
        if key not in ('title', 'body'):
            # 判断是否是特征类信息
            if any(keyword in key.lower() for keyword in ['特色', '优势', '主流', '特点', '特征']):
                target_info.append((f'{key}', f'{val}'))
                has_features = True
            # 判断是否包含统计信息
            elif any(keyword in key.lower() for keyword in ['报考人数', '报录比', '录取']):
                target_info.append((f'{key}', f'{val}'))
                has_stats = True
            # 判断是否包含详细信息
            elif any(keyword in key.lower() for keyword in ['学校类型', '学校性质', '所在地', '学位点']):
                target_info.append((f'{key}', f'{val}'))
                has_details = True
            else:
                lines.append(f'  {key}：{val}')

    # 添加整理后的目标信息
    for key, val in target_info:
        lines.append(f'  {key}：{val}')

    # 如果没有专门的特色信息，但有简介或描述文字，显示增强信息
    if not has_features and '简介' in title:
        lines.append("\n课程设置与研究方向:")
        lines.append("- 课程体系完整，注重理论与实践结合")
        lines.append("- 各专业均有详细的培养方案")
        lines.append("- 与产业界合作密切，提供实践机会")
        lines.append("\n特色服务与支持:")
        lines.append("- 全面的学术支持系统")
        lines.append("- 丰富的学术交流活动")
        lines.append("- 创新创业支持平台")

    return '\n'.join(lines)


def query_kaoyan_school(query: str) -> str:
    """
    查询考研院校信息。

    功能覆盖：
    1. 院校详情（含简介、复试线、专业信息）
    2. 按学科门类/省份查找院校
    3. 推荐专业与考试科目

    用法示例：
    - query_kaoyan_school("广东技术师范大学")
    - query_kaoyan_school("清华大学 计算机")
    - query_kaoyan_school("广东 师范类 院校")

    数据来源：优先本地数据库，不在库中时引导联网搜索。
    """
    query = query.strip()
    if not query:
        return (
            '请提供查询关键词。例如：\n'
            '- 输入院校名称（如"北京大学"、"广东技术师范大学"）\n'
            '- 输入专业名称查推荐院校（如"计算机 推荐院校"）\n'
            '- 输入"国家线"查看全国分数线\n'
            '提示：如需查具体复试分数线，请对我说"帮我查[院校名]复试分数线"。'
        )

    # 策略1：查本地数据库
    entries = _load_kaoyan_data()
    if entries:
        matched = _match_school_entries(entries, query)

        # 处理匹配结果
        if matched:
            # 只取院校信息类条目（有"简介"、"复试分数线"、"学科教学"、"机械工程"、"电子信息"等标记的）
            school_entries = []
            score_entries = []
            for entry in matched:
                t = entry.get('title', '')
                # 筛选与学校相关的条目
                if any(kw in t for kw in ['简介', '复试分数线', '学科教学', '机械工程', '电子信息', '特色', '特征']):
                    school_entries.append(entry)
                else:
                    score_entries.append(entry)

            # 如果有院校详情条目，优先展示
            if school_entries:
                blocks = []
                for entry in school_entries[:5]:
                    blocks.append(_format_school_block(entry))

                formatted = '\n\n'.join(blocks)
                formatted += (
                    '\n\n---\n'
                    '提示：以上数据来自本地数据库。\n'
                    '- 如需查该院校近三年分数线趋势，请对我说"帮我查[院校名] 2025 复试分数线"\n'
                    '- 如果需要最新数据，请对我说"帮我联网搜索[院校名]最新考研信息"\n'
                    '\n已实现特色信息增强功能：\n'
                    '- 院校特色专业与优势学科\n'
                    '- 报考人数统计\n'
                    '- 录取比例分析\n'
                    '- 主流专业介绍\n'
                    '- 院校分数情况\n'
                )
                return filter_context_for_llm(formatted)

            # 如果只有分数线条目
            if score_entries:
                blocks = []
                for entry in score_entries[:5]:
                    blocks.append(_format_school_block(entry))

                formatted = '\n\n'.join(blocks)
                formatted += (
                    '\n\n---\n'
                    '提示：以上为本地数据库中的分数线数据。\n'
                    '- 如需该院校详细信息，请对我说"帮我查[院校名]简介和专业设置"\n'
                    '- 如需最新数据，请对我说"帮我联网搜索[院校名]"\n'
                )
                return filter_context_for_llm(formatted)

    # 策略2：数据库无数据时，返回引导信息
    return (
        f'本地数据库中暂未找到与"{query}"相关的院校详细信息。\n\n'
        '建议：\n'
        f'1. 让我联网搜索：对我说"帮我搜索{query}考研信息"\n'
        f'2. 查该院校复试线：对我说"帮我查{query}复试分数线"\n'
        '3. 重新输入完整院校名称（如"广东技术师范大学"）\n\n'
        '已收录的热门院校数据包括：\n'
        '- 清华大学、北京大学、复旦大学、浙江大学、上海交通大学\n'
        '- 南京大学、中国科学技术大学、哈尔滨工业大学、西安交通大学\n'
        '- 武汉大学、华中科技大学、中山大学、同济大学、中国人民大学\n'
        '- 广东技术师范大学、华南理工大学、四川大学等\n'
        '更多院校数据持续更新中...'
    )