import os
import re

_KB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "knowledge_base_data.txt")
_sections: list[dict] = []

def _load_kb():
    global _sections
    if _sections:
        return _sections
    if not os.path.exists(_KB_PATH):
        return _sections

    with open(_KB_PATH, "r", encoding="utf-8") as f:
        all_lines = [l.strip() for l in f]

    # 第一步：找出所有岗位标题的位置
    # 岗位标题 = 一行文字，下一非空行包含"工作介绍"
    job_indices = []
    for i, line in enumerate(all_lines):
        if not line:
            continue
        # 跳过明显不是岗位标题的行
        if line[0] in "一二三四五六七八九" and ("、" in line or "）" in line):
            continue
        if line in ("研发技术类（核心高薪方向）",):
            continue
        if len(line) > 30:
            continue
        # 检查下一非空行是否包含"工作介绍"
        next_line = ""
        for j in range(i + 1, min(i + 3, len(all_lines))):
            if all_lines[j].strip():
                next_line = all_lines[j].strip()
                break
        if "工作介绍" in next_line:
            job_indices.append(i)

    # 第二步：按岗位标题位置切分，提取每个岗位的字段
    for idx, pos in enumerate(job_indices):
        job_title = all_lines[pos].rstrip("：:")
        # 当前岗位的结束位置是下一个岗位的开始，或文件末尾
        end = job_indices[idx + 1] if idx + 1 < len(job_indices) else len(all_lines)

        fields = {"job": job_title}
        # 从 pos+1 到 end 之间提取字段
        segment = all_lines[pos + 1 : end]
        pending_key = None

        for line in segment:
            if not line:
                continue
            # 检查是否是字段标题：以（数字）开头
            m = re.match(r"^（(\d+)）(.+)$", line)
            if m:
                key = m.group(2).strip("：:").strip()
                # 字段标题后可能直接跟着内容（当"工作介绍："行包含完整内容时）
                content_after = line.split("）", 1)[1]
                # 检查：如果同行后面有长内容（>10字符），则是内容
                rest = content_after.strip("：:").strip()
                if len(rest) > 10:
                    # 同行包含内容，直接存储
                    fields[key] = rest
                    pending_key = None
                else:
                    pending_key = key
                continue
            # 检查"工作介绍："格式（无括号编号）
            if line.startswith("工作介绍") and "：" in line:
                content = line.split("：", 1)[1].strip()
                if content:
                    fields["工作介绍"] = content
                    pending_key = None
                else:
                    pending_key = "工作介绍"
                continue
            if line.startswith("专业能力") and "：" in line:
                content = line.split("：", 1)[1].strip()
                if content:
                    fields["专业能力"] = content
                    pending_key = None
                else:
                    pending_key = "专业能力"
                continue
            if line.startswith("素质素养") and "：" in line:
                content = line.split("：", 1)[1].strip()
                if content:
                    fields["素质素养"] = content
                    pending_key = None
                else:
                    pending_key = "素质素养"
                continue
            if line.startswith("职业发展途径") and "：" in line:
                content = line.split("：", 1)[1].strip()
                if content:
                    fields["职业发展途径"] = content
                    pending_key = None
                else:
                    pending_key = "职业发展途径"
                continue
            # 普通内容行：如果 pending_key 存在，则归属到该 key
            if pending_key:
                fields[pending_key] = line
                pending_key = None

        # 也处理跨行内容（多行归属于同一 key）
        _sections.append(fields)

    return _sections

def _match_score(job: str, query: str) -> int:
    """简单关键词匹配打分"""
    score = 0
    q_lower = query.lower()
    j_lower = job.lower()
    # 完全匹配
    if q_lower in j_lower or j_lower in q_lower:
        score += 10
    # 逐字匹配
    for ch in query:
        if ch in job:
            score += 1
    return score

def query_knowledge_base(query: str) -> str:
    """
    从知识库中查询相关信息。
    传入用户的查询关键词，返回匹配的知识库内容。
    优先匹配车辆工程岗位信息，其次匹配考研相关数据。
    """
    sections = _load_kb()
    if not sections:
        return "知识库未加载，请检查知识库文件是否存在。"

    # 如果查询涉及考研相关问题，先尝试专门的考研查询
    kaoyan_keywords = ['考研', '复试', '分数线', '国家线', '报考人数', '报录比', '2026', '复试线', '分数线']
    is_kaoyan_query = any(keyword in query for keyword in kaoyan_keywords)

    if is_kaoyan_query:
        # 专门处理考研相关查询 - 搜索包含考研关键词的所有条目
        kaoyan_sections = []

        # 首先用文件位置直接找出包含考研关键词的段落
        with open(_KB_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        # 简单的文件内容检索 - 搜索包含考研数据的段落
        lines = content.split('\n')
        chunk_start = -1
        current_chunk = []

        # 识别考研数据段落
        for i, line in enumerate(lines):
            if any(keyword in line for keyword in kaoyan_keywords):
                # 找到考研相关的行，构建完整的段落
                if chunk_start == -1:
                    chunk_start = max(0, i - 3)  # 包含前几行上下文
                current_chunk.append(line)
            elif chunk_start != -1:
                # 这是与考研相关的段落的结尾
                if line.strip() == '' or (i - chunk_start > 20):  # 一段结束或超过20行
                    if any(keyword in ' '.join(current_chunk) for keyword in kaoyan_keywords):
                        kaoyan_sections.extend(_extract_kaoyan_data(current_chunk))
                    current_chunk = []
                    chunk_start = -1
                else:
                    current_chunk.append(line)

        if kaoyan_sections:
            # 为了显示清晰，我们只返回有明确考研信息的段落
            lines = []
            for s in kaoyan_sections[:3]:  # 只显示前3个相关的
                lines.append("【{}】".format(s.get('标题', '考研数据')))
                for k, v in s.items():
                    if k == "标题":
                        continue
                    lines.append("  {}: {}".format(k, v))
                lines.append("")
            return "\n".join(lines)

    # 对于车辆工程岗位查询
    # 按岗位名称匹配
    scored = [(s, _match_score(s["job"], query)) for s in sections]
    scored.sort(key=lambda x: x[1], reverse=True)

    # 取前3个最匹配的岗位
    top = [s for s, sc in scored[:3] if sc > 0]

    if not top:
        # 尝试全文搜索
        results = []
        for s in sections:
            full_text = " ".join(str(v) for v in s.values())
            if any(kw in full_text for kw in query.split()):
                results.append(s)
            if len(results) >= 3:
                break
        top = results

    if not top:
        no_result = "在知识库中未找到与「{}」直接相关的内容。".format(query)
        if is_kaoyan_query:
            no_result += "知识库中包含考研复试、国家线等信息，请尝试更具体的关键词搜索。"
        else:
            no_result += "知识库包含以下岗位方向：整车研发类（总布置、车身、底盘、动力总成、电池、电控、整车性能、电机、NVH、CAE仿真、CFD、热管理、空气动力学、碰撞安全、ADAS、自动驾驶算法、自动驾驶测试、智能座舱、车联网）、制造工艺类、软件开发类、销售市场类等。请尝试更具体的岗位名称搜索。"
        return no_result

    lines = []
    for s in top:
        lines.append(f"【{s['job']}】")
        for k, v in s.items():
            if k == "job":
                continue
            lines.append(f"  {k}：{v}")
        lines.append("")

    return "\n".join(lines)

def _extract_kaoyan_data(lines):
    """从行列表中提取考研数据段落"""
    # 简化版本：因为现在的函数主要在服务车辆工程数据
    # 考研数据专门存储在kaoyan_data_update.txt中
    return []