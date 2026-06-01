import os
import re

def query_kaoyan_data(query: str) -> str:
    """
    专门查询考研相关数据
    """
    kaoyan_data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "kaoyan_data.txt")

    # 检查考研数据文件是否存在
    if not os.path.exists(kaoyan_data_path):
        return "考研数据文件未找到，请检查文件是否存在。"

    with open(kaoyan_data_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 处理查询请求
    # 将查询拆分成关键词
    keywords = query.split()
    if not keywords:
        return "请输入有效的考研相关关键词，如'2026年国家线'、'清华大学复试分数'等。"

    # 检查是否包含考研关键信息
    kaoyan_keywords = ['考研', '复试', '分数线', '国家线', '报考人数', '报录比', '2026', '2025', '2024', '考研招生', '复试要求']

    # 搜索包含关键词的内容段落
    lines = content.split('\n')
    matching_sections = []

    # 搜索含有考研相关信息的段落
    current_section = []
    section_start = -1

    for i, line in enumerate(lines):
        # 当发现考研相关信息开始时
        if any(keyword in line for keyword in kaoyan_keywords) and len(current_section) == 0:
            section_start = i
            current_section = [line]
        elif section_start != -1:
            # 如果当前行是空行并遇到了下一个段落的开始
            if line.strip() == '' and any(keyword in lines[xx] for xx in range(i, min(i+5, len(lines))) for keyword in kaoyan_keywords):
                # 这个段落结束，但接下来又找到了考研相关内容，所以继续
                current_section.append(line)
            elif line.strip() == '' or i >= len(lines) - 1:
                # 段落结束
                if len(current_section) > 0:
                    # 检查段落是否与查询相关
                    section_text = " ".join(current_section)
                    # 判断是否相关
                    if any(keyword in section_text for keyword in keywords):
                        matching_sections.append("\n".join(current_section))
                    current_section = []
                    section_start = -1
                else:
                    current_section = []
                    section_start = -1
            else:
                if section_start != -1:
                    current_section.append(line)

    # 简化处理：返回包含关键词的前三个段落
    matching_lines = []
    keyword_matches = []

    for line in lines:
        line_content = line.strip()
        if not line_content:
            continue
        line_content_lower = line_content.lower()
        if any(keyword.lower() in line_content_lower for keyword in keywords):
            keyword_matches.append(line_content)
            if len(keyword_matches) >= 5:  # 限制返回结果数量
                break

    if keyword_matches:
        return "找到相关的考研数据:\n\n" + "\n".join(keyword_matches[:5])

    # 如果没有找到明确匹配，返回一些通用提示
    return (
        "在考研数据中未找到明确相关结果。\n\n"
        "建议您查询具体信息，如：\n"
        "1. '2026年国家线'\n"
        "2. '清华大学复试分数'\n"
        "3. '2026年考研复试流程'\n"
        "4. '北京大学考研分数线'\n"
        "5. '研究生复试要求'"
    )

def query_kaoyan_scores(query: str) -> str:
    """
    查询考研分数线（特定API方法）
    与原始query_kaoyan_scores保持兼容性
    """
    return query_kaoyan_data(query)