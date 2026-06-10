"""
基于模板简历.docx 填充用户简历数据，生成可下载的 DOCX 文件。

规则：
- 项目经历、实习经历、掌握技能 → 从用户简历提取并填入模板
- 其他字段（个人信息、教育背景等）→ 用户有就填，没有则保留模板默认值
- 用户没有实习经历 → 删除实习经历模块
"""

import os
import json
import copy
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

from backend.config import client, MODEL


def _find_template_path() -> str:
    """查找模板文件路径，支持多种查找方式"""
    # 方式1：当前工作目录
    cwd = os.getcwd()
    candidate = os.path.join(cwd, "模板简历.docx")
    if os.path.exists(candidate):
        return candidate

    # 方式2：从本文件向上找到项目根目录
    current = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):  # 最多向上找6层
        candidate = os.path.join(current, "模板简历.docx")
        if os.path.exists(candidate):
            return candidate
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent

    # 方式3：backend 目录的父目录
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    project_root = os.path.dirname(backend_dir)
    candidate = os.path.join(project_root, "模板简历.docx")
    if os.path.exists(candidate):
        return candidate

    raise FileNotFoundError("找不到模板简历.docx，请确保文件在项目根目录")


_TEMPLATE_PATH = _find_template_path()

FONT_NAME = "微软雅黑"
FONT_SIZE_NORMAL = Pt(10)  # 正文
FONT_SIZE_HEADING = Pt(13)  # 标题
FONT_SIZE_SMALL = Pt(9)  # 小字


def _extract_resume_data(raw_text: str) -> dict:
    """用 LLM 从原始简历文本中提取详细的结构化信息"""
    prompt = f"""从以下简历中提取结构化信息。返回纯 JSON（不要 markdown），缺失字段用空字符串或空数组。

{{
  "name": "",
  "phone": "",
  "gender": "",
  "age": "",
  "school": "",
  "major": "",
  "highest_degree": "",
  "graduation_time": "",
  "education_details": "",
  "projects": [
    {{"name": "", "description": ""}}
  ],
  "internships": [
    {{"company": "", "position": "", "time": "", "description": ""}}
  ],
  "skills": []
}}

【提取说明】
- name: 姓名
- phone: 手机号
- gender: 性别
- age: 年龄，只填数字
- school: 毕业院校/在读院校
- major: 专业
- highest_degree: 最高学历（如 本科、硕士）
- graduation_time: 毕业时间（如 2026.06）
- education_details: 教育背景的补充描述（主修课程等），一句话即可
- projects: 项目经历列表，每个项目有 name 和 description
- internships: 实习/工作经历列表，每个有 company(公司名)、position(职位)、time(时间段)、description(工作描述)
- skills: 技能列表，每个是一条技能字符串
- 如果某个字段确实没有信息，用空字符串或空数组

简历内容：
---
{raw_text}
---
"""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=4096,
            messages=[
                {"role": "system", "content": "你是一位简历信息提取专家。只返回 JSON，不输出其他内容。"},
                {"role": "user", "content": prompt},
            ],
            extra_body={"thinking": {"type": "disabled"}},
        )
        text = response.choices[0].message.content.strip()

        # 提取 JSON
        data = _extract_json(text)
        if data is None:
            return {"_error": "无法解析 LLM 返回的 JSON", "_raw": text}
        return data
    except Exception as e:
        return {"_error": str(e)}


def _extract_json(text: str):
    """从文本中提取 JSON 对象"""
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    import re
    m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except Exception:
            pass
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            pass
    return None


def _find_paragraph_by_keyword(doc, keyword: str):
    """根据关键字查找段落索引"""
    for i, p in enumerate(doc.paragraphs):
        if keyword in p.text:
            return i
    return -1


def _clear_paragraph(para):
    """清空段落的所有 runs"""
    for run in para.runs:
        run.text = ""
    # 如果有 XML 元素，也清理子元素中的文本
    for elem in para._element:
        if elem.tag.endswith('}r'):
            for t in elem:
                if t.tag.endswith('}t'):
                    t.text = ""


def _add_run(para, text: str, bold: bool = False, size=None, name: str = FONT_NAME):
    """向段落添加一个 run"""
    run = para.add_run(text)
    run.font.name = name
    # 确保 east-asia 字体也设置正确
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        from lxml import etree
        rFonts = etree.SubElement(rPr, qn('w:rFonts'))
    rFonts.set(qn('w:eastAsia'), name)
    if size:
        run.font.size = size
    run.font.bold = bold
    return run


def _replace_paragraph_text(para, new_text: str, bold: bool = False, size=FONT_SIZE_NORMAL):
    """替换段落的全部文本（保留格式）"""
    _clear_paragraph(para)
    _add_run(para, new_text, bold=bold, size=size)


def _insert_content_paragraph(doc, after_index: int, text: str, bold: bool = False,
                              size=FONT_SIZE_NORMAL, alignment=None):
    """在指定段落之后插入一个新段落"""
    new_para = doc.add_paragraph()
    # 移动新段落到正确位置（在 after_index 之后）
    after_element = doc.paragraphs[after_index]._element
    after_element.addnext(new_para._element)
    _add_run(new_para, text, bold=bold, size=size)
    if alignment is not None:
        new_para.alignment = alignment
    return new_para


def fill_template(raw_resume_text: str, output_path: str) -> str:
    """
    用简历数据填充模板，保存到 output_path。
    返回 output_path。
    """
    # 1. 提取结构化数据
    data = _extract_resume_data(raw_resume_text)
    if data.get("_error"):
        raise RuntimeError(f"简历信息提取失败: {data['_error']}")

    # 2. 加载模板
    if not os.path.exists(_TEMPLATE_PATH):
        raise FileNotFoundError(f"模板文件不存在: {_TEMPLATE_PATH}")
    doc = Document(_TEMPLATE_PATH)

    # === 填充个人信息（段落3: 电话/性别/年龄） ===
    _fill_contact_info(doc, data)

    # === 填充教育摘要（段落4: 最高学历/毕业时间） ===
    _fill_education_summary(doc, data)

    # === 填充教育背景详细内容 ===
    _fill_education_content(doc, data)

    # === 填充实习经历 ===
    _fill_internship(doc, data)

    # === 填充项目经历 ===
    _fill_projects(doc, data)

    # === 填充相关技能 ===
    _fill_skills(doc, data)

    # 3. 保存
    doc.save(output_path)
    return output_path


def _fill_contact_info(doc, data: dict):
    """填充段落3：电话/性别/年龄"""
    idx = _find_paragraph_by_keyword(doc, "电话")
    if idx < 0:
        return
    para = doc.paragraphs[idx]

    phone = data.get("phone", "") or "xxxxxxxx"
    gender = data.get("gender", "") or "x"
    age = data.get("age", "") or "x"

    # 重建段落
    _clear_paragraph(para)
    _add_run(para, "电话：", bold=False, size=FONT_SIZE_NORMAL)
    _add_run(para, phone, bold=False, size=FONT_SIZE_NORMAL)
    _add_run(para, "\t", bold=False, size=FONT_SIZE_NORMAL)
    _add_run(para, "性别：", bold=False, size=FONT_SIZE_NORMAL)
    _add_run(para, gender, bold=False, size=FONT_SIZE_NORMAL)
    _add_run(para, "\t", bold=False, size=FONT_SIZE_NORMAL)
    _add_run(para, "年龄：", bold=False, size=FONT_SIZE_NORMAL)
    _add_run(para, age, bold=False, size=FONT_SIZE_NORMAL)


def _fill_education_summary(doc, data: dict):
    """填充段落4：最高学历/毕业时间"""
    idx = _find_paragraph_by_keyword(doc, "最高学历")
    if idx < 0:
        return
    para = doc.paragraphs[idx]

    degree = data.get("highest_degree", "") or "xx"
    grad_time = data.get("graduation_time", "") or "xxxx.xx"

    _clear_paragraph(para)
    _add_run(para, "最高学历：", bold=False, size=FONT_SIZE_NORMAL)
    _add_run(para, degree, bold=False, size=FONT_SIZE_NORMAL)
    _add_run(para, "\t", bold=False, size=FONT_SIZE_NORMAL)
    _add_run(para, "毕业时间：", bold=False, size=FONT_SIZE_NORMAL)
    _add_run(para, grad_time, bold=False, size=FONT_SIZE_NORMAL)


def _fill_education_content(doc, data: dict):
    """填充教育背景内容（段落8-10区域）"""
    heading_idx = _find_paragraph_by_keyword(doc, "教育背景")
    if heading_idx < 0:
        return

    school = data.get("school", "")
    major = data.get("major", "")
    edu_details = data.get("education_details", "")

    # 收集教育背景要展示的内容
    lines = []
    if school or major:
        line = ""
        if school:
            line += school
        if major:
            line += f" · {major}" if line else major
        if line:
            lines.append(line)
    if edu_details:
        lines.append(edu_details)

    if not lines:
        return  # 没有额外教育信息，保留模板默认

    # 找到教育背景标题后面的空段落并填充
    _fill_empty_paragraphs_after(doc, heading_idx, lines)


def _fill_internship(doc, data: dict):
    """填充或删除实习经历"""
    heading_idx = _find_paragraph_by_keyword(doc, "实习经历")
    if heading_idx < 0:
        return

    internships = data.get("internships", []) or []

    if not internships:
        # 没有实习经历 → 删除该模块（标题 + 后续内容段落到下一个标题前）
        _delete_section(doc, heading_idx)
        return

    # 构建实习内容
    lines = []
    for item in internships:
        company = item.get("company", "")
        position = item.get("position", "")
        time_str = item.get("time", "")
        desc = item.get("description", "")

        header = ""
        if company:
            header += company
        if position:
            header += f" · {position}" if header else position
        if time_str:
            header += f"  |  {time_str}"
        if header:
            lines.append(header)
        if desc:
            lines.append(desc)
        lines.append("")  # 空行分隔

    # 去掉末尾多余空行
    while lines and lines[-1] == "":
        lines.pop()

    _fill_empty_paragraphs_after(doc, heading_idx, lines)


def _fill_projects(doc, data: dict):
    """填充项目经历"""
    heading_idx = _find_paragraph_by_keyword(doc, "项目经历")
    if heading_idx < 0:
        return

    projects = data.get("projects", []) or []

    if not projects:
        return  # 没有项目经历，保留模板默认

    lines = []
    for item in projects:
        name = item.get("name", "")
        desc = item.get("description", "")

        if name:
            lines.append(name)
        if desc:
            lines.append(desc)
        lines.append("")  # 空行分隔

    while lines and lines[-1] == "":
        lines.pop()

    _fill_empty_paragraphs_after(doc, heading_idx, lines)


def _fill_skills(doc, data: dict):
    """填充相关技能"""
    heading_idx = _find_paragraph_by_keyword(doc, "相关技能")
    if heading_idx < 0:
        return

    skills = data.get("skills", []) or []

    if not skills:
        return  # 没有技能，保留模板默认

    skill_text = "、".join(skills)
    _fill_empty_paragraphs_after(doc, heading_idx, [skill_text])


def _fix_paragraph_spacing(para):
    """修复段落的行距，将模板中极小的 exact 行距改为正常的自动行距"""
    pPr = para._element.find(qn('w:pPr'))
    if pPr is None:
        return
    spacing = pPr.find(qn('w:spacing'))
    if spacing is not None:
        # 移除 fixed exact 行距，恢复为自动行距
        line_val = spacing.get(qn('w:line'))
        line_rule = spacing.get(qn('w:lineRule'))
        if line_rule == 'exact' and line_val and int(line_val) < 300:
            # 行距太小（如 14、152），移除 exact 限制
            spacing.set(qn('w:lineRule'), 'auto')
            spacing.set(qn('w:line'), '360')  # 标准单倍行距


def _fill_empty_paragraphs_after(doc, heading_idx: int, lines: list):
    """
    在 heading_idx 之后找到连续的空白段落，按行填充内容。
    如果空白段落不够，插入新段落。
    """
    # 找到后续的空白段落
    content_indices = []
    for i in range(heading_idx + 1, len(doc.paragraphs)):
        p = doc.paragraphs[i]
        text = p.text.strip()
        # 如果遇到另一个标题（可能包含特定关键词）则停止
        if _is_section_heading(text):
            break
        content_indices.append(i)

    # 清除已有内容
    for ci in content_indices:
        _clear_paragraph(doc.paragraphs[ci])

    # 填充内容
    total_slots = len(content_indices) if content_indices else 0
    last_filled_element = doc.paragraphs[heading_idx]._element

    for li, line in enumerate(lines):
        if li < total_slots:
            # 使用现有空段落
            para = doc.paragraphs[content_indices[li]]
            _fix_paragraph_spacing(para)  # 修复模板空段落的极小行距
            _add_run(para, line, bold=False, size=FONT_SIZE_NORMAL)
            last_filled_element = para._element
        else:
            # 插入新段落
            new_para = doc.add_paragraph()
            _add_run(new_para, line, bold=False, size=FONT_SIZE_NORMAL)
            # 移到最后一个已填充段落之后
            last_filled_element.addnext(new_para._element)
            last_filled_element = new_para._element

    # 清除多余的空白段落（如果 lines 少于 slots）
    for ci in content_indices[len(lines):]:
        _clear_paragraph(doc.paragraphs[ci])


def _is_section_heading(text: str) -> bool:
    """判断文本是否为简历模板的章节标题"""
    headings = ["教育背景", "实习经历", "项目经历", "相关技能"]
    return any(h in text for h in headings)


def _delete_section(doc, heading_idx: int):
    """
    删除从 heading_idx 开始的整个章节（标题 + 后续内容，直到下一个标题）。
    """
    # 找到删除范围
    end_idx = heading_idx
    for i in range(heading_idx + 1, len(doc.paragraphs)):
        text = doc.paragraphs[i].text.strip()
        if _is_section_heading(text):
            break
        end_idx = i

    # 从后往前删除，避免索引变化
    for i in range(end_idx, heading_idx - 1, -1):
        p = doc.paragraphs[i]._element
        p.getparent().remove(p)
